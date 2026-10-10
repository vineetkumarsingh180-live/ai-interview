"""
Step 3 contract tests: the single authoritative HTTP contract.

Covers the OpenAPI snapshot, wire casing, id/validation behaviour and the structured error
envelope. The snapshot must be re-generated deliberately when the contract is changed on purpose.
"""
import json
import os
import re
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app
from app.shared.config import settings
from tests.fakes import FakeDb, install_db

HERE = os.path.dirname(__file__)


@pytest.fixture
def client():
    cleanup = install_db(app, FakeDb())
    yield TestClient(app, raise_server_exceptions=False)
    cleanup()


def _snapshot(name):
    with open(os.path.join(HERE, "snapshots", name)) as fh:
        return json.load(fh)


def test_openapi_document_matches_snapshot():
    assert json.loads(json.dumps(app.openapi())) == _snapshot("openapi.json")


def test_expected_routes_registered():
    expected = {
        ("POST", "/api/v1/leads/ingest/trigger"), ("POST", "/api/v1/leads/ingest/parse-text"),
        ("GET", "/api/v1/leads/ingest/recent"), ("GET", "/api/v1/leads/ingest/telemetry"),
        ("POST", "/api/v1/leads/outreach/generate"), ("POST", "/api/v1/leads/search"),
        ("GET", "/api/v1/leads/outreach/history"),
        ("POST", "/api/v1/assessment/repo/submit"), ("GET", "/api/v1/assessment/repo/recent"),
        ("GET", "/api/v1/assessment/repo/{repo_id}"),
        ("POST", "/api/v1/assessment/voice/init"), ("POST", "/api/v1/assessment/voice/turn"),
        ("GET", "/api/v1/assessment/voice/leaderboard"), ("GET", "/api/v1/assessment/voice/{session_id}"),
        ("GET", "/api/health"),
    }
    assert {(m.upper(), p) for p, ops in app.openapi()["paths"].items() for m in ops} == expected


def test_every_schema_property_is_camel_case():
    """One naming convention on the wire: no snake_case property anywhere in the contract."""
    offenders = []
    for name, schema in app.openapi()["components"]["schemas"].items():
        for prop in schema.get("properties", {}):
            if "_" in prop:
                offenders.append(f"{name}.{prop}")
    assert not offenders, offenders


def test_ids_are_uuids_in_the_contract():
    schemas = app.openapi()["components"]["schemas"]
    for model, prop in [("JobLeadResponse", "id"), ("CandidateRepoDetailResponse", "id"),
                        ("VoiceTurnInput", "sessionId"), ("OutreachDraftRequest", "leadId")]:
        assert schemas[model]["properties"][prop].get("format") == "uuid", (model, prop)


def test_health_reports_database_and_ai_status(client):
    body = client.get("/api/health").json()
    assert set(body) == {"status", "service", "version", "database", "gemini"}
    assert body["database"] in {"connected", "unreachable"}
    assert body["gemini"] in {"configured", "not_configured"}


def test_requests_accept_camel_case_and_snake_case(client):
    for body in ({"candidateName": "Ada"}, {"candidate_name": "Ada"}):
        res = client.post("/api/v1/assessment/voice/init", json=body)
        assert res.status_code == 201, res.text
        assert res.json()["candidateName"] == "Ada"


def test_responses_use_camel_case(client):
    res = client.post("/api/v1/assessment/voice/init", json={"candidateName": "Ada"})
    keys = set(res.json())
    assert {"id", "candidateName", "sessionStatus", "transcriptTurns", "defenseVerdict"} <= keys
    assert not any("_" in k for k in keys)


# ---- structured errors ---------------------------------------------------------------------
def _assert_envelope(res, status, code):
    assert res.status_code == status, res.text
    body = res.json()
    assert isinstance(body["detail"], str) and body["detail"]
    assert body["code"] == code
    return body


def test_validation_error_is_structured_with_field_errors(client):
    res = client.post("/api/v1/assessment/repo/submit", json={
        "candidateName": "Ada", "candidateGithubHandle": "ada", "repoUrl": "https://example.com/not-github"})
    body = _assert_envelope(res, 422, "validation_error")
    assert any(e["field"].lower().replace("_", "") in ("repourl",) for e in body["errors"]), body


def test_invalid_uuid_is_a_422_not_a_500(client):
    _assert_envelope(client.get("/api/v1/assessment/repo/not-a-uuid"), 422, "validation_error")


def test_unknown_resource_is_404_envelope(client):
    _assert_envelope(client.get(f"/api/v1/assessment/repo/{uuid.uuid4()}"), 404, "not_found")


def test_unknown_session_turn_is_404_envelope(client):
    res = client.post("/api/v1/assessment/voice/turn",
                      json={"sessionId": str(uuid.uuid4()), "candidateSpeechText": "hello"})
    _assert_envelope(res, 404, "not_found")


def test_non_uuid_session_id_is_rejected_as_422(client):
    res = client.post("/api/v1/assessment/voice/turn",
                      json={"sessionId": "demo-voice-session-1", "candidateSpeechText": "hello"})
    _assert_envelope(res, 422, "validation_error")


def test_database_down_is_503_envelope_not_a_stack_trace():
    class BrokenDb(FakeDb):
        async def execute(self, _stmt):
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    cleanup = install_db(app, BrokenDb())
    try:
        res = TestClient(app, raise_server_exceptions=False).get("/api/v1/leads/ingest/recent")
    finally:
        cleanup()
    body = _assert_envelope(res, 503, "database_unavailable")
    assert "connection refused" not in json.dumps(body)


def test_unexpected_exception_is_500_envelope_without_internals():
    class ExplodingDb(FakeDb):
        async def execute(self, _stmt):
            raise RuntimeError("secret internal detail /etc/passwd")

    cleanup = install_db(app, ExplodingDb())
    try:
        res = TestClient(app, raise_server_exceptions=False).get("/api/v1/assessment/repo/recent")
    finally:
        cleanup()
    body = _assert_envelope(res, 500, "internal_error")
    assert "secret" not in json.dumps(body)


def test_leaderboard_route_is_not_shadowed_by_session_route(client):
    res = client.get("/api/v1/assessment/voice/leaderboard")
    assert res.status_code == 200 and res.json() == []


def test_database_schema_has_expected_tables():
    from app.shared.database import Base

    assert set(Base.metadata.tables) == {
        "raw_posts", "job_leads", "lead_embeddings", "outreach_drafts",
        "candidate_repos", "benchmark_suites", "code_evaluation_results",
        "voice_sessions", "leaderboard_scores",
    }


def test_orm_mappers_configure_without_cross_module_relationships():
    from sqlalchemy.orm import configure_mappers

    configure_mappers()


def test_cors_is_not_wildcard_with_credentials():
    assert "*" not in settings.CORS_ORIGINS
