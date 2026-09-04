#!/usr/bin/env python3
"""Finalize and validate the native Doctor's Notes review build, then remove bootstrap files."""
from __future__ import annotations

import hashlib
import json
import re
import runpy
import subprocess
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(".")
PARTS = [ROOT / f"scripts/.doctors-notes-payload-{index}.txt" for index in range(1, 6)]
LOADER = ROOT / "scripts/.generate-doctors-notes-once.py"
EXPECTED_PAYLOAD_SHA = "994ce5736e6db3cf3d1d768120d60c18d87610961555d3781faa65730c2ae6b1"
EXPECTED_FIRST_LENGTH = 8500
EXPECTED_SLUGS = {
    "how-tiktok-livestreaming-rewired-my-marketing-brain",
    "nobody-owes-you-attention",
    "streaming-royalties-better-room",
    "tiktok-ads-experiment",
    "kiss-war-for-attention",
    "ai-does-not-replace-taste",
    "ai-music-video-independent-artist",
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.h1_count = 0
        self.canonicals: list[str] = []
        self.images: list[tuple[str, str | None]] = []
        self.links: list[str] = []
        self.og_title = False
        self.og_description = False
        self.json_ld: list[str] = []
        self._inside_json_ld = False
        self._json_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = dict(attrs_list)
        if tag == "h1":
            self.h1_count += 1
        if tag == "link" and attrs.get("rel") == "canonical" and attrs.get("href"):
            self.canonicals.append(str(attrs["href"]))
        if tag == "meta" and attrs.get("property") == "og:title":
            self.og_title = bool(attrs.get("content"))
        if tag == "meta" and attrs.get("property") == "og:description":
            self.og_description = bool(attrs.get("content"))
        if tag == "img" and attrs.get("src"):
            self.images.append((str(attrs["src"]), attrs.get("alt")))
        if tag == "a" and attrs.get("href"):
            self.links.append(str(attrs["href"]))
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self._inside_json_ld = True
            self._json_chunks = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._inside_json_ld:
            self.json_ld.append("".join(self._json_chunks).strip())
            self._inside_json_ld = False

    def handle_data(self, data: str) -> None:
        if self._inside_json_ld:
            self._json_chunks.append(data)


def normalize_payload() -> None:
    missing = [str(path) for path in [*PARTS, LOADER] if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing bootstrap files: {', '.join(missing)}")

    first = PARTS[0].read_text(encoding="utf-8")
    tail = "".join(path.read_text(encoding="utf-8") for path in PARTS[1:])
    payload = first + tail
    if hashlib.sha256(payload.encode("utf-8")).hexdigest() == EXPECTED_PAYLOAD_SHA:
        return

    if len(first) < EXPECTED_FIRST_LENGTH:
        raise RuntimeError("The first staged payload segment is shorter than expected.")
    corrected_first = first[:EXPECTED_FIRST_LENGTH]
    corrected_payload = corrected_first + tail
    corrected_sha = hashlib.sha256(corrected_payload.encode("utf-8")).hexdigest()
    if corrected_sha != EXPECTED_PAYLOAD_SHA:
        raise RuntimeError(f"Unable to restore staged payload; checksum was {corrected_sha}.")
    PARTS[0].write_text(corrected_first, encoding="utf-8")
    print(f"Normalized the first payload segment to {EXPECTED_FIRST_LENGTH} characters.")


def add_terms_social_metadata() -> None:
    path = ROOT / "terms/index.html"
    text = path.read_text(encoding="utf-8")
    if 'property="og:title"' in text and 'property="og:description"' in text:
        return
    marker = "</head>"
    if marker not in text:
        raise RuntimeError("Could not locate the Terms page head element.")
    metadata = (
        '<meta property="og:title" content="Terms &amp; Privacy | Dr. OMEB®">'
        '<meta property="og:description" content="Terms of use and privacy information for the official Dr. OMEB website.">'
        '<meta property="og:type" content="website">'
        '<meta property="og:url" content="https://onemanelectricalband.com/terms/">'
    )
    path.write_text(text.replace(marker, metadata + marker, 1), encoding="utf-8")
    print("Added complete social-sharing metadata to the Terms page.")


def validate() -> None:
    errors: list[str] = []
    article_pages = sorted((ROOT / "blog").glob("*/index.html"))
    actual_slugs = {path.parent.name for path in article_pages}
    if actual_slugs != EXPECTED_SLUGS:
        errors.append(f"Article slugs mismatch: {sorted(actual_slugs)}")

    pages = [ROOT / "blog/index.html", ROOT / "terms/index.html", *article_pages]
    for path in pages:
        if not path.exists():
            errors.append(f"Missing page: {path}")
            continue
        parser = PageParser()
        parser.feed(path.read_text(encoding="utf-8"))
        if parser.h1_count != 1:
            errors.append(f"{path}: expected one H1, found {parser.h1_count}")
        if len(parser.canonicals) != 1:
            errors.append(f"{path}: expected one canonical link")
        if not parser.og_title or not parser.og_description:
            errors.append(f"{path}: missing Open Graph title or description")
        if path in article_pages:
            if not parser.json_ld:
                errors.append(f"{path}: missing JSON-LD")
            else:
                try:
                    data = json.loads(parser.json_ld[0])
                    if data.get("@type") != "BlogPosting":
                        errors.append(f"{path}: JSON-LD is not BlogPosting")
                except Exception as exc:
                    errors.append(f"{path}: invalid JSON-LD ({exc})")
        for src, alt in parser.images:
            if not alt or not alt.strip():
                errors.append(f"{path}: image missing alt text: {src}")
            if src.startswith("/") and not (ROOT / src.lstrip("/")).exists():
                errors.append(f"{path}: missing local image: {src}")
        for href in parser.links:
            if not href.startswith("/blog/") or href in {"/blog/", "/blog/rss.xml"}:
                continue
            target = ROOT / urlparse(href).path.lstrip("/")
            exists = target.exists() if target.suffix else (target / "index.html").exists()
            if not exists:
                errors.append(f"{path}: broken internal blog link: {href}")

    feed = ET.parse(ROOT / "blog/rss.xml").getroot()
    items = feed.findall("./channel/item")
    if len(items) != 7:
        errors.append(f"RSS expected 7 items, found {len(items)}")
    for item in items:
        if not item.findtext("title") or not item.findtext("link") or not item.findtext("pubDate"):
            errors.append("RSS item missing title, link or pubDate")

    sitemap = ET.parse(ROOT / "sitemap.xml").getroot()
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = [node.text for node in sitemap.findall("sm:url/sm:loc", namespace)]
    if len(locations) != 16:
        errors.append(f"Sitemap expected 16 URLs, found {len(locations)}")
    for slug in EXPECTED_SLUGS:
        expected = f"https://onemanelectricalband.com/blog/{slug}/"
        if expected not in locations:
            errors.append(f"Sitemap missing {expected}")

    redirects = (ROOT / "_redirects").read_text(encoding="utf-8")
    for slug in EXPECTED_SLUGS:
        if f"/blog/{slug}/" not in redirects:
            errors.append(f"Redirect file missing destination for {slug}")

    for path in (ROOT / "blog/index.html", ROOT / "README.md", ROOT / "terms/index.html"):
        if "Substack" in path.read_text(encoding="utf-8"):
            errors.append(f"{path}: obsolete Substack language remains")

    if errors:
        raise RuntimeError("\n".join(errors))

    subprocess.run(["git", "diff", "--check"], check=True)
    print("VALIDATION PASS")
    print(f"HTML pages checked: {len(pages)}")
    print(f"Article pages: {len(article_pages)}")
    print(f"RSS items: {len(items)}")
    print(f"Sitemap URLs: {len(locations)}")


def remove_bootstrap_files() -> None:
    paths = [
        *PARTS,
        LOADER,
        ROOT / "scripts/.finalize-doctors-notes-once.py",
        ROOT / ".github/workflows/build-native-doctors-notes-once.yml",
        ROOT / ".github/workflows/finalize-native-doctors-notes-once.yml",
    ]
    for path in paths:
        path.unlink(missing_ok=True)
    print("Removed one-time bootstrap and workflow files.")


def main() -> None:
    normalize_payload()
    runpy.run_path(str(LOADER), run_name="__main__")
    add_terms_social_metadata()
    validate()
    remove_bootstrap_files()


if __name__ == "__main__":
    main()
