"""Build a SQLite lexicon database from the transcription JSON files.

The JSON transcriptions are the source of truth; the database is rebuilt from
scratch on every run. Do not edit it by hand: anything added directly to the
database (glosses, notes) is lost on the next build.

Tables:
    pages         one row per notebook page, with source metadata
    lines         ruled lines: English column, /Xam column (Lloyd's spelling)
    tokens        every /Xam token in reading order, with its IPA
    lexemes       distinct word forms (Lloyd's spelling), with IPA and gloss
    token_issues  why a token's IPA conversion is unresolved
    concordance   view: every token with its line, page and story

Usage:
    python3 xam_htr/build_lexicon_db.py transcriptions/*.json --out lexicon.sqlite
"""

import argparse
import sqlite3
from pathlib import Path

from corpus import is_uncertain, line_tokens, load_pages, normalise_word
from fetch_pages import page_url
from to_ipa import to_ipa, unresolved

SCHEMA = """
CREATE TABLE pages (
    id             INTEGER PRIMARY KEY,
    notebook       TEXT    NOT NULL,
    notebook_label TEXT,
    page           INTEGER NOT NULL,
    collector      TEXT,
    narrator       TEXT,
    story          TEXT,
    transcriber    TEXT,
    image_url      TEXT,
    UNIQUE (notebook, page)
);

CREATE TABLE lines (
    id          INTEGER PRIMARY KEY,
    page_id     INTEGER NOT NULL REFERENCES pages (id),
    n           INTEGER NOT NULL,
    english     TEXT,
    xam         TEXT,
    interlinear INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE lexemes (
    id     INTEGER PRIMARY KEY,
    lloyd  TEXT NOT NULL UNIQUE,   -- Lloyd's spelling, markup removed
    ipa    TEXT NOT NULL,          -- Naumann (2016) IPA, see to_ipa.py
    gloss  TEXT,                   -- to be filled in by a linguist
    notes  TEXT
);

CREATE TABLE tokens (
    id        INTEGER PRIMARY KEY,
    line_id   INTEGER NOT NULL REFERENCES lines (id),
    position  INTEGER NOT NULL,    -- 1-based position within the line
    surface   TEXT    NOT NULL,    -- exactly as transcribed, with markup
    ipa       TEXT    NOT NULL,
    uncertain INTEGER NOT NULL,
    lexeme_id INTEGER REFERENCES lexemes (id)  -- NULL for uncertain readings
);

CREATE TABLE token_issues (
    token_id INTEGER NOT NULL REFERENCES tokens (id),
    issue    TEXT    NOT NULL
);

CREATE INDEX tokens_lexeme ON tokens (lexeme_id);

CREATE VIEW concordance AS
SELECT lexemes.lloyd, lexemes.ipa AS lexeme_ipa, lexemes.gloss,
       tokens.surface, tokens.uncertain,
       pages.notebook, pages.page, lines.n AS line,
       lines.xam AS xam_line, lines.english AS english_line,
       pages.story, pages.narrator, pages.image_url
FROM tokens
JOIN lines ON lines.id = tokens.line_id
JOIN pages ON pages.id = lines.page_id
LEFT JOIN lexemes ON lexemes.id = tokens.lexeme_id;
"""


def insert_page(db: sqlite3.Connection, page: dict) -> int:
    cursor = db.execute(
        "INSERT INTO pages (notebook, notebook_label, page, collector, narrator,"
        " story, transcriber, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (page["notebook"], page.get("notebook_label"), page["page"],
         page.get("collector"), page.get("narrator"), page.get("story"),
         page.get("transcriber"), page_url(page["notebook"], page["page"])),
    )
    return cursor.lastrowid


def insert_line(db: sqlite3.Connection, page_id: int, line: dict) -> int:
    cursor = db.execute(
        "INSERT INTO lines (page_id, n, english, xam, interlinear) VALUES (?, ?, ?, ?, ?)",
        (page_id, line["n"], line["english"], line["xam"], line.get("interlinear", False)),
    )
    return cursor.lastrowid


def lexeme_id(db: sqlite3.Connection, word: str) -> int:
    db.execute("INSERT OR IGNORE INTO lexemes (lloyd, ipa) VALUES (?, ?)",
               (word, to_ipa(word)))
    return db.execute("SELECT id FROM lexemes WHERE lloyd = ?", (word,)).fetchone()[0]


def insert_token(db: sqlite3.Connection, line_id: int, position: int, token: str) -> None:
    uncertain = is_uncertain(token)
    word = normalise_word(token)
    lexeme = None if uncertain or not word else lexeme_id(db, word)
    cursor = db.execute(
        "INSERT INTO tokens (line_id, position, surface, ipa, uncertain, lexeme_id)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (line_id, position, token, to_ipa(token), uncertain, lexeme),
    )
    db.executemany("INSERT INTO token_issues (token_id, issue) VALUES (?, ?)",
                   [(cursor.lastrowid, issue) for issue in unresolved(token)])


def build_database(pages: list[dict], target: Path) -> None:
    target.unlink(missing_ok=True)
    with sqlite3.connect(target) as db:
        db.executescript(SCHEMA)
        for page in pages:
            page_id = insert_page(db, page)
            for line in page["lines"]:
                line_id = insert_line(db, page_id, line)
                for position, token in enumerate(line_tokens(line), start=1):
                    insert_token(db, line_id, position, token)
    db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("transcriptions", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, default=Path("lexicon.sqlite"))
    args = parser.parse_args()

    build_database(load_pages(args.transcriptions), args.out)
    print(args.out)


if __name__ == "__main__":
    main()
