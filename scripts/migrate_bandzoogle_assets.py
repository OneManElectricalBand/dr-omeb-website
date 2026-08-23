#!/usr/bin/env python3
"""Archive images referenced by the live Dr. OMEB Bandzoogle site.

The script crawls public pages on onemanelectricalband.com, discovers images in
HTML/CSS/JSON-LD, follows Bandzoogle/Zoogle redirects, saves the image bytes in
this repository, and writes a source-to-local manifest plus a human-readable
report.
"""

from __future__ import annotations

import hashlib
import html
import json
import mimetypes
import re
import sys
import time
from collections import deque
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, unquote, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

START_URL = "https://onemanelectricalband.com/"
SITE_HOSTS = {"onemanelectricalband.com", "www.onemanelectricalband.com"}
OUT_DIR = Path("assets/images/migrated")
MANIFEST_PATH = Path("assets/image-manifest.json")
REPORT_PATH = Path("assets/image-migration-report.md")
MAX_PAGES = 1000
MAX_IMAGE_BYTES = 40 * 1024 * 1024
TIMEOUT = 30
USER_AGENT = "DrOMEB-Asset-Migration/1.0 (+https://onemanelectricalband.com/)"

IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".svg", ".bmp", ".tif", ".tiff", ".ico"
}
CONTENT_TYPE_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
    "image/svg+xml": ".svg",
    "image/bmp": ".bmp",
    "image/tiff": ".tif",
    "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
}

CSS_URL_RE = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", re.I)
ABS_URL_RE = re.compile(r"https?://[^\s\"'<>\\)]+", re.I)
FILES_URL_RE = re.compile(r"(?:https?:)?//(?:www\.)?onemanelectricalband\.com/files/[^\s\"'<>\\)]+", re.I)
ZOOGLE_URL_RE = re.compile(r"https?://images\.zoogletools\.com/[^\s\"'<>\\)]+", re.I)

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})


def clean_url(value: str, base: str) -> str | None:
    if not value:
        return None
    value = html.unescape(value.strip()).strip("'\"")
    if not value or value.startswith(("data:", "blob:", "javascript:", "mailto:", "tel:", "#")):
        return None
    if value.startswith("//"):
        value = "https:" + value
    url = urljoin(base, value)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, ""))


def canonical_page_url(url: str) -> str:
    parsed = urlparse(url)
    # Keep only pagination-like query keys so blog archives can still be traversed.
    kept = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() in {"page", "p"}]
    query = urlencode(kept)
    path = parsed.path or "/"
    return urlunparse(("https", "onemanelectricalband.com", path, "", query, ""))


def is_internal_page(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.hostname not in SITE_HOSTS:
        return False
    path = parsed.path.lower()
    if any(path.endswith(ext) for ext in IMAGE_EXTS):
        return False
    if path.startswith(("/files/", "/admin", "/login", "/cart", "/checkout")):
        return False
    return True


def looks_image_url(url: str) -> bool:
    p = urlparse(url)
    lower_path = unquote(p.path).lower()
    if p.hostname == "images.zoogletools.com":
        return True
    if p.hostname in SITE_HOSTS and lower_path.startswith("/files/"):
        return True
    return any(lower_path.endswith(ext) or (ext + "/") in lower_path for ext in IMAGE_EXTS)


def srcset_urls(value: str, base: str) -> list[str]:
    out = []
    for part in value.split(","):
        candidate = part.strip().split()[0] if part.strip() else ""
        url = clean_url(candidate, base)
        if url:
            out.append(url)
    return out


def extract_image_urls_from_text(text: str, base: str) -> set[str]:
    found: set[str] = set()
    for regex in (FILES_URL_RE, ZOOGLE_URL_RE, ABS_URL_RE):
        for raw in regex.findall(text or ""):
            url = clean_url(raw.rstrip(".,;]}") , base)
            if url and looks_image_url(url):
                found.add(url)
    for raw in CSS_URL_RE.findall(text or ""):
        url = clean_url(raw, base)
        if url and looks_image_url(url):
            found.add(url)
    return found


def safe_stem_from_url(url: str) -> str:
    parsed = urlparse(url)
    decoded_path = unquote(parsed.path)
    # Zoogle originals often look like /original/foo.jpg/!!/transform...
    marker = "/original/"
    if marker in decoded_path:
        tail = decoded_path.split(marker, 1)[1].split("/!!", 1)[0].strip("/")
        name = Path(tail).name
    else:
        name = Path(decoded_path.rstrip("/")).name or "image"
    # Strip a known image extension here; it gets added after MIME detection.
    stem = Path(name).stem if Path(name).suffix.lower() in IMAGE_EXTS else name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-._") or "image"
    return stem[:90]


def extension_for(content_type: str, url: str) -> str:
    ctype = (content_type or "").split(";", 1)[0].strip().lower()
    if ctype in CONTENT_TYPE_EXT:
        return CONTENT_TYPE_EXT[ctype]
    path = unquote(urlparse(url).path)
    for ext in IMAGE_EXTS:
        if path.lower().endswith(ext) or (ext + "/") in path.lower():
            return ".jpg" if ext == ".jpeg" else ext
    guessed = mimetypes.guess_extension(ctype) if ctype else None
    return guessed or ".bin"


def download_image(url: str) -> tuple[bytes, str, str] | None:
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
            r.raise_for_status()
            ctype = (r.headers.get("content-type") or "").split(";", 1)[0].lower()
            if not ctype.startswith("image/"):
                return None
            chunks = []
            total = 0
            for chunk in r.iter_content(1024 * 256):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_IMAGE_BYTES:
                    raise ValueError(f"image exceeds {MAX_IMAGE_BYTES} bytes")
                chunks.append(chunk)
            return b"".join(chunks), ctype, r.url
    except Exception as exc:
        failures.append({"url": url, "error": str(exc)})
        return None


OUT_DIR.mkdir(parents=True, exist_ok=True)

pages_seen: list[str] = []
page_errors: list[dict] = []
image_sources: dict[str, set[str]] = {}
stylesheets_seen: set[str] = set()
queue = deque([START_URL])
queued = {canonical_page_url(START_URL)}

while queue and len(pages_seen) < MAX_PAGES:
    page_url = canonical_page_url(queue.popleft())
    try:
        r = session.get(page_url, timeout=TIMEOUT, allow_redirects=True)
        r.raise_for_status()
        ctype = (r.headers.get("content-type") or "").lower()
        if "text/html" not in ctype:
            continue
        pages_seen.append(page_url)
        soup = BeautifulSoup(r.text, "html.parser")

        discovered: set[str] = set()
        attr_names = ("src", "data-src", "data-original", "data-lazy-src", "poster")
        for tag in soup.find_all(True):
            for attr in attr_names:
                value = tag.get(attr)
                if value:
                    u = clean_url(value, r.url)
                    if u and looks_image_url(u):
                        discovered.add(u)
            for attr in ("srcset", "data-srcset"):
                if tag.get(attr):
                    discovered.update(u for u in srcset_urls(tag.get(attr), r.url) if looks_image_url(u))
            if tag.get("style"):
                discovered.update(extract_image_urls_from_text(tag.get("style"), r.url))

        for meta in soup.find_all("meta"):
            key = (meta.get("property") or meta.get("name") or "").lower()
            if "image" in key and meta.get("content"):
                u = clean_url(meta.get("content"), r.url)
                if u:
                    discovered.add(u)

        # Inline CSS / JSON-LD / other raw references.
        discovered.update(extract_image_urls_from_text(r.text, r.url))

        # Crawl linked stylesheets for theme/background images.
        for link in soup.find_all("link", href=True):
            rel = " ".join(link.get("rel") or []).lower()
            if "stylesheet" not in rel:
                continue
            css_url = clean_url(link["href"], r.url)
            if not css_url or css_url in stylesheets_seen:
                continue
            stylesheets_seen.add(css_url)
            try:
                css_r = session.get(css_url, timeout=TIMEOUT, allow_redirects=True)
                if css_r.ok:
                    for img_url in extract_image_urls_from_text(css_r.text, css_r.url):
                        discovered.add(img_url)
            except Exception as exc:
                page_errors.append({"url": css_url, "error": f"stylesheet: {exc}"})

        for img_url in discovered:
            image_sources.setdefault(img_url, set()).add(page_url)

        # Crawl public internal links.
        for a in soup.find_all("a", href=True):
            target = clean_url(a["href"], r.url)
            if not target or not is_internal_page(target):
                continue
            target = canonical_page_url(target)
            if target not in queued:
                queued.add(target)
                queue.append(target)

        time.sleep(0.05)
    except Exception as exc:
        page_errors.append({"url": page_url, "error": str(exc)})

truncated = bool(queue)

failures: list[dict] = []
manifest_items: list[dict] = []
sha_to_path: dict[str, str] = {}

for idx, url in enumerate(sorted(image_sources), start=1):
    result = download_image(url)
    if result is None:
        # If it merely wasn't an image response, record that distinctly.
        if not any(f["url"] == url for f in failures):
            failures.append({"url": url, "error": "response was not an image"})
        continue
    data, ctype, final_url = result
    sha = hashlib.sha256(data).hexdigest()
    if sha in sha_to_path:
        local_path = sha_to_path[sha]
        duplicate_of = local_path
    else:
        ext = extension_for(ctype, final_url or url)
        host = (urlparse(final_url or url).hostname or "unknown").replace("www.", "")
        host_slug = re.sub(r"[^A-Za-z0-9.-]+", "-", host)
        stem = safe_stem_from_url(final_url or url)
        short = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
        rel = Path("assets/images/migrated") / host_slug / f"{stem}--{short}{ext}"
        rel.parent.mkdir(parents=True, exist_ok=True)
        rel.write_bytes(data)
        local_path = rel.as_posix()
        sha_to_path[sha] = local_path
        duplicate_of = None

    manifest_items.append({
        "source_url": url,
        "final_url": final_url,
        "local_path": local_path,
        "content_type": ctype,
        "bytes": len(data),
        "sha256": sha,
        "duplicate_of": duplicate_of,
        "found_on": sorted(image_sources[url]),
    })
    if idx % 25 == 0:
        print(f"Downloaded {idx}/{len(image_sources)} candidates...", flush=True)

manifest = {
    "source_site": START_URL,
    "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "pages_crawled": len(pages_seen),
    "page_limit": MAX_PAGES,
    "crawl_truncated": truncated,
    "image_candidates": len(image_sources),
    "image_urls_archived": len(manifest_items),
    "unique_image_files": len(sha_to_path),
    "failed_images": failures,
    "page_errors": page_errors,
    "images": manifest_items,
}
MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

report_lines = [
    "# Bandzoogle Image Migration Report",
    "",
    f"Generated: `{manifest['generated_utc']}`",
    "",
    f"- Pages crawled: **{len(pages_seen)}**",
    f"- Image URL candidates discovered: **{len(image_sources)}**",
    f"- Image URLs archived: **{len(manifest_items)}**",
    f"- Unique image files saved: **{len(sha_to_path)}**",
    f"- Failed/non-image candidates: **{len(failures)}**",
    f"- Page/CSS crawl errors: **{len(page_errors)}**",
    f"- Crawl truncated at {MAX_PAGES} pages: **{'YES' if truncated else 'NO'}**",
    "",
    "## Archived images",
    "",
    "| Local file | Source | Found on pages |",
    "|---|---|---:|",
]
for item in manifest_items:
    src = item["source_url"].replace("|", "%7C")
    report_lines.append(f"| `{item['local_path']}` | {src} | {len(item['found_on'])} |")

if failures:
    report_lines += ["", "## Failed image candidates", ""]
    for f in failures:
        report_lines.append(f"- `{f['url']}` — {f['error']}")

if page_errors:
    report_lines += ["", "## Page/CSS crawl errors", ""]
    for f in page_errors:
        report_lines.append(f"- `{f['url']}` — {f['error']}")

report_lines += ["", "## Pages crawled", ""]
report_lines.extend(f"- {u}" for u in pages_seen)
REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

print(json.dumps({
    "pages_crawled": len(pages_seen),
    "candidates": len(image_sources),
    "archived_urls": len(manifest_items),
    "unique_files": len(sha_to_path),
    "failures": len(failures),
    "page_errors": len(page_errors),
    "truncated": truncated,
}, indent=2))

# Never fail the workflow just because an individual legacy asset is gone; the
# report is the authoritative list of anything that needs manual recovery.
sys.exit(0)
