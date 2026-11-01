"""Summarise transcription JSON files into a Markdown report.

The report contains running parallel text (English / /Xam in Lloyd's spelling
and in IPA), uncertainty statistics, unresolved IPA conversions and a seed
word list for building a lexicon.

Usage:
    python3 xam_htr/build_report.py transcriptions/*.json --out report.md
"""

import argparse
import re
from collections import Counter
from pathlib import Path

from corpus import is_uncertain, load_pages, normalise_word, xam_tokens
from to_ipa import to_ipa, unresolved

CLICK_LETTERS = "ʘǀǃǂ×"


def running_text(page: dict, column: str) -> str:
    text = " ".join(line[column] for line in page["lines"] if line[column])
    return re.sub(r"-\s+", "", text)


def parallel_section(page: dict) -> str:
    return "\n".join([
        f"### Page {page['page']}",
        "",
        f"**English:** {running_text(page, 'english')}",
        "",
        f"**/Xam (Lloyd):** {running_text(page, 'xam')}",
        "",
        f"**/Xam (IPA):** {to_ipa(running_text(page, 'xam'))}",
        "",
    ])


def statistics_section(pages: list[dict]) -> str:
    rows = ["| Page | /Xam tokens | Uncertain | % |", "|---|---|---|---|"]
    for page in pages:
        tokens = xam_tokens(page)
        uncertain = sum(map(is_uncertain, tokens))
        rows.append(f"| {page['page']} | {len(tokens)} | {uncertain} | "
                    f"{100 * uncertain / len(tokens):.0f}% |")
    return "\n".join(rows)


def click_section(pages: list[dict]) -> str:
    text = "".join(line["xam"] for page in pages for line in page["lines"])
    counts = Counter(char for char in text if char in CLICK_LETTERS)
    return "\n".join(f"- `{char}`: {count}" for char, count in counts.most_common())


def word_list_section(pages: list[dict]) -> str:
    words = Counter(
        normalise_word(token)
        for page in pages
        for token in xam_tokens(page)
        if not is_uncertain(token)
    )
    words.pop("", None)
    return "\n".join(f"| {word} | {to_ipa(word)} | {count} |"
                     for word, count in words.most_common())


def unresolved_section(pages: list[dict]) -> str:
    reasons = Counter(
        reason
        for page in pages
        for token in xam_tokens(page)
        for reason in unresolved(token)
    )
    return "\n".join(f"| {reason} | {count} |" for reason, count in reasons.most_common())


def build_report(pages: list[dict]) -> str:
    return "\n".join([
        "# /Xam transcription prototype: report",
        "",
        "## Parallel text",
        "",
        *map(parallel_section, pages),
        "## Uncertainty",
        "",
        statistics_section(pages),
        "",
        "## Click letters used",
        "",
        click_section(pages),
        "",
        "## Unresolved IPA conversions (need a specialist)",
        "",
        "| Issue | Tokens |",
        "|---|---|",
        unresolved_section(pages),
        "",
        "## Seed word list (certain readings only)",
        "",
        "| Lloyd | IPA | Count |",
        "|---|---|---|",
        word_list_section(pages),
        "",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcriptions", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, default=Path("report.md"))
    args = parser.parse_args()

    args.out.write_text(build_report(load_pages(args.transcriptions)), encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
