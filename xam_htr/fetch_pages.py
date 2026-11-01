"""Download notebook page scans from the Digital Bleek & Lloyd archive.

Usage:
    python3 fetch_pages.py BC_151_A2_1_009 449 452 --out data/raw

Only the low-resolution web images are publicly served (~1350 px per spread).
Check the archive's terms of use before downloading at scale.
"""

import argparse
import time
import urllib.request
from pathlib import Path

BASE_URL = "https://digitalbleeklloyd.uct.ac.za/collection/lloyd_xam_nb_lowres"
POLITE_DELAY_SECONDS = 1.0


def page_prefix(book_id: str) -> str:
    """BC_151_A2_1_009 -> A2_1_9 (the archive drops leading zeros in file names)."""
    series, sub, number = book_id.split("_")[2:5]
    return f"{series}_{int(sub)}_{int(number)}"


def page_filename(book_id: str, page: int) -> str:
    return f"{page_prefix(book_id)}_{page:05d}.JPG"


def page_url(book_id: str, page: int) -> str:
    return f"{BASE_URL}/{book_id}/{page_filename(book_id, page)}"


def download_page(book_id: str, page: int, out_dir: Path) -> Path:
    target = out_dir / page_filename(book_id, page).replace(".JPG", ".jpg")
    if target.exists():
        return target
    with urllib.request.urlopen(page_url(book_id, page), timeout=60) as response:
        target.write_bytes(response.read())
    time.sleep(POLITE_DELAY_SECONDS)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book_id", help="e.g. BC_151_A2_1_009")
    parser.add_argument("first_page", type=int)
    parser.add_argument("last_page", type=int)
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    for page in range(args.first_page, args.last_page + 1):
        print(download_page(args.book_id, page, args.out))


if __name__ == "__main__":
    main()
