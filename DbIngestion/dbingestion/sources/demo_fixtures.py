"""
Labelled demo showcase, loaded from data files (fixtures/demo/showcase.json), never from Python
literals. It goes through the same pipeline as real input but with is_demo = True and source_type =
demo_fixture, so it can always be told apart from genuine data and removed.
"""

import json
import os
from datetime import datetime, timedelta
from typing import List

from ..validation import DemoCandidateInput, ManualPostInput
from . import SourceItem

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "demo")
SHOWCASE = "showcase.json"


def _load() -> dict:
    with open(os.path.join(FIXTURE_DIR, SHOWCASE), "r", encoding="utf-8") as fh:
        return json.load(fh)


def posts() -> List[SourceItem[ManualPostInput]]:
    now = datetime.utcnow()
    items: List[SourceItem[ManualPostInput]] = []
    for i, rec in enumerate(_load()["leads"]):
        rec = dict(rec)
        minutes = rec.pop("minutes_ago", None)
        value = ManualPostInput(**rec)
        if minutes is not None:
            value.posted_at = now - timedelta(minutes=minutes)
        items.append(SourceItem(i, value=value, raw=rec))
    return items


def candidates() -> List[SourceItem[DemoCandidateInput]]:
    return [SourceItem(i, value=DemoCandidateInput(**rec), raw=rec) for i, rec in enumerate(_load()["candidates"])]
