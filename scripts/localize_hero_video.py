"""One-time, checksum-verified migration of the homepage video to local assets."""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://d1n53z5vgh6uee.cloudfront.net/u/671130/3458d9e1d86d3216293eaffdae8df6a8cd41fbc0/web/8b1364d33ac71f7d30e8177f54248640c04f4c5a.mp4'
CHECKSUM = 'b9f2d5f049eb169c59a67f9b59d397723ff7532e6fa613fd11d01dd104398e0c'
VIDEO_TAG = '''<video id="hero-video" playsinline muted loop preload="none" poster="/assets/video/dr-omeb-hero-poster.webp" width="1280" height="720" aria-label="Dr. OMEB live performance montage" data-desktop-src="/assets/video/dr-omeb-hero-desktop.mp4" data-mobile-src="/assets/video/dr-omeb-hero-mobile.mp4"></video>
<button class="hero-motion" type="button" aria-controls="hero-video" hidden>Play video</button>'''
JS = '''(() => {
  'use strict';
  const video = document.querySelector('#hero-video');
  const button = document.querySelector('.hero-motion');
  if (!video || !button) return;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const update = () => { button.textContent = video.paused ? 'Play video' : 'Pause video'; };
  const play = async () => {
    if (!video.getAttribute('src')) {
      video.src = window.matchMedia('(max-width: 760px)').matches
        ? video.dataset.mobileSrc : video.dataset.desktopSrc;
    }
    try { await video.play(); } catch { /* Keep the poster and manual play control. */ }
    update();
  };
  button.hidden = false;
  button.addEventListener('click', () => { if (video.paused) play(); else video.pause(); });
  video.addEventListener('play', update);
  video.addEventListener('pause', update);
  video.addEventListener('error', () => {
    video.pause();
    video.removeAttribute('src');
    video.load();
    update();
  });
  reducedMotion.addEventListener('change', event => { if (event.matches) video.pause(); });
  if (!reducedMotion.matches && !navigator.connection?.saveData) play();
})();
'''
CSS = '''
/* Local hero playback controls stay clear of the overlapping title card. */
.hero-motion{position:absolute;left:16px;bottom:52px;z-index:3;min-height:44px;padding:8px 16px;border:1px solid var(--line);background:rgba(8,7,7,.92);color:var(--bone);font-size:15px;font-weight:700;cursor:pointer}
.hero-motion[hidden]{display:none}.hero-motion:focus-visible{outline:2px solid var(--gold);outline-offset:3px}
'''


def main():
    page_path = ROOT / 'index.html'
    page = page_path.read_text()
    if 'id="hero-video"' in page:
        required = [ROOT / 'assets/video' / name for name in ['dr-omeb-hero-desktop.mp4', 'dr-omeb-hero-mobile.mp4', 'dr-omeb-hero-poster.webp']]
        if all(p.is_file() for p in required):
            print('Hero already migrated; no changes.')
            return
        raise RuntimeError('Partial migration needs review; refusing to overwrite.')
    pattern = r'<video\b[^>]*>\s*<source\b[^>]*src="' + re.escape(SOURCE) + r'"[^>]*>\s*</video>'
    if len(re.findall(pattern, page)) != 1:
        raise RuntimeError('Expected hero markup changed; refusing to overwrite.')
    with tempfile.TemporaryDirectory() as folder:
        temp = Path(folder)
        source = temp / 'source.mp4'
        local_source = os.environ.get('HERO_SOURCE_FILE')
        if local_source:
            data = Path(local_source).read_bytes()
        else:
            with urllib.request.urlopen(SOURCE, timeout=60) as response:
                data = response.read(20_000_000)
        if hashlib.sha256(data).hexdigest() != CHECKSUM:
            raise RuntimeError('Source checksum mismatch; refusing to publish.')
        source.write_bytes(data)
        for device, crf, scale in [('desktop', '25', []), ('mobile', '26', ['-vf', 'scale=640:360'])]:
            output = temp / f'dr-omeb-hero-{device}.mp4'
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(source), '-an', *scale, '-c:v', 'libx264', '-preset', 'slow', '-crf', crf, '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)], check=True)
            subprocess.run(['ffmpeg', '-v', 'error', '-i', str(output), '-f', 'null', '-'], check=True)
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', '0.8', '-i', str(source), '-frames:v', '1', '-quality', '85', str(temp / 'dr-omeb-hero-poster.webp')], check=True)
        dest = ROOT / 'assets/video'
        dest.mkdir(parents=True, exist_ok=True)
        for asset in temp.glob('dr-omeb-hero-*'):
            (dest / asset.name).write_bytes(asset.read_bytes())
            print(f'{asset.name}: {asset.stat().st_size:,} bytes')
    page = re.sub(pattern, lambda _: VIDEO_TAG, page)
    page = page.replace('</body>', '<script src="/assets/js/hero-video.js" defer></script></body>')
    page_path.write_text(page)
    (ROOT / 'assets/js/hero-video.js').write_text(JS)
    css_path = ROOT / 'assets/css/site.css'
    css_path.write_text(css_path.read_text() + CSS)
    subprocess.run(['node', '--check', str(ROOT / 'assets/js/hero-video.js')], check=True)
    subprocess.run(['python3', str(ROOT / 'scripts/check_site_links.py')], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
