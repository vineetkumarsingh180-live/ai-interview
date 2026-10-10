"""
Integration tests against the real isolated Synapse PostgreSQL (needs `alembic upgrade head`).

Every test runs inside an outer transaction that is rolled back, so the database is left exactly
as it was. The tables are emptied *inside* that transaction first, so pre-existing rows (e.g. the
labelled demo fixtures) neither affect the assertions nor are lost. Skipped automatically when the database is unreachable. The AI provider is stubbed.
"""
import uuid

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.main import app
from app.shared.config import settings
from app.shared.database import get_db

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        conn = await engine.connect()
        outer = await conn.begin()
        await conn.execute(text("SELECT 1 FROM alembic_version"))
        # Clean slate *inside this transaction only* (rolled back at the end), so existing rows
        # such as the labelled demo fixtures never affect assertions and are never deleted.
        for table in ("leaderboard_scores", "voice_sessions", "outreach_drafts", "lead_embeddings",
                      "job_leads", "raw_posts", "benchmark_suites", "code_evaluation_results", "candidate_repos"):
            await conn.execute(text(f"DELETE FROM {table}"))
    except Exception as exc:  # database missing / not migrated
        await engine.dispose()
        pytest.skip(f"Synapse database not available: {type(exc).__name__}")
    session = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")

    async def override():
        yield session

    app.dependency_overrides[get_db] = override
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
        await session.close()
        await outer.rollback()
        await conn.close()
        await engine.dispose()


def _stub_ai(monkeypatch, module, text_value, usage=None):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")

    async def fake(payload, **kwargs):
        body = {"candidates": [{"content": {"parts": [{"text": text_value}]}}]}
        if usage:
            body["usageMetadata"] = usage
        return body

    monkeypatch.setattr(f"app.modules.{module}.generate_content", fake)


async def test_repo_submission_roundtrip_is_awaiting_analysis(client):
    res = await client.post("/api/v1/assessment/repo/submit", json={
        "candidateName": "Ada", "candidateGithubHandle": "ada", "repoUrl": "https://github.com/ada/engine"})
    assert res.status_code == 201, res.text
    repo = res.json()
    assert repo["status"] == "awaiting_analysis" and repo["benchmark"] is None and repo["evaluation"] is None

    listed = (await client.get("/api/v1/assessment/repo/recent")).json()
    assert [r["id"] for r in listed] == [repo["id"]]
    one = await client.get(f"/api/v1/assessment/repo/{repo['id']}")
    assert one.status_code == 200 and one.json()["repoName"] == "engine"


async def test_ingest_without_ai_is_stored_and_counted_as_awaiting(client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    res = await client.post("/api/v1/leads/ingest/trigger",
                            json={"platform": "twitter", "rawContent": "Hiring a Rust dev", "externalId": "t-1"})
    assert res.status_code == 201 and res.json()["status"] == "awaiting_analysis"
    assert (await client.get("/api/v1/leads/ingest/recent")).json() == []
    t = (await client.get("/api/v1/leads/ingest/telemetry")).json()
    assert (t["totalScanned24h"], t["qualifiedLeadsCount"], t["seekingDiscardedCount"], t["awaitingAnalysisCount"]) == (1, 0, 0, 1)
    assert t["channelsMonitored"] == ["Manual import"] and t["avgLatencyMs"] is None


async def test_ingest_hiring_lead_roundtrip_filter_search_and_telemetry(client, monkeypatch):
    _stub_ai(monkeypatch, "job_lead_radar.service",
             '{"is_hiring": true, "role_title": "Rust Engineer", "company_name": "Acme", "tech_stack": ["Rust", "Raft"]}')
    created = await client.post("/api/v1/leads/ingest/trigger", json={
        "platform": "reddit", "rawContent": "Acme is hiring a Rust Engineer", "externalId": "r-1",
        "authorHandle": "u/acme"})
    assert created.status_code == 201 and created.json()["status"] == "created"
    lead = created.json()["lead"]
    assert lead["rawPost"]["authorHandle"] == "u/acme" and lead["matchScore"] is None

    recent = (await client.get("/api/v1/leads/ingest/recent")).json()
    assert [l["id"] for l in recent] == [lead["id"]]
    assert (await client.get("/api/v1/leads/ingest/recent?platform=reddit")).json()[0]["id"] == lead["id"]
    assert (await client.get("/api/v1/leads/ingest/recent?platform=twitter")).json() == []

    hits = (await client.post("/api/v1/leads/search", json={"queryText": "rust acme"})).json()
    assert [h["lead"]["id"] for h in hits] == [lead["id"]]
    assert hits[0]["matchType"] == "keyword" and hits[0]["similarityScore"] is None
    assert (await client.post("/api/v1/leads/search", json={"queryText": "cobol"})).json() == []

    t = (await client.get("/api/v1/leads/ingest/telemetry")).json()
    assert t["qualifiedLeadsCount"] == 1 and t["totalScanned24h"] == 1


async def test_ingest_seeker_is_discarded_and_counted(client, monkeypatch):
    _stub_ai(monkeypatch, "job_lead_radar.service", '{"is_hiring": false}')
    res = await client.post("/api/v1/leads/ingest/trigger", json={"platform": "twitter", "rawContent": "open to work", "externalId": "s-1"})
    assert res.json()["status"] == "discarded"
    assert (await client.get("/api/v1/leads/ingest/recent")).json() == []
    t = (await client.get("/api/v1/leads/ingest/telemetry")).json()
    assert t["seekingDiscardedCount"] == 1 and t["qualifiedLeadsCount"] == 0


async def test_duplicate_external_id_is_a_409_envelope(client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    body = {"platform": "twitter", "rawContent": "x", "externalId": "dup-1"}
    assert (await client.post("/api/v1/leads/ingest/trigger", json=body)).status_code == 201
    again = await client.post("/api/v1/leads/ingest/trigger", json=body)
    assert again.status_code == 409 and again.json()["code"] == "duplicate_post"


async def test_outreach_roundtrip_records_real_model_and_history(client, monkeypatch):
    _stub_ai(monkeypatch, "job_lead_radar.service",
             '{"is_hiring": true, "role_title": "Go Engineer", "company_name": "Beta", "tech_stack": ["Go"]}')
    lead = (await client.post("/api/v1/leads/ingest/trigger", json={
        "platform": "linkedin", "rawContent": "Beta hiring", "externalId": "l-1"})).json()["lead"]

    _stub_ai(monkeypatch, "job_lead_radar.service",
             '{"pitch_subject": "Go at Beta", "generated_pitch": "Hello Beta"}', usage={"promptTokenCount": 5, "candidatesTokenCount": 3})
    res = await client.post("/api/v1/leads/outreach/generate", json={"leadId": lead["id"], "tone": "Executive"})
    assert res.status_code == 201, res.text
    draft = res.json()
    assert draft["modelVersion"] == settings.GEMINI_MODEL and draft["promptTokens"] == 5
    hist = (await client.get("/api/v1/leads/outreach/history")).json()
    assert [h["id"] for h in hist] == [draft["id"]]


async def test_voice_interview_roundtrip_publishes_unscored_row_to_leaderboard(client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    repo = (await client.post("/api/v1/assessment/repo/submit", json={
        "candidateName": "Ada Lovelace", "candidateGithubHandle": "ada", "repoUrl": "https://github.com/ada/engine",
        "targetRole": "Backend"})).json()

    init = await client.post("/api/v1/assessment/voice/init", json={"repoId": repo["id"]})
    assert init.status_code == 201, init.text
    session = init.json()
    assert session["candidateName"] == "Ada Lovelace" and session["repoId"] == repo["id"]
    assert session["finalCompositeScore"] is None and len(session["transcriptTurns"]) == 1

    turn = await client.post("/api/v1/assessment/voice/turn",
                             json={"sessionId": session["id"], "candidateSpeechText": "I used event sourcing."})
    assert turn.status_code == 200, turn.text
    t = turn.json()
    assert t["aiStatus"] == "unavailable" and t["currentCompositeScore"] is None
    assert t["currentVerdict"] == "needs_human_review" and t["turnNumber"] == 1

    board = (await client.get("/api/v1/assessment/voice/leaderboard")).json()
    assert len(board) == 1
    row = board[0]
    assert (row["candidateName"], row["candidateHandle"], row["repoName"], row["targetRole"]) == (
        "Ada Lovelace", "ada", "engine", "Backend")
    assert row["voiceDefenseScore"] is None and row["compositePercentile"] is None and row["rankTier"] is None
    assert row["statusTag"] == "needs_human_review"

    stored = (await client.get(f"/api/v1/assessment/voice/{session['id']}")).json()
    assert [x["speaker"] for x in stored["transcriptTurns"]] == ["ai_interviewer", "candidate"]


async def test_health_reports_connected_database(client):
    body = (await client.get("/api/health")).json()
    assert body["database"] == "connected" and body["status"] == "ok"
