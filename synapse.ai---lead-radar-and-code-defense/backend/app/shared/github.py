"""
Minimal client for GitHub's supported REST API (https://docs.github.com/rest).

Infrastructure only. It returns exactly what GitHub returned (no defaults, no derived claims) and
raises `GitHubError` with a stable code otherwise. It never clones, downloads or executes code.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from .config import settings

_API_VERSION = "2022-11-28"


class GitHubError(Exception):
    """code: not_found | rate_limited | forbidden | unavailable | invalid_response"""

    def __init__(self, code: str, message: str, *, status: Optional[int] = None):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


@dataclass(frozen=True)
class GitHubRepoSnapshot:
    """Facts GitHub returned for one repository. `None` means GitHub returned no value."""

    github_id: int
    full_name: str
    name: str
    owner_login: str
    owner_avatar_url: Optional[str]
    html_url: str
    description: Optional[str]
    default_branch: Optional[str]
    language: Optional[str]
    languages_bytes: Dict[str, int]
    head_sha: Optional[str]
    stars: int
    forks: int
    open_issues: int
    license_spdx: Optional[str]
    topics: List[str]
    visibility: Optional[str]
    archived: bool
    is_fork: bool
    size_kb: Optional[int]
    created_at: Optional[str]
    pushed_at: Optional[str]
    updated_at: Optional[str]
    fetched_at: datetime = field(default_factory=datetime.utcnow)


class GitHubClient:
    def __init__(
        self,
        *,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        timeout: float = 15.0,
    ):
        self._token = settings.GITHUB_TOKEN if token is None else token
        self._base = (base_url or settings.GITHUB_API_URL).rstrip("/")
        self._transport = transport
        self._timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": _API_VERSION,
            "User-Agent": "synapse-dbingestion",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    @staticmethod
    def _raise_for(resp: httpx.Response, what: str) -> None:
        if resp.status_code == 404:
            raise GitHubError("not_found", f"{what} was not found (or is private).", status=404)
        if resp.status_code in (403, 429):
            remaining = resp.headers.get("x-ratelimit-remaining")
            if remaining == "0" or resp.status_code == 429:
                reset = resp.headers.get("x-ratelimit-reset", "unknown")
                raise GitHubError("rate_limited", f"GitHub rate limit reached (resets at epoch {reset}).", status=resp.status_code)
            raise GitHubError("forbidden", f"GitHub refused access to {what}.", status=resp.status_code)
        if resp.status_code >= 500:
            raise GitHubError("unavailable", f"GitHub is unavailable ({resp.status_code}).", status=resp.status_code)
        if resp.status_code >= 400:
            raise GitHubError("invalid_response", f"GitHub returned {resp.status_code} for {what}.", status=resp.status_code)

    async def fetch_repository(self, owner: str, name: str) -> GitHubRepoSnapshot:
        async with httpx.AsyncClient(
            base_url=self._base, headers=self._headers(), timeout=self._timeout, transport=self._transport
        ) as http:
            try:
                repo_resp = await http.get(f"/repos/{owner}/{name}")
                self._raise_for(repo_resp, f"repository {owner}/{name}")
                repo = repo_resp.json()
                if not isinstance(repo, dict) or "id" not in repo or "full_name" not in repo:
                    raise GitHubError("invalid_response", "GitHub returned an unexpected repository payload.")

                langs_resp = await http.get(f"/repos/{owner}/{name}/languages")
                self._raise_for(langs_resp, f"languages of {owner}/{name}")
                languages = {str(k): int(v) for k, v in (langs_resp.json() or {}).items()}

                head_sha: Optional[str] = None
                branch = repo.get("default_branch")
                if branch:
                    br = await http.get(f"/repos/{owner}/{name}/branches/{branch}")
                    if br.status_code == 200:
                        head_sha = ((br.json() or {}).get("commit") or {}).get("sha")
                    elif br.status_code not in (404, 409):   # empty repository: no head commit, not an error
                        self._raise_for(br, f"branch {branch} of {owner}/{name}")
            except httpx.TransportError as exc:
                raise GitHubError("unavailable", f"Could not reach GitHub ({type(exc).__name__}).") from exc
            except ValueError as exc:                          # malformed JSON
                raise GitHubError("invalid_response", "GitHub returned a body that is not valid JSON.") from exc

        owner_obj: Dict[str, Any] = repo.get("owner") or {}
        license_obj: Dict[str, Any] = repo.get("license") or {}
        return GitHubRepoSnapshot(
            github_id=int(repo["id"]),
            full_name=str(repo["full_name"]),
            name=str(repo.get("name") or name),
            owner_login=str(owner_obj.get("login") or owner),
            owner_avatar_url=owner_obj.get("avatar_url"),
            html_url=str(repo.get("html_url") or f"https://github.com/{owner}/{name}"),
            description=repo.get("description"),
            default_branch=branch,
            language=repo.get("language"),
            languages_bytes=languages,
            head_sha=head_sha,
            stars=int(repo.get("stargazers_count") or 0),
            forks=int(repo.get("forks_count") or 0),
            open_issues=int(repo.get("open_issues_count") or 0),
            license_spdx=license_obj.get("spdx_id"),
            topics=[str(t) for t in (repo.get("topics") or [])],
            visibility=repo.get("visibility"),
            archived=bool(repo.get("archived")),
            is_fork=bool(repo.get("fork")),
            size_kb=repo.get("size"),
            created_at=repo.get("created_at"),
            pushed_at=repo.get("pushed_at"),
            updated_at=repo.get("updated_at"),
        )
