"""Code Verifier module public API. Import from here only (never from submodules)."""

from . import models  # noqa: F401  (registers tables with SQLAlchemy metadata)
from .router import router
from .interfaces import RepositoryAnalysis, RepositoryAnalyzer, RepositoryDirectory, get_repository_analyzer
from .ingestion import (
    DemoAnalysis,
    RepoRecord,
    register_demo_analysed_repository,
    delete_repositories,
    parse_github_url,
    register_github_repository,
    register_repository_url,
    reject_repo_url,
)

__all__ = ["router", "RepositoryAnalysis", "RepositoryAnalyzer", "get_repository_analyzer", "RepositoryDirectory", "RepoRecord", "DemoAnalysis", "register_demo_analysed_repository", "parse_github_url", "register_github_repository", "register_repository_url", "reject_repo_url", "delete_repositories"]
