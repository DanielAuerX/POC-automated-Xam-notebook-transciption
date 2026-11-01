"""Cut notebook spreads into single written pages and upscale them for reading.

Each scan shows an open notebook (two pages). Often only one page carries
writing, so pages with too little ink are skipped.

Usage:
    python3 crop_pages.py data/raw/*.jpg --out data/pages
"""

import argparse
from pathlib import Path

from PIL import Image

INK_THRESHOLD = 110          # grey level below which a pixel counts as ink
MIN_INK_FRACTION = 0.01      # pages with less ink than this are treated as blank
UPSCALE_FACTOR = 2


def ink_fraction(page: Image.Image) -> float:
    grey = page.convert("L")
    histogram = grey.histogram()
    dark_pixels = sum(histogram[:INK_THRESHOLD])
    return dark_pixels / (grey.width * grey.height)


def split_spread(spread: Image.Image) -> dict[str, Image.Image]:
    middle = spread.width // 2
    return {
        "L": spread.crop((0, 0, middle, spread.height)),
        "R": spread.crop((middle, 0, spread.width, spread.height)),
    }


def written_pages(spread_path: Path) -> dict[str, Image.Image]:
    halves = split_spread(Image.open(spread_path))
    return {side: page for side, page in halves.items()
            if ink_fraction(page) >= MIN_INK_FRACTION}


def upscale(page: Image.Image) -> Image.Image:
    size = (page.width * UPSCALE_FACTOR, page.height * UPSCALE_FACTOR)
    return page.resize(size, Image.LANCZOS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spreads", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, default=Path("data/pages"))
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    for spread_path in args.spreads:
        for side, page in written_pages(spread_path).items():
            target = args.out / f"{spread_path.stem}_{side}.png"
            upscale(page).save(target)
            print(target)


if __name__ == "__main__":
    main()
