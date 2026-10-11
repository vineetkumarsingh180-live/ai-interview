"""
Manual job-post source: text the operator provides themselves.

Inputs: a JSON array / {"records": [...]}, a JSON-lines file, a plain .txt file (the whole file is
one post), or `--text`. Nothing is fetched from any website. The text is passed through unchanged.
"""

import json
import os
from typing import Iterator, List, Optional

from pydantic import ValidationError

from ..validation import ManualPostInput, describe
from . import SourceItem


def _validate(index: int, data: object) -> SourceItem[ManualPostInput]:
    if not isinstance(data, dict):
        return SourceItem(index, error_code="invalid_record", error_message="record must be a JSON object", raw=data)
    try:
        return SourceItem(index, value=ManualPostInput(**data), raw=data)
    except ValidationError as exc:
        return SourceItem(index, error_code="invalid_input", error_message=describe(exc), raw=data)
    except TypeError as exc:
        return SourceItem(index, error_code="invalid_input", error_message=str(exc), raw=data)


def from_text(text: str, platform: str, **fields) -> List[SourceItem[ManualPostInput]]:
    return [_validate(0, {"platform": platform, "text": text, **fields})]


def from_file(path: str, *, platform: Optional[str] = None, **fields) -> List[SourceItem[ManualPostInput]]:
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()

    if ext == ".txt":
        if not platform:
            return [SourceItem(0, error_code="missing_platform", error_message="--platform is required for a .txt file")]
        return [_validate(0, {"platform": platform, "text": content, **fields})]

    items: List[SourceItem[ManualPostInput]] = []
    if ext == ".jsonl":
        for i, line in enumerate(content.splitlines()):
            if not line.strip():
                continue
            try:
                items.append(_validate(i, json.loads(line)))
            except json.JSONDecodeError as exc:
                items.append(SourceItem(i, error_code="invalid_json", error_message=str(exc)))
        return items

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        return [SourceItem(0, error_code="invalid_json", error_message=f"{os.path.basename(path)}: {exc}")]
    if isinstance(data, dict):
        data = data.get("records")
    if not isinstance(data, list):
        return [SourceItem(0, error_code="invalid_file", error_message='expected a JSON array or {"records": [...]}')]
    return [_validate(i, rec) for i, rec in enumerate(data)]


def iter_valid(items: List[SourceItem[ManualPostInput]]) -> Iterator[SourceItem[ManualPostInput]]:
    return (i for i in items if i.value is not None)
