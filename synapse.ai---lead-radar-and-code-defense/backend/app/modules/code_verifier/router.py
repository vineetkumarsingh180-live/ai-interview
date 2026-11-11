"""
Code Verifier module: HTTP routes (URLs unchanged).
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db
from app.shared.errors import ApiError, NotFound, ServiceUnavailable

from .schemas import CandidateRepoDetailResponse, RepoDeleteResponse, RepoSubmissionRequest
from .service import CodeVerifierService
from .code_analyzer import CodeAnalysisRequest, CodeAnalysisResult, analyse_code

router = APIRouter(prefix="/assessment/repo", tags=["Code Verifier"])


@router.post(
    "/submit",
    response_model=CandidateRepoDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a repository for analysis (stored as awaiting_analysis; nothing is scored)",
)
async def submit_repo(submission: RepoSubmissionRequest, db: AsyncSession = Depends(get_db)):
    return await CodeVerifierService.submit_repository(db=db, submission=submission)


@router.get(
    "/recent",
    response_model=List[CandidateRepoDetailResponse],
    summary="Submitted repositories with their measured results, if any (newest first)",
)
async def get_recent_repos(
    limit: int = Query(20, ge=1, le=50),
    include_demo: bool = Query(True, alias="includeDemo", description="Include labelled demo fixtures"),
    db: AsyncSession = Depends(get_db),
):
    return await CodeVerifierService.list_recent_repos(db=db, limit=limit, include_demo=include_demo)


@router.get("/{repo_id}", response_model=CandidateRepoDetailResponse, summary="One repository and its results")
async def get_repo_detail(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = await CodeVerifierService.get_repo_details(db=db, repo_id=repo_id)
    if not repo:
        raise NotFound("Candidate repository not found.")
    return repo


@router.delete(
    "/{repo_id}",
    response_model=RepoDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete or unsubmit a candidate repository",
)
async def delete_repo(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    deleted = await CodeVerifierService.delete_repository(db=db, repo_id=repo_id)
    if not deleted:
        raise NotFound("Candidate repository not found.")
    return RepoDeleteResponse(success=True, repo_id=repo_id)


# ── AI code paste analyzer ────────────────────────────────────────────────────

# Mounted under a separate prefix so it stays clean (not mixed with repo CRUD)
code_analyze_router = APIRouter(prefix="/assessment/code", tags=["Code Verifier"])


@code_analyze_router.post(
    "/analyze",
    response_model=CodeAnalysisResult,
    summary="Paste code and get an AI-powered quality score (uses GEMINI_API_KEY_CODE_VERIFIER)",
)
async def analyze_code_snippet(request: CodeAnalysisRequest):
    """
    Accepts raw code text, calls Gemini with the dedicated Code Verifier API key,
    and returns a structured AI score across 6 quality dimensions.
    """
    return await analyse_code(request)


from pydantic import BaseModel, Field
from .repo_ai_analyzer import analyze_github_repository, RepoAnalysisOutput


class RepoUrlAnalysisRequest(BaseModel):
    repo_url: str = Field(..., description="Public GitHub repository URL")
    candidate_name: Optional[str] = Field(default="Candidate", description="Candidate name")


@router.post(
    "/analyze-url",
    response_model=RepoAnalysisOutput,
    summary="Directly analyze GitHub repository URL using Gemini AI (scores vulgarity, bugs, advance)",
)
async def analyze_repo_url_direct(
    payload: RepoUrlAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Candidate pastes their GitHub repo URL.
    Fetches real code files from GitHub and calls Gemini 3.5 Flash to evaluate:
    - Vulgarity & Code Cleanliness (0-100)
    - Bugs & Vulnerability Safety (0-100)
    - Advanced Engineering Architecture (0-100)
    """
    try:
        ai_out = await analyze_github_repository(payload.repo_url)
    except ValueError as exc:
        raise ApiError(str(exc), status_code=400, code="bad_request")
    except Exception as exc:
        logger.exception("Code Verifier repo analysis encountered an error: %s", exc)
        raise ApiError("Could not complete repository analysis. Please verify the URL and try again.", status_code=500, code="internal_error")

    # Record into database for submissions history and leaderboard
    try:
        cand_name = (payload.candidate_name or "").strip() or ai_out.owner or "Candidate"
        handle = cand_name.lower().replace(" ", "")
        submission = RepoSubmissionRequest(
            candidate_name=cand_name,
            candidate_github_handle=handle,
            repo_url=payload.repo_url,
        )
        await CodeVerifierService.record_analyzed_repo(db=db, submission=submission, ai_out=ai_out)
    except Exception as exc:
        logger.warning("Could not persist repo submission to database: %s", exc)

    return ai_out

