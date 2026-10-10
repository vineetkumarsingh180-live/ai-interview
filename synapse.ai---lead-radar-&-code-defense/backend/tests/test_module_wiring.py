"""Composition-root wiring: Voice Defense's ports are served by Leaderboard and Code Verifier."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.code_verifier.models import CandidateRepo
from app.modules.leaderboard.models import LeaderboardScore
from app.modules.voice_defense.models import VoiceSession
from tests.fakes import FakeDb, install_db


@pytest.fixture
def make_client():
    cleanups = []

    def make(db):
        cleanups.append(install_db(app, db))
        return TestClient(app, raise_server_exceptions=False)

    yield make
    for c in cleanups:
        c()


def _session(session_id, repo_id=None, name="Ada Lovelace"):
    return VoiceSession(id=session_id, repo_id=repo_id, candidate_name=name, session_status="active",
                        defense_verdict="needs_human_review", transcript_turns=[], key_takeaways=[],
                        duration_seconds=0)


def test_voice_turn_publishes_to_leaderboard_through_port(make_client):
    sid, rid = uuid.uuid4(), uuid.uuid4()
    repo = CandidateRepo(id=rid, candidate_name="Ada Lovelace", candidate_github_handle="ada",
                         repo_url="https://github.com/ada/engine", repo_name="engine", target_role="Staff Eng")
    db = FakeDb({(VoiceSession, sid): _session(sid, rid), (CandidateRepo, rid): repo})
    res = make_client(db).post("/api/v1/assessment/voice/turn",
                               json={"sessionId": str(sid), "candidateSpeechText": "quorum and pre-vote"})
    assert res.status_code == 200, res.text
    rows = [o for o in db.added if isinstance(o, LeaderboardScore)]
    assert len(rows) == 1
    row = rows[0]
    assert (row.session_id, row.candidate_name, row.candidate_handle, row.repo_name, row.target_role) == (
        sid, "Ada Lovelace", "ada", "engine", "Staff Eng")
    assert row.voice_defense_score is None and row.status_tag == "needs_human_review"


def test_voice_init_reads_candidate_through_repository_port(make_client):
    rid = uuid.uuid4()
    repo = CandidateRepo(id=rid, candidate_name="Grace Hopper", candidate_github_handle="grace",
                         repo_url="https://github.com/grace/compiler", repo_name="compiler")
    res = make_client(FakeDb({(CandidateRepo, rid): repo})).post(
        "/api/v1/assessment/voice/init", json={"repoId": str(rid), "candidateName": "ignored"})
    assert res.status_code == 201, res.text
    assert res.json()["candidateName"] == "Grace Hopper"
    assert res.json()["repoId"] == str(rid)


def test_each_module_exposes_its_public_api():
    from app.modules import code_verifier, job_lead_radar, leaderboard, voice_defense

    for module in (code_verifier, job_lead_radar, leaderboard, voice_defense):
        assert hasattr(module, "router") and module.__all__, module.__name__
