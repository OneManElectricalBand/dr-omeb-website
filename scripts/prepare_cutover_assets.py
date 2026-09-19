from pathlib import Path
import shutil
import sys

from PIL import Image, ImageOps


SOURCE = Path(sys.argv[1])
ROOT = Path(__file__).resolve().parents[1]
GALLERY_SOURCE = SOURCE / "Photo Galleries" / "Vincent DePorters Artwork"
FILE_SOURCE = SOURCE / "Bandzoogle Files"
GALLERY_DEST = ROOT / "assets" / "images" / "album-art"
SITE_DEST = ROOT / "assets" / "images" / "site"
PRESS_DEST = ROOT / "assets" / "images" / "press"


def optimize(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "transparency" in image.info else "RGB")
        image.save(destination, "WEBP", quality=84, method=6)


for source in sorted(GALLERY_SOURCE.iterdir()):
    if source.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        continue
    optimize(source, GALLERY_DEST / f"{source.stem}.webp")

SITE_DEST.mkdir(parents=True, exist_ok=True)
shutil.copy2(
    FILE_SOURCE / "rock-n-roll-church-background.webp",
    SITE_DEST / "rock-n-roll-church-background.webp",
)
shutil.copy2(
    FILE_SOURCE / "rock-n-roll-church-background-mobile.webp",
    SITE_DEST / "rock-n-roll-church-background-mobile.webp",
)
PRESS_DEST.mkdir(parents=True, exist_ok=True)
shutil.copy2(FILE_SOURCE / "pr-image-2.png", PRESS_DEST / "dr-omeb-press-photo.png")
optimize(FILE_SOURCE / "pr-image-2.png", PRESS_DEST / "dr-omeb-press-photo.webp")

print(f"Prepared {len(list(GALLERY_DEST.glob('*.webp')))} gallery images, 2 backgrounds, and press-photo files")
