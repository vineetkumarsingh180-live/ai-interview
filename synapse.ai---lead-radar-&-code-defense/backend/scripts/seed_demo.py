#!/usr/bin/env python3
"""
Insert a few clearly labelled development fixtures (is_demo = true). Never run automatically.

    python scripts/seed_demo.py            # add fixtures (idempotent)
    python scripts/seed_demo.py --remove   # delete only is_demo rows

Fixtures contain no scores, benchmarks, evaluations, percentiles or verdicts: repositories are
`awaiting_analysis`, leads state only what a post could state, and nothing implies a hiring decision.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import delete, select  # noqa: E402

from app.main import app  # noqa: E402,F401  (registers every module's models)
from app.modules.code_verifier.models import CandidateRepo  # noqa: E402
from app.modules.job_lead_radar.models import JobLead, RawPost  # noqa: E402
from app.shared.database import AsyncSessionLocal, engine  # noqa: E402

DEMO_LEADS = [
    ("twitter", "Backend Engineer (demo fixture)", "Example Co A (demo)", ["Python", "PostgreSQL"], "Remote"),
    ("reddit", "Platform Engineer (demo fixture)", "Example Co B (demo)", ["Go", "Kubernetes"], "Hybrid"),
    ("linkedin", "Data Engineer (demo fixture)", "Example Co C (demo)", ["Python", "Kafka"], None),
]
DEMO_REPOS = [
    ("Demo Candidate One (fixture)", "demo-candidate-one", "https://github.com/demo-fixture/sample-project-one"),
    ("Demo Candidate Two (fixture)", "demo-candidate-two", "https://github.com/demo-fixture/sample-project-two"),
]


async def add() -> None:
    async with AsyncSessionLocal() as db:
        for i, (platform, role, company, stack, mode) in enumerate(DEMO_LEADS, start=1):
            ext = f"demo-fixture-{i}"
            if (await db.execute(select(RawPost).where(RawPost.external_id == ext))).scalar_one_or_none():
                continue
            post = RawPost(
                platform=platform, external_id=ext, author_handle="demo_fixture", author_name="Demo Fixture",
                raw_content=f"[DEMO FIXTURE, not a real post] {company} is hiring: {role}.",
                source_channel="Demo fixture", is_processed=True, classification="hiring",
            )
            db.add(post)
            await db.flush()
            db.add(JobLead(
                raw_post_id=post.id, role_title=role, company_name=company, tech_stack=stack,
                location_mode=mode, is_hiring=True, is_demo=True,
            ))
        for name, handle, url in DEMO_REPOS:
            if (await db.execute(select(CandidateRepo).where(CandidateRepo.repo_url == url))).scalar_one_or_none():
                continue
            db.add(CandidateRepo(
                candidate_name=name, candidate_github_handle=handle, repo_url=url,
                repo_name=url.rsplit("/", 1)[-1], status="awaiting_analysis", is_demo=True,
                benchmark=None, evaluation=None,
            ))
        await db.commit()
    print(f"seeded {len(DEMO_LEADS)} demo leads and {len(DEMO_REPOS)} demo repositories (labelled is_demo)")


async def remove() -> None:
    async with AsyncSessionLocal() as db:
        demo_post_ids = (await db.execute(select(JobLead.raw_post_id).where(JobLead.is_demo.is_(True)))).scalars().all()
        await db.execute(delete(JobLead).where(JobLead.is_demo.is_(True)))
        if demo_post_ids:
            await db.execute(delete(RawPost).where(RawPost.id.in_(demo_post_ids)))
        await db.execute(delete(CandidateRepo).where(CandidateRepo.is_demo.is_(True)))
        await db.commit()
    print("removed demo fixtures")


async def main() -> None:
    try:
        await (remove() if "--remove" in sys.argv else add())
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
