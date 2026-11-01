"""Convert diplomatic /Xam transcriptions (Lloyd's orthography) to IPA.

Target notation: the IPA representation of Naumann (2016), "The phoneme
inventory of Taa (West !Xoon dialect)", Table 1, with click accompaniments
analysed as consonant clusters following Güldemann (2001) and Naumann:
plain ǀ, voiced ǀ̬, aspirated ǀʰ, nasal ǀ̃, cluster click + uvular ǀχ.

Every mapping rule carries a status: "confident" rules follow standard readings
of the Bleek–Lloyd orthography; "hypothesis" rules need confirmation by a
specialist. Sequences without a rule pass through unchanged and are reported by
`unresolved()` so they can be decided on explicitly.

Editorial markup (_ ~~ ^ [ ] ?) passes through untouched.
"""

import re
import unicodedata
from dataclasses import dataclass

MACRON = "̄"           # Lloyd: long vowel
BREVE = "̆"            # Lloyd: short vowel (IPA extra-short, kept)
X_BELOW = "͓"          # Lloyd: small x under a letter
IPA_LONG = "ː"         # ː
IPA_ASPIRATED = "ʰ"    # ʰ
IPA_EJECTIVE = "ʼ"     # ʼ
IPA_NASAL = "̃"        # ◌̃  on the click letter (Naumann Table 1)
IPA_VOICED = "̬"       # ◌̬  stands in for Naumann's voiced-click glyphs
IPA_UVULAR_FRICATIVE = "χ"  # χ  (Naumann's orthographic <x>)

CLICKS = "ʘǀǃǂǁ"   # ʘ ǀ ǃ ǂ ǁ
VOWELS = "aeiou"
COMBINING_MARKS = "̀-ͯ"


@dataclass(frozen=True)
class Rule:
    lloyd: str
    ipa: str
    status: str


# What follows a click letter in Lloyd's spelling marks the click type.
# {click} is replaced by the click letter itself.
CLICK_RULES = [
    Rule("k" + X_BELOW, "{click}" + IPA_UVULAR_FRICATIVE, "hypothesis"),  # ǀχ cluster
    Rule("kh", "{click}" + IPA_ASPIRATED, "hypothesis"),  # ǀʰ, or cluster ǀ+kʰ?
    Rule("k", "{click}", "confident"),                    # ǀ  plain click
    Rule("n", "{click}" + IPA_NASAL, "confident"),        # ǀ̃  nasal click
    Rule("g", "{click}" + IPA_VOICED, "confident"),       # ǀ̬  voiced click
    Rule("", "{click}", "hypothesis"),                    # bare click read as plain
]

# Ordinary consonant spellings, longest first.
SEGMENT_RULES = [
    Rule("k" + X_BELOW, IPA_UVULAR_FRICATIVE, "hypothesis"),  # χ
    Rule("kh", "k" + IPA_ASPIRATED, "confident"),             # kʰ
    Rule("tt", "t" + IPA_EJECTIVE, "hypothesis"),             # tʼ  Lloyd's doubled t
    Rule("ng", "ŋ", "confident"),                        # ŋ
    Rule("ss", "s", "hypothesis"),                            # Lloyd's doubled s
    Rule("y", "j", "confident"),                              # j
]

# Lloyd spellings whose IPA value is still open.
UNRESOLVED_SPELLINGS = {
    "wh": "wh: Naumann 2016 has w and h but no hʷ/ʍ; w + h?",
    "×": "unidentified × glyph",
    "ʂ": "s with hook: Lloyd's or the transcriber's?",
}

CLICK_PATTERN = re.compile(
    f"([{CLICKS}])(" + "|".join(re.escape(r.lloyd) for r in CLICK_RULES if r.lloyd) + ")?"
)
SEGMENT_PATTERN = re.compile("|".join(re.escape(r.lloyd) for r in SEGMENT_RULES))
VOWEL_PATTERN = re.compile(f"([{VOWELS}])([{COMBINING_MARKS}]*)")
CONFLICTING_LENGTH = re.compile(
    f"[{VOWELS}][{COMBINING_MARKS}]*{MACRON}[{COMBINING_MARKS}]*{BREVE}"
    f"|[{VOWELS}][{COMBINING_MARKS}]*{BREVE}[{COMBINING_MARKS}]*{MACRON}"
)


def _convert_click(match: re.Match) -> str:
    click, accompaniment = match.group(1), match.group(2) or ""
    rule = next(r for r in CLICK_RULES if r.lloyd == accompaniment)
    return rule.ipa.format(click=click)


def _convert_segment(match: re.Match) -> str:
    return next(r.ipa for r in SEGMENT_RULES if r.lloyd == match.group(0))


def _convert_vowel(match: re.Match) -> str:
    """Lloyd's macron (length) becomes IPA ː after the vowel; other marks stay."""
    vowel, marks = match.group(1), match.group(2)
    if MACRON not in marks or BREVE in marks:
        return vowel + marks
    return vowel + marks.replace(MACRON, "") + IPA_LONG


def to_ipa(lloyd_text: str) -> str:
    text = unicodedata.normalize("NFD", lloyd_text)
    text = CLICK_PATTERN.sub(_convert_click, text)
    text = SEGMENT_PATTERN.sub(_convert_segment, text)
    text = VOWEL_PATTERN.sub(_convert_vowel, text)
    return unicodedata.normalize("NFC", text)


def unresolved(lloyd_text: str) -> list[str]:
    """Reasons why parts of this text could not be converted with confidence."""
    text = unicodedata.normalize("NFD", lloyd_text)
    reasons = [reason for spelling, reason in UNRESOLVED_SPELLINGS.items()
               if spelling in text]
    if CONFLICTING_LENGTH.search(text):
        reasons.append("vowel with both macron and breve: length unclear, kept as written")
    return reasons
