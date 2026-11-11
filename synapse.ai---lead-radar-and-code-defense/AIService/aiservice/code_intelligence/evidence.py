"""
Repository evidence: the ONLY input code and interview intelligence accept.

Repository content is untrusted. Nothing here executes, installs or builds anything; it filters
and bounds data that a caller already holds as text. Sensitive-looking files are excluded before
anything can reach a prompt, and every limit is explicit.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

MAX_FILES = 40
MAX_FILE_CHARS = 12_000
MAX_TOTAL_CHARS = 150_000

_SENSITIVE_NAME = re.compile(
    r"(^|/)(\.env(\..*)?|id_(rsa|dsa|ecdsa|ed25519)|.*\.(pem|key|p12|pfx|jks|keystore)|"
    r"credentials(\.\w+)?|secrets?(\.\w+)?|\.npmrc|\.pypirc|\.netrc|.*\.tfstate)$",
    re.IGNORECASE,
)
_SECRET_CONTENT = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|(?i:api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"\s]{12,}['\"]"
)
_MANIFESTS = {
    "package.json", "requirements.txt", "pyproject.toml", "pipfile", "go.mod", "cargo.toml", "pom.xml",
    "build.gradle", "gemfile", "composer.json", "poetry.lock", "package-lock.json", "yarn.lock",
}
_LANG = {
    ".py": "Python", ".rs": "Rust", ".go": "Go", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript",
    ".jsx": "JavaScript", ".java": "Java", ".kt": "Kotlin", ".c": "C", ".h": "C", ".cpp": "C++", ".cc": "C++",
    ".cs": "C#", ".rb": "Ruby", ".php": "PHP", ".swift": "Swift", ".sql": "SQL", ".sh": "Shell",
}
_TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec)/|(^|/)(test_[^/]+|[^/]+_test\.\w+|[^/]+\.(test|spec)\.\w+)$", re.IGNORECASE)


@dataclass(frozen=True)
class RepositoryFile:
    path: str
    content: str


@dataclass
class RepositoryEvidence:
    """What a caller actually holds about a repository. Empty `files` means nothing was inspected."""

    repo_url: str
    commit_sha: Optional[str] = None
    files: List[RepositoryFile] = field(default_factory=list)
    excluded: Dict[str, str] = field(default_factory=dict)     # path -> reason (never the content)
    truncated: bool = False

    @property
    def paths(self) -> List[str]:
        return [f.path for f in self.files]

    def facts(self) -> Dict[str, object]:
        """Deterministic observations only: counted from the files, with no interpretation."""
        languages: Dict[str, int] = {}
        for f in self.files:
            ext = "." + f.path.rsplit(".", 1)[-1].lower() if "." in f.path.rsplit("/", 1)[-1] else ""
            if ext in _LANG:
                languages[_LANG[ext]] = languages.get(_LANG[ext], 0) + 1
        return {
            "files_inspected": len(self.files),
            "languages_by_file_count": dict(sorted(languages.items(), key=lambda kv: -kv[1])),
            "test_files": [p for p in self.paths if _TEST_PATH.search(p)],
            "dependency_manifests": [p for p in self.paths if p.rsplit("/", 1)[-1].lower() in _MANIFESTS],
            "excluded_files": len(self.excluded),
            "truncated": self.truncated,
        }


def prepare_evidence(repo_url: str, files: Iterable[Tuple[str, str]], *, commit_sha: Optional[str] = None) -> RepositoryEvidence:
    """Apply size limits and exclude sensitive or binary-looking files. `files` is (path, text)."""
    ev = RepositoryEvidence(repo_url=repo_url, commit_sha=commit_sha)
    total = 0
    for path, content in files:
        clean = (path or "").strip().lstrip("/")
        if not clean or ".." in clean.split("/"):
            ev.excluded[path or "(empty)"] = "invalid_path"
        elif _SENSITIVE_NAME.search(clean):
            ev.excluded[clean] = "sensitive_filename"
        elif "\x00" in (content or ""):
            ev.excluded[clean] = "binary"
        elif _SECRET_CONTENT.search(content or ""):
            ev.excluded[clean] = "secret_like_content"
        elif len(ev.files) >= MAX_FILES:
            ev.excluded[clean] = "file_limit"
            ev.truncated = True
        else:
            text = content[:MAX_FILE_CHARS]
            if len(content) > MAX_FILE_CHARS or total + len(text) > MAX_TOTAL_CHARS:
                ev.truncated = True
            if total + len(text) > MAX_TOTAL_CHARS:
                ev.excluded[clean] = "size_limit"
                continue
            total += len(text)
            ev.files.append(RepositoryFile(clean, text))
    return ev


def render_for_prompt(evidence: RepositoryEvidence) -> str:
    return "\n\n".join(f"### FILE: {f.path}\n{f.content}" for f in evidence.files)
