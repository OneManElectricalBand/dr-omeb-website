from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
import re


ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for attr in ("href", "src"):
            if attr in values:
                self.values.append((tag, attr, values[attr]))


def local_target(source: Path, value: str):
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or value.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    path = unquote(parsed.path)
    if not path:
        return None
    target = ROOT / path.lstrip("/") if path.startswith("/") else source.parent / path
    if path.endswith("/"):
        target = target / "index.html"
    elif not target.suffix and target.is_dir():
        target = target / "index.html"
    return target.resolve()


errors = []
html_files = sorted(ROOT.rglob("*.html"))
for source in html_files:
    parser = Links()
    parser.feed(source.read_text(encoding="utf-8"))
    for tag, attr, value in parser.values:
        target = local_target(source, value)
        if target is not None and not target.exists():
            errors.append(f"{source.relative_to(ROOT)}: missing {tag} {attr}={value}")

for source in sorted(ROOT.rglob("*.css")):
    content = source.read_text(encoding="utf-8")
    for value in re.findall(r"url\(['\"]?([^)'\"]+)", content):
        target = local_target(source, value)
        if target is not None and not target.exists():
            errors.append(f"{source.relative_to(ROOT)}: missing CSS url={value}")

if errors:
    raise SystemExit("\n".join(errors))

print(f"Checked {len(html_files)} HTML pages and local CSS references; no missing local targets.")
