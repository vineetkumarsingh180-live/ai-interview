import pytest

from aiservice import (
    InvalidProviderResponse,
    LeadIntelligence,
    OutreachRequest,
    ProviderRateLimited,
)

pytestmark = pytest.mark.anyio

POST = "Acme is hiring a Staff Rust Engineer! $220k-$285k, remote friendly. Stack: Rust, Kafka. DM @acme_ceo"


def answer(**over):
    base = {
        "is_hiring": True, "role_title": "Staff Rust Engineer", "company_name": "Acme", "comp_min": 220000,
        "comp_max": 285000, "comp_currency": "USD", "tech_stack": ["Rust", "Kafka"], "location_mode": "Remote",
        "contact_anchor": "@acme_ceo", "summary": "Acme hires a Rust engineer.",
        "evidence": {"role_title": "Staff Rust Engineer", "company_name": "Acme", "comp_currency": "$220k",
                     "location_mode": "remote friendly", "contact_anchor": "DM @acme_ceo"},
    }
    base.update(over)
    return base


async def test_unconfigured_provider_is_unavailable_and_nothing_is_sent(fake):
    p = fake(configured=False)
    r = await LeadIntelligence(p).analyze_post(POST, "twitter")
    assert (r.status, r.reason) == ("unavailable", "not_configured") and p.prompts == []
    assert r.fields.role_title is None and r.is_hiring is None


async def test_supported_fields_are_kept_with_verified_evidence(fake):
    r = await LeadIntelligence(fake(answer())).analyze_post(POST, "twitter")
    assert r.status == "analyzed" and r.is_hiring is True
    f = r.fields
    assert (f.role_title, f.company_name, f.comp_min, f.comp_max) == ("Staff Rust Engineer", "Acme", 220000, 285000)
    assert f.location_mode == "Remote" and f.tech_stack == ["Rust", "Kafka"] and f.contact_anchor == "@acme_ceo"
    assert r.evidence["location_mode"] == "remote friendly" and r.dropped_fields == []
    assert (r.model, r.prompt_version, r.usage.prompt_tokens) == ("fake-model-1", "2", 11)


async def test_invented_values_are_dropped_not_trusted(fake):
    reply = answer(
        company_name="Globex", comp_min=999000, comp_max=1200000, tech_stack=["Rust", "Haskell"],
        location_mode="Onsite", urgency_tier="Immediate", clearance_required=True,
        evidence={"company_name": "Globex Corporation", "location_mode": "in the office", "urgency_tier": "ASAP"},
    )
    r = await LeadIntelligence(fake(reply)).analyze_post(POST, "twitter")
    f = r.fields
    assert f.company_name is None                      # not in the post
    assert f.comp_min is None and f.comp_max is None   # numbers not in the post
    assert f.comp_currency is None                     # no compensation left to qualify
    assert f.tech_stack == ["Rust"]                    # Haskell is not in the post
    assert f.location_mode is None and f.urgency_tier is None and f.clearance_required is None
    for name in ("company_name", "comp_min", "comp_max", "location_mode", "urgency_tier", "clearance_required", "tech_stack:Haskell"):
        assert name in r.dropped_fields


async def test_inverted_compensation_range_is_discarded(fake):
    r = await LeadIntelligence(fake(answer(comp_min=285000, comp_max=220000))).analyze_post(POST, "twitter")
    assert r.fields.comp_min is None and r.fields.comp_max is None


async def test_job_seeker_is_classified_without_fields(fake):
    r = await LeadIntelligence(fake({"is_hiring": False})).analyze_post("open to work, Go dev", "reddit")
    assert r.status == "analyzed" and r.is_hiring is False
    assert r.fields.role_title is None and r.fields.tech_stack == []


@pytest.mark.parametrize("reply", ["not json", "[1,2]", {"role_title": "x"}, {"is_hiring": "maybe"}])
async def test_unparseable_or_schema_invalid_answers_are_invalid_responses(fake, reply):
    r = await LeadIntelligence(fake(reply)).analyze_post(POST, "twitter")
    assert r.status == "invalid_response" and r.fields.role_title is None


async def test_provider_failures_become_unavailable_with_the_reason(fake):
    r = await LeadIntelligence(fake(error=ProviderRateLimited("slow down"))).analyze_post(POST, "twitter")
    assert (r.status, r.reason) == ("unavailable", "rate_limited")


async def test_empty_post_is_rejected_without_calling_the_provider(fake):
    p = fake(answer())
    r = await LeadIntelligence(p).analyze_post("   ", "twitter")
    assert r.status == "invalid_response" and p.prompts == []


async def test_provider_is_injected_and_post_goes_into_the_prompt(fake):
    p = fake(answer())
    await LeadIntelligence(p).analyze_post(POST, "linkedin")
    assert "Platform: linkedin" in p.prompts[0] and "Staff Rust Engineer" in p.prompts[0]


# ---- outreach -----------------------------------------------------------------------------
REQ = OutreachRequest(role_title="Engineer", company_name="Acme", tech_stack=["Go"])


async def test_outreach_generated_uses_only_supplied_facts(fake):
    p = fake({"pitch_subject": "Go role", "generated_pitch": "Hello Acme"})
    r = await LeadIntelligence(p).draft_outreach(REQ)
    assert (r.status, r.subject, r.pitch, r.usage.completion_tokens) == ("generated", "Go role", "Hello Acme", 7)
    assert "do not invent" in p.prompts[0] and "ROLE: Engineer" in p.prompts[0]


async def test_outreach_unavailable_without_key(fake):
    r = await LeadIntelligence(fake(configured=False)).draft_outreach(REQ)
    assert (r.status, r.reason, r.pitch) == ("unavailable", "not_configured", None)


async def test_outreach_empty_or_malformed_draft_is_invalid(fake):
    for reply in ({"pitch_subject": "s", "generated_pitch": "  "}, {"pitch_subject": "s"}, "oops"):
        r = await LeadIntelligence(fake(reply)).draft_outreach(REQ)
        assert r.status == "invalid_response" and r.pitch is None
