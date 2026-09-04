#!/usr/bin/env python3
"""Create a portable backup of Dr. OMEB's legacy Doctor's Notes blog.

The backup includes:
- every discovered post as untouched source HTML;
- a readable Markdown copy of each post;
- locally copied/downloaded post images;
- a machine-readable manifest and human-readable report.

It is intended to run in GitHub Actions from the dr-omeb-website repository.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Tag
from markdownify import markdownify as html_to_markdown

BASE_URL = "https://onemanelectricalband.com"
ARCHIVE_URL = f"{BASE_URL}/blogs/diary-of-a-rock-n-roll-doctor"
OUT_DIR = Path("archive/doctors-notes")
POSTS_DIR = OUT_DIR / "posts"
RAW_DIR = OUT_DIR / "raw-html"
IMAGES_DIR = OUT_DIR / "images"
MANIFEST_PATH = OUT_DIR / "manifest.json"
REPORT_PATH = OUT_DIR / "backup-report.md"
README_PATH = OUT_DIR / "README.md"
ASSET_MANIFEST_PATH = Path("assets/image-manifest.json")

TIMEOUT = 35
MAX_ARCHIVE_PAGES = 50
MAX_IMAGE_BYTES = 40 * 1024 * 1024
USER_AGENT = "DrOMEB-DoctorsNotes-Backup/1.0 (+https://onemanelectricalband.com/)"

POST_RE = re.compile(
    r"/(?:blog/blog|blogs/[^/]+/posts)/(\d+)/([^?#]+)",
    re.IGNORECASE,
)
MONTH_DATE_RE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2},\s+\d{4}\b",
    re.IGNORECASE,
)
NUMERIC_DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b")
UNWANTED_CLASS_RE = re.compile(
    r"comment|share|social|navigation|pagination|back[-_ ]?to|subscribe|"
    r"site[-_ ]?(?:header|footer)|menu|toolbar|admin|edit[-_ ]?controls?",
    re.IGNORECASE,
)
CHROME_IMAGE_RE = re.compile(
    r"favicon|dr-omeb-logo|social[-_ ]?icon|facebook-|instagram-|twitter-|"
    r"twitch-|envelope-|apple-music-|amazon-|spotify-|bandcamp-|deezer-|"
    r"soundcloud-|youtube-[0-9a-f]",
    re.IGNORECASE,
)

session = requests.Session()
session.headers.update(
    {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    }
)


@dataclass
class PostRecord:
    post_id: str
    source_url: str
    title: str = ""
    archive_date: str | None = None
    final_url: str | None = None
    published_date: str | None = None
    slug: str = ""
    markdown_path: str | None = None
    raw_html_path: str | None = None
    images: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def canonical_url(url: str) -> str:
    parsed = urlparse(url)
    path = re.sub(r"/+", "/", parsed.path or "/")
    return urlunparse(("https", "onemanelectricalband.com", path, "", "", ""))


def slugify(value: str, fallback: str = "post") -> str:
    value = unquote(value or "")
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value[:110] or fallback


def quote_yaml(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    value = normalize_space(value)
    formats = (
        "%b %d, %Y",
        "%B %d, %Y",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
    )
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    month_match = MONTH_DATE_RE.search(value)
    if month_match:
        for fmt in ("%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(month_match.group(0), fmt).date().isoformat()
            except ValueError:
                continue
    numeric_match = NUMERIC_DATE_RE.search(value)
    if numeric_match:
        try:
            return datetime.strptime(numeric_match.group(0), "%m/%d/%Y").date().isoformat()
        except ValueError:
            pass
    return None


def fetch_html(url: str) -> tuple[requests.Response, BeautifulSoup]:
    response = session.get(url, timeout=TIMEOUT, allow_redirects=True)
    response.raise_for_status()
    ctype = (response.headers.get("content-type") or "").lower()
    if "text/html" not in ctype:
        raise ValueError(f"Expected HTML but received {ctype or 'unknown content type'}")
    return response, BeautifulSoup(response.text, "html.parser")


def title_from_card(anchor: Tag) -> str:
    own = normalize_space(anchor.get_text(" ", strip=True))
    if own and own.lower() not in {"read more", "read more posts", "continue reading"}:
        return own
    node: Tag | None = anchor
    for _ in range(7):
        if node is None:
            break
        for selector in ("h1", "h2", "h3", "h4", "[class*='title']"):
            heading = node.select_one(selector)
            if heading:
                text = normalize_space(heading.get_text(" ", strip=True))
                if text and text.lower() not in {"doctor's notes", "dr. omeb"}:
                    return text
        node = node.parent if isinstance(node.parent, Tag) else None
    return ""


def date_from_card(anchor: Tag) -> str | None:
    node: Tag | None = anchor
    for _ in range(7):
        if node is None:
            break
        text = normalize_space(node.get_text(" ", strip=True))
        match = MONTH_DATE_RE.search(text)
        if match:
            parsed = parse_date(match.group(0))
            if parsed:
                return parsed
        node = node.parent if isinstance(node.parent, Tag) else None
    return None


def discover_posts() -> tuple[list[PostRecord], list[dict]]:
    posts: dict[str, PostRecord] = {}
    archive_errors: list[dict] = []
    empty_pages = 0

    for page in range(1, MAX_ARCHIVE_PAGES + 1):
        page_url = ARCHIVE_URL if page == 1 else f"{ARCHIVE_URL}?p={page}"
        try:
            _, soup = fetch_html(page_url)
        except Exception as exc:
            archive_errors.append({"url": page_url, "error": str(exc)})
            break

        new_ids: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            absolute = urljoin(page_url, anchor["href"])
            match = POST_RE.search(urlparse(absolute).path)
            if not match:
                continue
            post_id, path_slug = match.groups()
            source_url = canonical_url(absolute)
            title = title_from_card(anchor)
            archive_date = date_from_card(anchor)
            if post_id not in posts:
                posts[post_id] = PostRecord(
                    post_id=post_id,
                    source_url=source_url,
                    title=title,
                    archive_date=archive_date,
                    slug=slugify(path_slug, fallback=f"post-{post_id}"),
                )
                new_ids.add(post_id)
            else:
                record = posts[post_id]
                if not record.title and title:
                    record.title = title
                if not record.archive_date and archive_date:
                    record.archive_date = archive_date

        if new_ids:
            empty_pages = 0
        else:
            empty_pages += 1
        if page >= 2 and empty_pages >= 1:
            break
        time.sleep(0.1)

    def sort_key(record: PostRecord) -> tuple[str, str]:
        return (record.archive_date or "0000-00-00", record.post_id)

    return sorted(posts.values(), key=sort_key, reverse=True), archive_errors


def find_post_heading(soup: BeautifulSoup, title: str) -> Tag | None:
    title_norm = normalize_space(title).lower()
    title_tokens = set(re.findall(r"[a-z0-9]+", title_norm))
    best: tuple[float, Tag] | None = None
    for heading in soup.find_all(["h1", "h2", "h3"]):
        text = normalize_space(heading.get_text(" ", strip=True))
        if not text:
            continue
        norm = text.lower()
        if title_norm and norm == title_norm:
            return heading
        tokens = set(re.findall(r"[a-z0-9]+", norm))
        overlap = len(tokens & title_tokens) / max(1, len(title_tokens))
        if overlap >= 0.6 and (best is None or overlap > best[0]):
            best = (overlap, heading)
    return best[1] if best else None


def candidate_score(node: Tag, title: str) -> float:
    text = normalize_space(node.get_text(" ", strip=True))
    length = len(text)
    if length < 300 or length > 200_000:
        return -1e9
    descriptor = " ".join(
        [node.name or "", node.get("id", ""), " ".join(node.get("class", []))]
    ).lower()
    score = 0.0
    if node.name == "article":
        score += 9000
    if node.name == "main":
        score += 1800
    if any(word in descriptor for word in ("blog-post", "post-content", "post-body", "article-body")):
        score += 8000
    elif any(word in descriptor for word in ("post", "article", "content", "blog")):
        score += 3500
    if title and normalize_space(title).lower() in text.lower():
        score += 1500
    if NUMERIC_DATE_RE.search(text) or MONTH_DATE_RE.search(text):
        score += 500
    score -= length / 80
    return score


def choose_body_container(soup: BeautifulSoup, title: str) -> Tag:
    candidates: list[Tag] = []
    selectors = (
        "article",
        "[itemprop='articleBody']",
        "[class*='blog-post']",
        "[class*='post-content']",
        "[class*='post-body']",
        "[class*='article-body']",
        "main",
    )
    for selector in selectors:
        candidates.extend(soup.select(selector))

    heading = find_post_heading(soup, title)
    node = heading
    for _ in range(10):
        if not isinstance(node, Tag):
            break
        candidates.append(node)
        node = node.parent if isinstance(node.parent, Tag) else None

    unique: list[Tag] = []
    seen_ids: set[int] = set()
    for candidate in candidates:
        marker = id(candidate)
        if marker not in seen_ids:
            seen_ids.add(marker)
            unique.append(candidate)

    if not unique:
        return soup.body or soup
    return max(unique, key=lambda item: candidate_score(item, title))


def clean_body_html(container: Tag, title: str) -> str:
    fragment = BeautifulSoup(str(container), "html.parser")
    for tag in fragment.find_all(["script", "style", "noscript", "nav", "footer", "header", "form", "button"]):
        tag.decompose()
    for tag in list(fragment.find_all(True)):
        descriptor = " ".join(
            [tag.get("id", ""), " ".join(tag.get("class", []))]
        )
        if descriptor and UNWANTED_CLASS_RE.search(descriptor):
            tag.decompose()
            continue
        exact = normalize_space(tag.get_text(" ", strip=True)).lower()
        if exact in {"minimize image", "edit image", "delete image", "back to all posts"}:
            tag.decompose()

    heading = find_post_heading(fragment, title)
    if heading:
        heading.decompose()
    return str(fragment)


def clean_markdown(markdown: str) -> str:
    markdown = markdown.replace("\u00a0", " ")
    lines: list[str] = []
    previous_blank = False
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        normalized = normalize_space(line).lower()
        if normalized in {
            "minimize image",
            "edit image",
            "delete image",
            "back to all posts",
            "leave a comment",
            "share link",
        }:
            continue
        is_blank = not line.strip()
        if is_blank and previous_blank:
            continue
        lines.append(line)
        previous_blank = is_blank
    return "\n".join(lines).strip() + "\n"


def extract_title(soup: BeautifulSoup, fallback: str) -> str:
    for attrs in (
        {"property": "og:title"},
        {"name": "twitter:title"},
    ):
        meta = soup.find("meta", attrs=attrs)
        if meta and meta.get("content"):
            title = normalize_space(meta["content"])
            title = re.sub(r"\s*[|–—-]\s*Dr\.?\s*OMEB.*$", "", title, flags=re.I)
            if title:
                return title
    heading = find_post_heading(soup, fallback)
    if heading:
        return normalize_space(heading.get_text(" ", strip=True))
    return fallback or "Untitled Doctor's Notes Post"


def extract_published_date(soup: BeautifulSoup, fallback: str | None) -> str | None:
    for attrs in (
        {"property": "article:published_time"},
        {"name": "date"},
        {"itemprop": "datePublished"},
    ):
        node = soup.find(attrs=attrs)
        if node:
            raw = node.get("content") or node.get("datetime") or node.get_text(" ", strip=True)
            parsed = parse_date(raw)
            if parsed:
                return parsed
    text = normalize_space(soup.get_text(" ", strip=True))
    numeric_matches = NUMERIC_DATE_RE.findall(text)
    if numeric_matches:
        parsed = parse_date(numeric_matches[-1])
        if parsed:
            return parsed
    return fallback


def load_asset_manifest() -> list[dict]:
    if not ASSET_MANIFEST_PATH.exists():
        return []
    try:
        data = json.loads(ASSET_MANIFEST_PATH.read_text(encoding="utf-8"))
        return data.get("images", [])
    except Exception:
        return []


def zoogle_asset_key(url: str) -> str | None:
    decoded = unquote(url)
    match = re.search(r"/u/\d+/([0-9a-f]{20,})/original/([^/?]+)", decoded, re.I)
    if match:
        return f"{match.group(1).lower()}::{match.group(2).lower()}"
    return None


def image_url_from_tag(tag: Tag, base_url: str) -> list[str]:
    values: list[str] = []
    for attr in ("src", "data-src", "data-original", "data-lazy-src"):
        raw = tag.get(attr)
        if raw:
            values.append(urljoin(base_url, html.unescape(raw)))
    for attr in ("srcset", "data-srcset"):
        raw = tag.get(attr)
        if raw:
            for part in raw.split(","):
                candidate = part.strip().split()[0] if part.strip() else ""
                if candidate:
                    values.append(urljoin(base_url, html.unescape(candidate)))
    return values


def parsed_page_image_urls(soup: BeautifulSoup, container: Tag, base_url: str) -> set[str]:
    urls: set[str] = set()
    for tag in container.find_all("img"):
        urls.update(image_url_from_tag(tag, base_url))
    for attrs in (
        {"property": "og:image"},
        {"name": "twitter:image"},
    ):
        meta = soup.find("meta", attrs=attrs)
        if meta and meta.get("content"):
            urls.add(urljoin(base_url, html.unescape(meta["content"])))
    return {url for url in urls if url.startswith(("http://", "https://"))}


def relevant_manifest_images(post_id: str, asset_items: list[dict]) -> list[dict]:
    matches: list[dict] = []
    for item in asset_items:
        found_on = item.get("found_on") or []
        if not any(post_id in str(page) for page in found_on):
            continue
        source_url = str(item.get("source_url") or "")
        local_path = str(item.get("local_path") or "")
        host = (urlparse(source_url).hostname or "").lower()
        if host in {"www.facebook.com", "facebook.com", "assets-app-production-pubnet.bndzgl.com"}:
            continue
        if len(found_on) > 8 or CHROME_IMAGE_RE.search(local_path):
            continue
        source_path = Path(local_path)
        if not source_path.exists() or source_path.suffix.lower() not in {
            ".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".svg", ".bmp", ".tif", ".tiff"
        }:
            continue
        matches.append(item)

    best_by_key: dict[str, dict] = {}
    for item in matches:
        source_url = str(item.get("source_url") or "")
        key = zoogle_asset_key(source_url) or str(item.get("sha256") or source_url)
        previous = best_by_key.get(key)
        if previous is None or int(item.get("bytes") or 0) > int(previous.get("bytes") or 0):
            best_by_key[key] = item
    return sorted(best_by_key.values(), key=lambda item: str(item.get("local_path") or ""))


def safe_image_stem(value: str) -> str:
    stem = Path(unquote(urlparse(value).path)).stem or "image"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-._") or "image"
    return stem[:70]


def download_fallback_image(url: str) -> tuple[bytes, str] | None:
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            response.raise_for_status()
            ctype = (response.headers.get("content-type") or "").split(";", 1)[0].lower()
            if not ctype.startswith("image/"):
                return None
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_content(256 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_IMAGE_BYTES:
                    raise ValueError("image too large")
                chunks.append(chunk)
            ext = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
                "image/gif": ".gif",
                "image/avif": ".avif",
                "image/svg+xml": ".svg",
            }.get(ctype, Path(unquote(urlparse(response.url).path)).suffix or ".bin")
            return b"".join(chunks), ext
    except Exception:
        return None


def backup_images(
    record: PostRecord,
    soup: BeautifulSoup,
    container: Tag,
    asset_items: list[dict],
    copied_by_sha: dict[str, str],
) -> list[dict]:
    backed_up: list[dict] = []
    used_source_keys: set[str] = set()

    for item in relevant_manifest_images(record.post_id, asset_items):
        local_source = Path(str(item["local_path"]))
        sha = str(item.get("sha256") or "")
        if not sha:
            sha = hashlib.sha256(local_source.read_bytes()).hexdigest()
        if sha in copied_by_sha:
            backup_rel = copied_by_sha[sha]
        else:
            stem = safe_image_stem(local_source.name.split("--", 1)[0])
            ext = local_source.suffix.lower() or ".bin"
            dest = IMAGES_DIR / f"{sha[:12]}-{stem}{ext}"
            if not dest.exists():
                shutil.copy2(local_source, dest)
            backup_rel = dest.as_posix()
            copied_by_sha[sha] = backup_rel
        source_url = str(item.get("source_url") or "")
        source_key = zoogle_asset_key(source_url) or source_url
        used_source_keys.add(source_key)
        backed_up.append(
            {
                "source_url": source_url,
                "original_archive_path": local_source.as_posix(),
                "backup_path": backup_rel,
                "bytes": int(item.get("bytes") or local_source.stat().st_size),
                "sha256": sha,
            }
        )

    for url in sorted(parsed_page_image_urls(soup, container, record.final_url or record.source_url)):
        host = (urlparse(url).hostname or "").lower()
        if host in {"www.facebook.com", "facebook.com", "assets-app-production-pubnet.bndzgl.com"}:
            continue
        key = zoogle_asset_key(url) or url
        if key in used_source_keys:
            continue
        downloaded = download_fallback_image(url)
        if not downloaded:
            continue
        data, ext = downloaded
        sha = hashlib.sha256(data).hexdigest()
        if sha in copied_by_sha:
            backup_rel = copied_by_sha[sha]
        else:
            stem = safe_image_stem(url)
            dest = IMAGES_DIR / f"{sha[:12]}-{stem}{ext}"
            if not dest.exists():
                dest.write_bytes(data)
            backup_rel = dest.as_posix()
            copied_by_sha[sha] = backup_rel
        backed_up.append(
            {
                "source_url": url,
                "original_archive_path": None,
                "backup_path": backup_rel,
                "bytes": len(data),
                "sha256": sha,
            }
        )
        used_source_keys.add(key)

    unique: dict[str, dict] = {}
    for image in backed_up:
        unique.setdefault(str(image["backup_path"]), image)
    return list(unique.values())


def relative_image_path(markdown_file: Path, image_path: str) -> str:
    return Path("..").joinpath("images", Path(image_path).name).as_posix()


def write_post(record: PostRecord, response: requests.Response, soup: BeautifulSoup, asset_items: list[dict], copied_by_sha: dict[str, str]) -> None:
    record.final_url = canonical_url(response.url)
    record.title = extract_title(soup, record.title)
    record.published_date = extract_published_date(soup, record.archive_date)
    if not record.slug:
        match = POST_RE.search(urlparse(record.final_url).path)
        record.slug = slugify(match.group(2) if match else record.title, fallback=f"post-{record.post_id}")

    date_prefix = record.published_date or "undated"
    basename = f"{date_prefix}-{record.post_id}-{record.slug}"
    raw_path = RAW_DIR / f"{basename}.html"
    markdown_path = POSTS_DIR / f"{basename}.md"
    raw_path.write_text(response.text, encoding="utf-8")

    container = choose_body_container(soup, record.title)
    cleaned_html = clean_body_html(container, record.title)
    markdown = clean_markdown(
        html_to_markdown(
            cleaned_html,
            heading_style="ATX",
            bullets="-",
            strip=["script", "style"],
        )
    )
    if len(normalize_space(markdown)) < 200:
        record.warnings.append("Readable Markdown extraction was unusually short; use the raw HTML copy if needed.")
        markdown = normalize_space(container.get_text("\n", strip=True)) + "\n"

    record.images = backup_images(record, soup, container, asset_items, copied_by_sha)
    frontmatter = [
        "---",
        f"title: {quote_yaml(record.title)}",
        f"published: {quote_yaml(record.published_date or '')}",
        f"post_id: {quote_yaml(record.post_id)}",
        f"source_url: {quote_yaml(record.source_url)}",
        f"final_url: {quote_yaml(record.final_url)}",
        f"backed_up_utc: {quote_yaml(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))}",
        "images:",
    ]
    if record.images:
        for image in record.images:
            frontmatter.append(f"  - {quote_yaml(relative_image_path(markdown_path, image['backup_path']))}")
    else:
        frontmatter[-1] = "images: []"
    frontmatter += ["---", "", f"# {record.title}", ""]

    image_section: list[str] = []
    if record.images:
        image_section += ["## Backed-up images", ""]
        for index, image in enumerate(record.images, start=1):
            rel = relative_image_path(markdown_path, image["backup_path"])
            image_section.append(f"![{record.title} — image {index}]({rel})")
            image_section.append("")
        image_section += ["---", ""]

    markdown_path.write_text(
        "\n".join(frontmatter + image_section) + markdown,
        encoding="utf-8",
    )
    record.markdown_path = markdown_path.as_posix()
    record.raw_html_path = raw_path.as_posix()


def prepare_output_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for directory in (POSTS_DIR, RAW_DIR, IMAGES_DIR):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)


def write_reports(records: list[PostRecord], archive_errors: list[dict], post_errors: list[dict], generated: str) -> None:
    image_paths = {image["backup_path"] for record in records for image in record.images}
    manifest = {
        "source_archive": ARCHIVE_URL,
        "generated_utc": generated,
        "posts_discovered": len(records),
        "posts_backed_up": sum(1 for record in records if record.markdown_path and record.raw_html_path),
        "unique_images_in_backup": len(image_paths),
        "archive_errors": archive_errors,
        "post_errors": post_errors,
        "posts": [
            {
                "post_id": record.post_id,
                "title": record.title,
                "published_date": record.published_date,
                "source_url": record.source_url,
                "final_url": record.final_url,
                "slug": record.slug,
                "markdown_path": record.markdown_path,
                "raw_html_path": record.raw_html_path,
                "images": record.images,
                "warnings": record.warnings,
            }
            for record in records
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = [
        "# Doctor's Notes Backup Report",
        "",
        f"Generated: `{generated}`",
        "",
        f"- Posts discovered: **{manifest['posts_discovered']}**",
        f"- Posts backed up: **{manifest['posts_backed_up']}**",
        f"- Unique post images copied into the portable backup: **{manifest['unique_images_in_backup']}**",
        f"- Archive-page errors: **{len(archive_errors)}**",
        f"- Individual post errors: **{len(post_errors)}**",
        "",
        "## Backed-up posts",
        "",
        "| Date | Post | Markdown | Raw HTML | Images |",
        "|---|---|---|---|---:|",
    ]
    for record in records:
        markdown_link = f"[Markdown]({Path(record.markdown_path).relative_to(OUT_DIR).as_posix()})" if record.markdown_path else "FAILED"
        html_link = f"[HTML]({Path(record.raw_html_path).relative_to(OUT_DIR).as_posix()})" if record.raw_html_path else "FAILED"
        safe_title = record.title.replace("|", "\\|")
        report.append(
            f"| {record.published_date or 'Unknown'} | {safe_title} | {markdown_link} | {html_link} | {len(record.images)} |"
        )
    if archive_errors:
        report += ["", "## Archive errors", ""]
        report.extend(f"- `{item['url']}` — {item['error']}" for item in archive_errors)
    if post_errors:
        report += ["", "## Post errors", ""]
        report.extend(f"- `{item['url']}` — {item['error']}" for item in post_errors)
    REPORT_PATH.write_text("\n".join(report) + "\n", encoding="utf-8")

    readme = f"""# Portable Doctor's Notes Backup

This directory is a portable backup of the public **Doctor's Notes** archive from
`{ARCHIVE_URL}`.

Generated: `{generated}`

## Contents

- `posts/` — readable Markdown copies with local image references.
- `raw-html/` — untouched HTML responses retained for exact recovery.
- `images/` — {len(image_paths)} unique images used by the backed-up posts.
- `manifest.json` — source URLs, post IDs, dates, file paths, image hashes, and any warnings.
- `backup-report.md` — human-readable inventory.

The Markdown files are the easiest source for rebuilding a native blog. The raw HTML
files are the safety copy when exact legacy formatting or embedded code must be recovered.
This backup is stored on a non-production Git branch so it is not part of the live site.
"""
    README_PATH.write_text(readme, encoding="utf-8")


def main() -> int:
    generated = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    prepare_output_dirs()
    records, archive_errors = discover_posts()
    asset_items = load_asset_manifest()
    copied_by_sha: dict[str, str] = {}
    post_errors: list[dict] = []

    for index, record in enumerate(records, start=1):
        print(f"[{index}/{len(records)}] Backing up {record.source_url}", flush=True)
        try:
            response, soup = fetch_html(record.source_url)
            write_post(record, response, soup, asset_items, copied_by_sha)
        except Exception as exc:
            record.warnings.append(str(exc))
            post_errors.append({"url": record.source_url, "error": str(exc)})
        time.sleep(0.1)

    write_reports(records, archive_errors, post_errors, generated)
    summary = {
        "posts_discovered": len(records),
        "posts_backed_up": sum(1 for record in records if record.markdown_path),
        "unique_images": len(copied_by_sha),
        "archive_errors": len(archive_errors),
        "post_errors": len(post_errors),
    }
    print(json.dumps(summary, indent=2))
    return 0 if summary["posts_backed_up"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
