"""Load transcription JSON files and split their /Xam text into tokens.

Shared by the report builder and the lexicon database builder, so both
tokenise the corpus the same way.
"""

import json
import re
from pathlib import Path

# Editorial markup and trailing punctuation that are not part of a word.
MARKUP = re.compile(r"[_~^\"]|[.,;:!?](?=\s|$)")
TOKEN = re.compile(r"\[[^\]]*\]|\S+")


def load_pages(paths: list[Path]) -> list[dict]:
    pages = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    return sorted(pages, key=lambda page: page["page"])


def line_tokens(line: dict) -> list[str]:
    return TOKEN.findall(line["xam"])


def xam_tokens(page: dict) -> list[str]:
    return [token for line in page["lines"] for token in line_tokens(line)]


def is_uncertain(token: str) -> bool:
    return "[" in token


def normalise_word(token: str) -> str:
    """Strip editorial markup, punctuation and sentence-initial capitals."""
    return MARKUP.sub("", token).strip("-").lower()
