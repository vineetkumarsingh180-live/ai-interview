"""
Code Verifier module: HTTP routes (URLs unchanged).
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db
from app.shared.errors import NotFound

from .schemas import CandidateRepoDetailResponse, RepoSubmissionRequest
from .service import CodeVerifierService

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
async def get_recent_repos(limit: int = Query(20, ge=1, le=50), db: AsyncSession = Depends(get_db)):
    return await CodeVerifierService.list_recent_repos(db=db, limit=limit)


@router.get("/{repo_id}", response_model=CandidateRepoDetailResponse, summary="One repository and its results")
async def get_repo_detail(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = await CodeVerifierService.get_repo_details(db=db, repo_id=repo_id)
    if not repo:
        raise NotFound("Candidate repository not found.")
    return repo
