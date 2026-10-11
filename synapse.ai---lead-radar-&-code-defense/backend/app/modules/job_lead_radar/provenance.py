"""
Job Lead Radar: how a post's text is normalised and fingerprinted (business rule owned here).

The ORIGINAL text is always stored unchanged in `raw_posts.raw_content`; normalisation is used only
to compare posts for deduplication.
"""

import hashlib
import re
import unicodedata

_WS = re.compile(r"\s+")


def normalize_post_text(text: str) -> str:
    """Unicode NFC, whitespace runs collapsed to one space, trimmed. Case is preserved."""
    return _WS.sub(" ", unicodedata.normalize("NFC", text)).strip()


def content_hash(platform: str, text: str) -> str:
    """Stable fingerprint of (platform, normalised text)."""
    payload = f"{platform.strip().lower()}\n{normalize_post_text(text)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
