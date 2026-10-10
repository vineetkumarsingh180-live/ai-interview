"""
Step 5: nothing fabricated. When the AI provider or an analysis engine is unavailable the API says
so (explicit state or 503); it never answers with canned scores, verdicts, text or identities.
"""
import pathlib
import re
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.job_lead_radar.models import JobLead, RawPost
from app.modules.voice_defense.models import VoiceSession
from app.shared.config import settings
from tests.fakes import FakeDb, install_db

APP_DIR = pathlib.Path(__file__).resolve().parents[1] / "app"


@pytest.fixture
def api():
    holder = {}

    def make(db=None):
        holder["cleanup"] = install_db(app, db or FakeDb())
        return TestClient(app, raise_server_exceptions=False)

    yield make
    if "cleanup" in holder:
        holder["cleanup"]()


@pytest.fixture
def no_ai(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")


@pytest.fixture
def with_ai(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")


def _gemini_returns(monkeypatch, module, text, usage=None):
    async def fake(payload, **kwargs):
        body = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
        if usage:
            body["usageMetadata"] = usage
        return body

    monkeypatch.setattr(f"app.modules.{module}.generate_content", fake)


# ---- source-level guard: known fabricated literals must never come back -----------------------
FORBIDDEN = ["AUTO_HIRE", "Auto-Hire", "distributed-raft-kv", "Aura Engine", "dicebear", "94.2", "98.1",
             "gemini-3.8-flash", "Staff Distributed Systems Engineer", "Raft election", "talent@auraengine"]


def test_no_fabricated_literals_in_backend_source():
    hits = []
    for path in APP_DIR.rglob("*.py"):
        text = path.read_text()
        for needle in FORBIDDEN:
            if needle in text:
                hits.append(f"{path.relative_to(APP_DIR)}: {needle}")
    assert not hits, hits


# ---- lead radar ----------------------------------------------------------------------------
def test_ingest_without_ai_is_awaiting_analysis_and_creates_no_lead(api, no_ai):
    db = FakeDb()
    res = api(db).post("/api/v1/leads/ingest/trigger", json={"platform": "twitter", "rawContent": "Hiring a Rust dev"})
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "awaiting_analysis" and body["lead"] is None and body["reason"]
    assert not [o for o in db.added if isinstance(o, JobLead)]
    raw = [o for o in db.added if isinstance(o, RawPost)][0]
    assert raw.is_processed is False and raw.classification is None


def test_ingest_job_seeker_is_discarded_not_stored_as_lead(api, with_ai, monkeypatch):
    _gemini_returns(monkeypatch, "job_lead_radar.service", '{"is_hiring": false}')
    db = FakeDb()
    body = api(db).post("/api/v1/leads/ingest/trigger",
                        json={"platform": "twitter", "rawContent": "open to work"}).json()
    assert body["status"] == "discarded" and body["lead"] is None
    assert not [o for o in db.added if isinstance(o, JobLead)]
    assert [o for o in db.added if isinstance(o, RawPost)][0].classification == "seeking"


def test_ingest_hiring_lead_uses_only_stated_fields(api, with_ai, monkeypatch):
    _gemini_returns(monkeypatch, "job_lead_radar.service",
                    '{"is_hiring": true, "role_title": "Rust Engineer", "company_name": "Acme", "tech_stack": ["Rust"]}')
    body = api().post("/api/v1/leads/ingest/trigger",
                      json={"platform": "reddit", "rawContent": "Acme is hiring a Rust Engineer"}).json()
    lead = body["lead"]
    assert body["status"] == "created"
    assert (lead["roleTitle"], lead["companyName"], lead["techStack"]) == ("Rust Engineer", "Acme", ["Rust"])
    for unstated in ("compMin", "compMax", "compCurrency", "equityNote", "companyStage", "locationMode",
                     "urgencyTier", "contactAnchor", "matchScore", "clearanceRequired"):
        assert lead[unstated] is None, unstated
    assert lead["isDemo"] is False


def test_ingest_hiring_without_role_is_needs_review(api, with_ai, monkeypatch):
    _gemini_returns(monkeypatch, "job_lead_radar.service", '{"is_hiring": true, "role_title": null}')
    body = api().post("/api/v1/leads/ingest/trigger", json={"platform": "twitter", "rawContent": "we are hiring"}).json()
    assert body["status"] == "needs_review" and body["lead"] is None


def test_outreach_without_ai_is_503_not_template_text(api, no_ai):
    lead_id = uuid.uuid4()
    lead = JobLead(id=lead_id, raw_post_id=uuid.uuid4(), role_title="Engineer", company_name="Acme",
                   tech_stack=["Go"], is_hiring=True)
    res = api(FakeDb({(JobLead, lead_id): lead})).post(
        "/api/v1/leads/outreach/generate", json={"leadId": str(lead_id), "tone": "Executive"})
    assert res.status_code == 503 and res.json()["code"] == "ai_unavailable"


def test_outreach_with_ai_records_real_model_and_usage(api, with_ai, monkeypatch):
    lead_id = uuid.uuid4()
    lead = JobLead(id=lead_id, raw_post_id=uuid.uuid4(), role_title="Engineer", company_name="Acme",
                   tech_stack=["Go"], is_hiring=True)
    _gemini_returns(monkeypatch, "job_lead_radar.service",
                    '{"pitch_subject": "Go role at Acme", "generated_pitch": "Hello Acme"}',
                    usage={"promptTokenCount": 11, "candidatesTokenCount": 7})
    res = api(FakeDb({(JobLead, lead_id): lead})).post(
        "/api/v1/leads/outreach/generate", json={"leadId": str(lead_id)})
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["modelVersion"] == settings.GEMINI_MODEL
    assert (body["promptTokens"], body["completionTokens"]) == (11, 7)
    assert body["generatedPitch"] == "Hello Acme"


def test_outreach_unknown_lead_is_404(api, with_ai):
    res = api().post("/api/v1/leads/outreach/generate", json={"leadId": str(uuid.uuid4())})
    assert res.status_code == 404


# ---- code verifier ---------------------------------------------------------------------------
def test_repo_submission_is_awaiting_analysis_with_no_scores(api):
    res = api().post("/api/v1/assessment/repo/submit", json={
        "candidateName": "Ada", "candidateGithubHandle": "@ada", "repoUrl": "https://github.com/ada/engine"})
    assert res.status_code == 201, res.text
    repo = res.json()
    assert repo["status"] == "awaiting_analysis" and repo["repoName"] == "engine"
    for unknown in ("benchmark", "evaluation", "language", "commitSha", "candidateAvatarUrl", "targetRole", "branch"):
        assert repo[unknown] is None, unknown
    assert repo["isDemo"] is False
    assert repo["candidateGithubHandle"] == "ada"


# ---- voice defense ----------------------------------------------------------------------------
def test_voice_session_starts_unscored_with_a_neutral_opening(api):
    body = api().post("/api/v1/assessment/voice/init", json={"candidateName": "Ada"}).json()
    assert body["finalCompositeScore"] is None and body["technicalDepthScore"] is None
    assert body["defenseVerdict"] == "needs_human_review"
    assert len(body["transcriptTurns"]) == 1 and body["transcriptTurns"][0]["speaker"] == "ai_interviewer"
    assert "Raft" not in body["transcriptTurns"][0]["text"]


def test_voice_turn_without_ai_records_answer_and_reports_unavailable(api, no_ai):
    sid = uuid.uuid4()
    session = VoiceSession(id=sid, candidate_name="Ada", session_status="active",
                           defense_verdict="needs_human_review", transcript_turns=[], key_takeaways=[],
                           duration_seconds=0)
    res = api(FakeDb({(VoiceSession, sid): session})).post(
        "/api/v1/assessment/voice/turn", json={"sessionId": str(sid), "candidateSpeechText": "banana"})
    body = res.json()
    assert res.status_code == 200
    assert body["aiStatus"] == "unavailable" and body["interviewerReplyText"] is None
    assert body["currentCompositeScore"] is None and body["defenseScoreDelta"] is None
    assert body["currentVerdict"] == "needs_human_review"
    assert [t["speaker"] for t in session.transcript_turns] == ["candidate"]   # answer stored, no fake reply


def test_voice_turn_with_ai_returns_a_generated_question_but_no_score(api, with_ai, monkeypatch):
    sid = uuid.uuid4()
    session = VoiceSession(id=sid, candidate_name="Ada", session_status="active",
                           defense_verdict="needs_human_review", transcript_turns=[], key_takeaways=[],
                           duration_seconds=0)
    _gemini_returns(monkeypatch, "voice_defense.service", "How does your cache invalidate?")
    body = api(FakeDb({(VoiceSession, sid): session})).post(
        "/api/v1/assessment/voice/turn", json={"sessionId": str(sid), "candidateSpeechText": "I use an LRU."}).json()
    assert body["aiStatus"] == "generated" and body["interviewerReplyText"] == "How does your cache invalidate?"
    assert body["currentCompositeScore"] is None
    assert body["currentVerdict"] == "needs_human_review"
