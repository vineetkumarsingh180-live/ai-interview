"""
Backend <-> AIService integration (mock provider; no network, no key).

Proves the wiring through the composition root, the adapters' mapping, and the unavailable states.
This is NOT live Gemini verification.
"""
import uuid

import pytest
from aiservice.providers.base import Generation

from app.core.ai_adapters import (
    AIServiceInterviewer,
    AIServiceLeadAnalyzer,
    AIServiceOutreachDrafter,
    AIServiceRepositoryAnalyzer,
)
from app.main import app
from app.modules import code_verifier, job_lead_radar, voice_defense
from app.modules.code_verifier.models import CandidateRepo
from app.modules.code_verifier.service import CodeVerifierService
from tests.fakes import FakeDb

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class Scripted:
    name, model = "scripted", "scripted-1"

    def __init__(self, text=None, configured=True):
        self.text, self.configured, self.calls = text, configured, 0

    def is_configured(self):
        return self.configured

    async def generate_text(self, **kw):
        self.calls += 1
        return Generation(text=self.text, model=self.model)

    generate_json = generate_text


def test_all_ai_ports_are_bound_to_aiservice_adapters_in_the_composition_root():
    o = app.dependency_overrides
    assert isinstance(o[job_lead_radar.get_lead_analyzer](), AIServiceLeadAnalyzer)
    assert isinstance(o[job_lead_radar.get_outreach_drafter](), AIServiceOutreachDrafter)
    assert isinstance(o[voice_defense.get_interviewer](), AIServiceInterviewer)
    assert isinstance(o[code_verifier.get_repository_analyzer](), AIServiceRepositoryAnalyzer)


async def test_lead_adapter_maps_verified_fields_and_dropped_claims():
    text = '{"is_hiring": true, "role_title": "Rust Engineer", "company_name": "Globex", "tech_stack": ["Rust", "Cobol"]}'
    adapter = AIServiceLeadAnalyzer(lambda: Scripted(text))
    r = await adapter.analyze_post("Acme is hiring a Rust Engineer. Rust all day.", "twitter")
    assert r.status == "analyzed" and r.is_hiring is True
    assert r.role_title == "Rust Engineer" and r.company_name is None and r.tech_stack == ["Rust"]
    assert "company_name" in r.dropped_fields and "tech_stack:Cobol" in r.dropped_fields
    assert (r.model, r.prompt_version) == ("scripted-1", "2")


async def test_every_adapter_reports_unavailable_without_a_key_and_never_fabricates():
    p = lambda: Scripted(configured=False)  # noqa: E731
    lead = await AIServiceLeadAnalyzer(p).analyze_post("Acme hiring", "twitter")
    assert (lead.status, lead.role_title, lead.is_hiring) == ("unavailable", None, None)
    out = await AIServiceOutreachDrafter(p).draft(
        role_title="E", company_name="A", tone="Executive", tech_stack=[], comp_min=None, comp_max=None,
        comp_currency=None, candidate_background=None)
    assert (out.status, out.pitch) == ("unavailable", None)
    fu = await AIServiceInterviewer(p).follow_up([{"speaker": "candidate", "text": "I cache."}])
    assert (fu.status, fu.question) == ("unavailable", None)


async def test_code_verifier_seam_reports_content_unavailable_and_calls_no_provider(monkeypatch):
    repo_id = uuid.uuid4()
    repo = CandidateRepo(id=repo_id, candidate_name="Ada", candidate_github_handle="ada",
                         repo_url="https://github.com/ada/engine", repo_name="engine", status="awaiting_analysis")
    provider = Scripted('{"summary": "should never be asked"}')

    async def get_repo(db, rid):
        return repo if rid == repo_id else None

    monkeypatch.setattr("app.modules.code_verifier.service.repository.get_repo", get_repo)
    result = await CodeVerifierService.request_analysis(
        FakeDb(), repo_id, AIServiceRepositoryAnalyzer(lambda: provider))
    assert (result.status, result.reason) == ("unavailable", "repository_content_not_available")
    assert provider.calls == 0 and repo.status == "awaiting_analysis"


async def test_code_verifier_seam_with_unknown_repository_is_not_found(monkeypatch):
    from app.shared.errors import NotFound

    async def get_repo(db, rid):
        return None

    monkeypatch.setattr("app.modules.code_verifier.service.repository.get_repo", get_repo)

    with pytest.raises(NotFound):
        await CodeVerifierService.request_analysis(FakeDb(), uuid.uuid4(), AIServiceRepositoryAnalyzer(lambda: Scripted()))
