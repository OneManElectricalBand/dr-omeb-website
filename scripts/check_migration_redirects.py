"""Check migrated links reach real pages/anchors and retired URLs stay retired."""
from pathlib import Path
from urllib.parse import urlsplit
import re

ROOT = Path(__file__).resolve().parents[1]
rules = []
seen = set()
for line in (ROOT / '_redirects').read_text().splitlines():
    if not line.strip() or line.startswith('#'):
        continue
    source, destination, status = line.split()
    assert source not in seen, f'Duplicate source: {source}'
    assert status in {'301', '302', '303', '307', '308'}, line
    assert len(line) <= 1000, line
    seen.add(source)
    rules.append((source, destination))
    target = urlsplit(destination)
    if not target.netloc:
        file = ROOT / target.path.lstrip('/')
        if target.path.endswith('/'):
            file /= 'index.html'
        assert file.is_file(), f'Missing destination: {destination}'
        if target.fragment:
            assert re.search(r'id=[\"\']' + re.escape(target.fragment) + r'[\"\']', file.read_text()), destination

def resolve(path):
    for source, destination in rules:
        pattern = re.escape(source).replace(r'\*', '.*')
        if re.fullmatch(pattern, path):
            return destination
    return None

# Independent regression examples: duplicate IDs, slug variants and the clicked 404.
expected = {
    '/track/3234141/johanna-ft-bobby-mackey': '/music/#johanna',
    '/track/3234178/johanna-ft-bobby-mackey/': '/music/#johanna',
    '/track/3234136/calling-doctor-love': '/music/#calling-dr-love',
    '/track/3234182/nights-in-white-satin': '/music/#nights-in-white-satin',
    '/track/3234177/close-my-eyes-forever': '/music/#close-my-eyes-forever',
    '/track/4837303': '/music/#symptom-of-the-universe',
    '/blogs/diary-of-a-rock-n-roll-doctor.rss': '/blog/feed.xml',
    '/blog/blog_posts': '/blog/',
    '/blog/blog/7334700/deck-the-war-pigs-a-christmas-parody': '/music/#deck-the-war-pigs',
    '/blogs/diary-of-a-rock-n-roll-doctor/posts/7762077/your-brand-is-losing-a-war-for-attention-kiss-figured-out-how-to-win-it-50-years-ago': '/blog/kiss-war-for-attention/',
}
for source, destination in expected.items():
    assert resolve(source) == destination, source
for source in ['/index.php', '/event/5501294/674636966/anderson-township-pub-atp', '/blog/blog/7524996/marketing-that-rocks-w-dr-c-february-2025-edition', '/track/9999999/unknown', '/an-unknown-page']:
    assert resolve(source) is None, f'Unrelated redirect: {source}'
assert sum('*' in source for source, _ in rules) <= 100
assert len([s for s in seen if re.fullmatch(r'/track/\d+', s)]) == 22
print(f'Checked {len(rules)} redirects: valid destinations/anchors, 22 track IDs, preserved articles, intentional 404s.')
