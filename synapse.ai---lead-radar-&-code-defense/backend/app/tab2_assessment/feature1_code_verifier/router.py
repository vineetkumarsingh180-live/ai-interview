"""
FastAPI Modular Router for Code Verifier & LLM Grader (Tab 2, Feature 1)
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.tab2_assessment.feature1_code_verifier.schemas import (
    RepoSubmissionRequest,
    CandidateRepoDetailResponse,
)
from app.tab2_assessment.feature1_code_verifier.service import CodeVerifierService

router = APIRouter(prefix="/assessment/repo", tags=["Tab 2 - Code Verifier"])

@router.post(
    "/submit",
    response_model=CandidateRepoDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit candidate repository for sandbox AST benchmarking and LLM architecture grading"
)
async def submit_repo(
    submission: RepoSubmissionRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        repo = await CodeVerifierService.evaluate_repository(db=db, submission=submission)
        detailed_repo = await CodeVerifierService.get_repo_details(db=db, repo_id=repo.id)
        return detailed_repo
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Repo evaluation failed: {str(e)}"
        )

@router.get(
    "/recent",
    response_model=List[CandidateRepoDetailResponse],
    summary="Retrieve verified candidate repositories with benchmark metrics"
)
async def get_recent_repos(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    return await CodeVerifierService.list_recent_repos(db=db, limit=limit)

@router.get(
    "/{repo_id}",
    response_model=CandidateRepoDetailResponse,
    summary="Get repository detailed evaluation report"
)
async def get_repo_detail(
    repo_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    repo = await CodeVerifierService.get_repo_details(db=db, repo_id=repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Candidate repository not found")
    return repo
