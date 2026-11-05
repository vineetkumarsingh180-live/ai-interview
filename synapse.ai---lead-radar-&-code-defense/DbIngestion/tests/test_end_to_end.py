"""
End to end: source -> DbIngestion -> PostgreSQL -> FastAPI JSON (what React receives).

Everything runs inside the conftest's rolled-back transaction against the real database; the
FastAPI app is the real app with `get_db` bound to a session in that same transaction. GitHub is a
mock transport. The React layer is covered by the frontend test suite and the browser run in
handoff section 59.
"""
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.shared.database import get_db
from dbingestion import runner
from dbingestion.sources import demo_fixtures, github_repos, manual_posts
from tests.test_github_repos import make_client

pytestmark = pytest.mark.anyio

STRUCTURED = {"role_title": "Rust Engineer", "company_name": "Acme", "tech_stack": ["Rust"], "location_mode": "Remote"}
TEXT = "Acme is hiring a Rust engineer. Remote."


@pytest.fixture
async def api(conn):
    session = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")

    async def override():
        yield session

    app.dependency_overrides[get_db] = override
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
        await session.close()


def post(**over):
    return manual_posts._validate(0, {"platform": "twitter", "text": TEXT, "structured": STRUCTURED, **over})


async def test_empty_database_gives_honest_empty_api_answers(api):
    assert (await api.get("/api/v1/leads/ingest/recent")).json() == []
    assert (await api.get("/api/v1/assessment/repo/recent")).json() == []
    t = (await api.get("/api/v1/leads/ingest/telemetry")).json()
    assert t["totalScanned24h"] == 0 and t["qualifiedLeadsCount"] == 0 and t["demoPostsCount"] == 0
    assert t["avgLatencyMs"] is None
    assert (await api.get("/api/v1/assessment/voice/leaderboard")).json() == []


async def test_manual_post_reaches_api_with_provenance_and_no_invented_scores(session_factory, api):
    await runner.run_posts([post(source_url="https://x.com/acme/status/1")], session_factory=session_factory)
    (lead,) = (await api.get("/api/v1/leads/ingest/recent")).json()
    assert lead["roleTitle"] == "Rust Engineer" and lead["entrySource"] == "operator_entered"
    assert lead["matchScore"] is None
    raw = lead["rawPost"]
    assert raw["rawContent"] == TEXT
    assert (raw["sourceType"], raw["verificationStatus"], raw["isDemo"]) == ("manual_text", "unverified", False)
    assert raw["sourceUrl"] == "https://x.com/acme/status/1"


async def test_duplicate_is_ingested_once_and_counted_once(session_factory, api):
    first = await runner.run_posts([post()], session_factory=session_factory)
    again = await runner.run_posts([post()], session_factory=session_factory)
    assert first.counts()["created"] == 1 and again.counts()["duplicate"] == 1
    assert len((await api.get("/api/v1/leads/ingest/recent")).json()) == 1
    assert (await api.get("/api/v1/leads/ingest/telemetry")).json()["totalScanned24h"] == 1


async def test_invalid_and_incomplete_input_never_reaches_the_api(session_factory, api):
    items = [
        manual_posts._validate(0, {"platform": "twitter", "text": "   "}),                           # blank
        manual_posts._validate(1, {"platform": "twitter", "text": "x", "structured": {"role_title": "Only"}}),  # missing company
        manual_posts._validate(2, {"platform": "myspace", "text": "unsupported platform"}),         # rejected by module
        manual_posts._validate(3, "not an object"),
    ]
    s = await runner.run_posts(items, session_factory=session_factory)
    assert s.counts()["rejected"] == 4 and s.counts()["created"] == 0
    assert (await api.get("/api/v1/leads/ingest/recent")).json() == []


async def test_post_without_structured_fields_waits_for_analysis_not_a_fabricated_lead(session_factory, api):
    await runner.run_posts([manual_posts._validate(0, {"platform": "reddit", "text": "Raw text only"})], session_factory=session_factory)
    assert (await api.get("/api/v1/leads/ingest/recent")).json() == []
    t = (await api.get("/api/v1/leads/ingest/telemetry")).json()
    assert t["totalScanned24h"] == 1 and t["awaitingAnalysisCount"] == 1 and t["qualifiedLeadsCount"] == 0


async def test_demo_rows_are_labelled_and_excluded_from_real_counts(session_factory, api):
    await runner.run_posts(demo_fixtures.posts(), source_type="demo_fixture", is_demo=True, session_factory=session_factory)
    await runner.run_posts([post()], session_factory=session_factory)
    allr = (await api.get("/api/v1/leads/ingest/recent")).json()
    genuine = (await api.get("/api/v1/leads/ingest/recent", params={"includeDemo": "false"})).json()
    n_demo_leads = sum(1 for i in demo_fixtures.posts() if i.value.structured is not None)
    assert len(allr) == len(genuine) + n_demo_leads
    assert all(r["rawPost"]["isDemo"] for r in allr if r not in genuine)
    assert len(genuine) == 1 and not genuine[0]["rawPost"]["isDemo"]
    t = (await api.get("/api/v1/leads/ingest/telemetry")).json()
    assert t["totalScanned24h"] == 1 and t["demoPostsCount"] == len(demo_fixtures.posts())
    # demo activity is reported in separate fields, never mixed into the genuine counts
    assert t["demoScanned24h"] == len(demo_fixtures.posts()) and t["demoQualifiedLeadsCount"] == n_demo_leads
    assert t["demoSeekingDiscardedCount"] == 1 and t["demoAwaitingAnalysisCount"] == 1 and t["qualifiedLeadsCount"] == 1


async def test_github_repo_reaches_api_with_only_github_facts(session_factory, api):
    await runner.run_github(github_repos.from_urls(["https://github.com/ada/engine"]), client=make_client(), session_factory=session_factory)
    (repo,) = (await api.get("/api/v1/assessment/repo/recent")).json()
    assert repo["sourceType"] == "github_api" and repo["verificationStatus"] == "github_metadata"
    assert repo["status"] == "awaiting_analysis" and repo["language"] == "Rust"
    assert repo["githubMetadata"]["stars"] == 7
    detail = (await api.get(f"/api/v1/assessment/repo/{repo['id']}")).json()
    assert detail["benchmark"] is None and detail["evaluation"] is None   # nothing measured, nothing invented


async def test_duplicate_repo_submitted_through_api_is_409_not_a_second_row(session_factory, api):
    await runner.run_github(github_repos.from_urls(["https://github.com/ada/engine"]), client=make_client(), session_factory=session_factory)
    r = await api.post("/api/v1/assessment/repo/submit", json={
        "candidateName": "X", "candidateGithubHandle": "x", "repoUrl": "https://github.com/ada/engine"})
    assert r.status_code == 409 and r.json()["code"] == "duplicate_repository"
    assert len((await api.get("/api/v1/assessment/repo/recent")).json()) == 1


async def test_database_failure_is_a_503_envelope_not_fabricated_data():
    class Broken:
        async def execute(self, *a, **k):
            raise ConnectionRefusedError("db down")

        async def commit(self): ...
        async def rollback(self): ...
        async def close(self): ...

    async def override():
        yield Broken()

    app.dependency_overrides[get_db] = override
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as c:
            r = await c.get("/api/v1/leads/ingest/recent")
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert r.status_code >= 500
    body = r.json()
    assert "code" in body and "detail" in body and not isinstance(body, list)
