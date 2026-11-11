"""Small deterministic text helpers used to verify AI output against its source text."""

import re
import unicodedata
from typing import Set

_WS = re.compile(r"\s+")
_NUM = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*([kKmM])?(?![\w])")


def normalize(text: str) -> str:
    """NFC + collapsed whitespace + casefold: the form used for substring evidence checks."""
    return _WS.sub(" ", unicodedata.normalize("NFC", text or "")).strip().casefold()


def contains_quote(source: str, quote: str) -> bool:
    """True when `quote` (non-trivial) occurs verbatim, ignoring case and whitespace, in `source`."""
    q = normalize(quote)
    return len(q) >= 3 and q in normalize(source)


def contains_term(source: str, term: str) -> bool:
    t = normalize(term)
    return bool(t) and t in normalize(source)


def numbers_in(text: str) -> Set[float]:
    """Every number the text states, with k/m suffixes expanded (e.g. "$220k" -> 220000)."""
    found: Set[float] = set()
    for raw, suffix in _NUM.findall(text or ""):
        try:
            value = float(raw.replace(",", ""))
        except ValueError:
            continue
        mult = {"k": 1_000, "m": 1_000_000}.get(suffix.lower(), 1) if suffix else 1
        found.add(value * mult)
        found.add(value)
    return found
