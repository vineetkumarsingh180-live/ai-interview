"""
GitHub repository source: operator-provided repository URLs, enriched with metadata fetched from
GitHub's supported REST API (see backend app.shared.github). No scraping, no cloning, no code
download or execution.
"""

import json
import os
from typing import List

from pydantic import ValidationError

from ..validation import GithubRepoInput, describe
from . import SourceItem


def _validate(index: int, data: object) -> SourceItem[GithubRepoInput]:
    if isinstance(data, str):
        data = {"repo_url": data}
    if not isinstance(data, dict):
        return SourceItem(index, error_code="invalid_record", error_message="record must be a URL or an object", raw=data)
    try:
        return SourceItem(index, value=GithubRepoInput(**data), raw=data)
    except ValidationError as exc:
        return SourceItem(index, error_code="invalid_input", error_message=describe(exc), raw=data)


def from_urls(urls: List[str], *, candidate_name: str = None, target_role: str = None) -> List[SourceItem[GithubRepoInput]]:
    extra = {k: v for k, v in (("candidate_name", candidate_name), ("target_role", target_role)) if v}
    return [_validate(i, {"repo_url": u, **extra}) for i, u in enumerate(urls)]


def from_file(path: str) -> List[SourceItem[GithubRepoInput]]:
    """A .json file (array of URLs/objects or {"records": [...]}) or a .txt file with one URL per line."""
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    if path.lower().endswith(".txt"):
        urls = [ln.strip() for ln in content.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        return [_validate(i, u) for i, u in enumerate(urls)]
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        return [SourceItem(0, error_code="invalid_json", error_message=f"{os.path.basename(path)}: {exc}")]
    if isinstance(data, dict):
        data = data.get("records")
    if not isinstance(data, list):
        return [SourceItem(0, error_code="invalid_file", error_message='expected a JSON array or {"records": [...]}')]
    return [_validate(i, rec) for i, rec in enumerate(data)]
