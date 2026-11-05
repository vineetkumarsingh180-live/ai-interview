"""Manual job-post ingestion: provenance, dedup, validation, run log, transactions."""
import json

import pytest

from app.modules import job_lead_radar
from app.shared.ingestion_log import IngestContext
from dbingestion import runner
from dbingestion.sources import manual_posts

pytestmark = pytest.mark.anyio

TEXT = "Acme is hiring a Rust engineer.\n\n  Remote, $180k-$220k.   DM me!"


def item(**over):
    base = {"platform": "twitter", "text": TEXT, "author_handle": "@acme_ceo"}
    base.update(over)
    return manual_posts._validate(0, base)


async def test_post_is_stored_unchanged_with_provenance_and_never_verified(session_factory, read):
    summary = await runner.run_posts(
        [item(source_url="https://x.com/acme_ceo/status/1", note="pasted by operator")],
        label="unit-test", session_factory=session_factory)
    assert summary.counts()["created"] == 1 and summary.run_id

    (row,) = await read("select raw_content, source_type, verification_status, source_url, content_hash, "
                        "is_demo, is_processed, classification, provenance->>'note', ingestion_run_id "
                        "from raw_posts")
    assert row[0] == TEXT                               # original text, byte-for-byte
    assert row[1] == "manual_text" and row[2] == "unverified"
    assert row[3] == "https://x.com/acme_ceo/status/1"
    assert row[4] == job_lead_radar.content_hash("twitter", TEXT)
    assert row[5] is False and row[6] is False and row[7] is None   # genuine, not analysed, not classified
    assert row[8] == "pasted by operator"
    assert str(row[9]) == summary.run_id
    assert await read("select count(*) from job_leads") == [(0,)]     # no lead without operator fields or AI


async def test_run_is_recorded_with_counts(session_factory, read):
    s = await runner.run_posts([item(), item(text="Another post"), item(platform="myspace")],
                               label="counts", session_factory=session_factory)
    (run,) = await read("select source_type, source_label, status, records_seen, records_created, "
                        "records_rejected, finished_at is not null from ingestion_runs")
    assert run == ("manual_text", "counts", "completed_with_errors", 3, 2, 1, True)
    assert s.counts() == {"created": 2, "updated": 0, "duplicate": 0, "rejected": 1, "failed": 0}


async def test_identical_post_is_a_duplicate_even_with_different_whitespace(session_factory, read):
    await runner.run_posts([item()], session_factory=session_factory)
    again = await runner.run_posts(
        [item(text="  Acme is hiring   a Rust engineer.\r\n\r\nRemote, $180k-$220k. DM me!  ")], session_factory=session_factory)
    r = again.results[0]
    assert (r.status, r.code) == ("duplicate", "duplicate_content") and r.entity_id
    assert await read("select count(*) from raw_posts") == [(1,)]


async def test_same_text_on_another_platform_is_not_a_duplicate(session_factory, read):
    await runner.run_posts([item(platform="twitter"), item(platform="reddit")], session_factory=session_factory)
    assert await read("select count(*) from raw_posts") == [(2,)]


async def test_external_id_reuse_with_different_text_is_rejected(session_factory, read):
    await runner.run_posts([item(external_id="ext-1")], session_factory=session_factory)
    s = await runner.run_posts([item(external_id="ext-1", text="Completely different text")], session_factory=session_factory)
    assert (s.results[0].status, s.results[0].code) == ("rejected", "external_id_conflict")
    assert await read("select count(*) from raw_posts") == [(1,)]


@pytest.mark.parametrize("over,code", [
    ({"platform": "myspace"}, "invalid_platform"),
])
async def test_module_business_rules_reject_with_codes(session_factory, over, code):
    s = await runner.run_posts([item(**over)], session_factory=session_factory)
    assert (s.results[0].status, s.results[0].code) == ("rejected", code)


@pytest.mark.parametrize("data", [
    {"platform": "twitter"},                              # missing text
    {"platform": "twitter", "text": "   "},               # blank
    {"text": "hello"},                                    # missing platform
    {"platform": "twitter", "text": "x" * 20001},         # too long
    {"platform": "twitter", "text": "x", "surprise": 1},  # unknown field
    {"platform": "twitter", "text": "x", "structured": {"role_title": "Eng"}},   # incomplete structured block
])
async def test_invalid_or_incomplete_input_is_rejected_before_the_database(session_factory, read, data):
    s = await runner.run_posts([manual_posts._validate(0, data)], session_factory=session_factory)
    assert s.results[0].status == "rejected" and s.results[0].code == "invalid_input"
    assert await read("select count(*) from raw_posts") == [(0,)]


async def test_module_rejects_blank_structured_fields_even_if_called_directly(session_factory):
    ctx = IngestContext(source_type="manual_text")
    rec = job_lead_radar.PostRecord(platform="twitter", raw_content="hello world",
                                    structured=job_lead_radar.StructuredLead(role_title=" ", company_name="Acme"))
    async with session_factory() as db:
        r = await job_lead_radar.ingest_post_record(db, rec, ctx)
    assert (r.status, r.code) == ("rejected", "incomplete_structured_fields")


async def test_operator_entered_fields_create_a_lead_labelled_operator_entered(session_factory, read):
    s = await runner.run_posts([item(structured={
        "role_title": "Rust Engineer", "company_name": "Acme", "tech_stack": ["Rust"], "location_mode": "Remote"})],
        session_factory=session_factory)
    assert s.results[0].status == "created" and s.results[0].detail["awaiting_analysis"] is False
    (lead,) = await read("select role_title, company_name, entry_source, is_demo, match_score, comp_min, "
                         "urgency_tier, company_stage from job_leads")
    assert lead == ("Rust Engineer", "Acme", "operator_entered", False, None, None, None, None)
    (post,) = await read("select classification, is_processed, verification_status from raw_posts")
    assert post == ("hiring", True, "unverified")


async def test_dry_run_reports_exactly_but_writes_nothing(session_factory, read):
    await runner.run_posts([item()], session_factory=session_factory)
    s = await runner.run_posts([item(), item(text="brand new text")], dry_run=True, session_factory=session_factory)
    assert s.run_id is None and [r.status for r in s.results] == ["duplicate", "created"]
    assert await read("select count(*) from raw_posts") == [(1,)]
    assert await read("select count(*) from ingestion_runs") == [(1,)]      # only the first real run


async def test_a_failing_record_does_not_stop_the_batch(session_factory, read, monkeypatch):
    real = job_lead_radar.ingest_post_record

    async def flaky(db, record, ctx):
        if "BOOM" in record.raw_content:
            raise RuntimeError("simulated database failure")
        return await real(db, record, ctx)

    monkeypatch.setattr(job_lead_radar, "ingest_post_record", flaky)
    s = await runner.run_posts([item(text="first"), item(text="BOOM"), item(text="third")], session_factory=session_factory)
    assert [r.status for r in s.results] == ["created", "failed", "created"]
    assert s.results[1].code == "persistence_error"
    assert await read("select count(*) from raw_posts") == [(2,)]
    (run,) = await read("select status, records_failed from ingestion_runs")
    assert run == ("completed_with_errors", 1)


async def test_unreachable_database_aborts_the_run_with_a_clear_error():
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def broken():
        raise ConnectionRefusedError("db down")
        yield

    with pytest.raises(runner.IngestionAborted):
        await runner.run_posts([item()], session_factory=broken)


async def test_rollback_deletes_only_the_rows_of_that_run(session_factory, read):
    a = await runner.run_posts([item(text="run A post", structured={"role_title": "R", "company_name": "C"})], session_factory=session_factory)
    b = await runner.run_posts([item(text="run B post")], session_factory=session_factory)
    import uuid
    out = await runner.rollback_run(uuid.UUID(a.run_id), session_factory=session_factory)
    assert out == {"raw_posts_deleted": 1, "repositories_deleted": 0}
    rows = await read("select raw_content from raw_posts")
    assert rows == [("run B post",)] and await read("select count(*) from job_leads") == [(0,)]   # lead cascaded
    assert b.run_id


async def test_demo_showcase_is_labelled_and_removable_without_touching_genuine_rows(session_factory, read):
    from dbingestion.sources import demo_fixtures

    await runner.run_posts([item(text="a genuine post")], session_factory=session_factory)
    d = await runner.run_posts(demo_fixtures.posts(), source_type="demo_fixture", is_demo=True, session_factory=session_factory)
    r = await runner.run_demo_candidates(demo_fixtures.candidates(), session_factory=session_factory)
    n_posts, n_cands = len(demo_fixtures.posts()), len(demo_fixtures.candidates())
    n_leads = sum(1 for i in demo_fixtures.posts() if i.value.structured is not None)
    assert 0 < n_leads < n_posts            # the showcase also holds a job seeker and a post awaiting analysis
    assert d.counts()["created"] == n_posts and r.counts()["created"] == n_cands
    assert await read("select count(*) from raw_posts where is_demo and source_type='demo_fixture' and verification_status='demo_fixture'") == [(n_posts,)]
    assert await read("select count(*) from raw_posts where is_demo and classification='seeking' and is_processed") == [(1,)]
    assert await read("select count(*) from raw_posts where is_demo and not is_processed") == [(1,)]
    assert await read("select count(*) from job_leads where is_demo and entry_source='demo_fixture' and match_score is not null") == [(n_leads,)]
    assert await read("select count(*) from candidate_repos where is_demo and github_metadata is not null and metadata_fetched_at is null") == [(n_cands,)]
    assert await read("select count(*) from candidate_repos where is_demo and source_type='demo_fixture' and github_repo_id is null") == [(n_cands,)]
    assert await read("select count(*) from benchmark_suites") == [(n_cands,)]
    assert await read("select count(*) from code_evaluation_results") == [(n_cands,)]
    assert await read("select count(*) from voice_sessions where is_demo and defense_verdict='needs_human_review'") == [(n_cands,)]
    assert await read("select count(*) from leaderboard_scores where is_demo and status_tag='needs_human_review'") == [(n_cands,)]
    # loading twice is idempotent
    again = await runner.run_demo_candidates(demo_fixtures.candidates(), session_factory=session_factory)
    assert again.counts()["created"] == 0 and again.counts()["duplicate"] == n_cands

    out = await runner.remove_demo(session_factory=session_factory)
    assert out == {"raw_posts_deleted": n_posts, "repositories_deleted": n_cands,
                   "interview_sessions_deleted": n_cands, "leaderboard_rows_deleted": n_cands}
    assert await read("select raw_content from raw_posts") == [("a genuine post",)]
    assert await read("select count(*) from benchmark_suites") == [(0,)]


async def test_demo_classification_is_refused_for_genuine_records(session_factory, read):
    s = await runner.run_posts([item(demo_classification="seeking")], session_factory=session_factory)
    assert (s.results[0].status, s.results[0].code) == ("rejected", "unmeasured_fields_not_allowed")
    assert await read("select count(*) from raw_posts") == [(0,)]


async def test_unmeasured_values_are_refused_for_genuine_records(session_factory, read):
    s = await runner.run_posts(
        [item(structured={"role_title": "Dev", "company_name": "Real Co", "match_score": 99, "urgency_tier": "Immediate"})],
        session_factory=session_factory)
    assert (s.results[0].status, s.results[0].code) == ("rejected", "unmeasured_fields_not_allowed")
    assert await read("select count(*) from raw_posts") == [(0,)]


def test_file_sources(tmp_path):
    jl = tmp_path / "posts.jsonl"
    jl.write_text('{"platform":"reddit","text":"hello"}\nnot json\n\n{"platform":"reddit"}\n')
    items = manual_posts.from_file(str(jl))
    assert [i.value is not None for i in items] == [True, False, False]
    assert items[1].error_code == "invalid_json" and items[2].error_code == "invalid_input"

    txt = tmp_path / "post.txt"
    txt.write_text("whole file is one post")
    assert manual_posts.from_file(str(txt))[0].error_code == "missing_platform"
    ok = manual_posts.from_file(str(txt), platform="telegram")
    assert ok[0].value.text == "whole file is one post"

    arr = tmp_path / "a.json"
    arr.write_text(json.dumps({"records": [{"platform": "twitter", "text": "t"}]}))
    assert manual_posts.from_file(str(arr))[0].value.platform == "twitter"
    bad = tmp_path / "b.json"
    bad.write_text("{oops")
    assert manual_posts.from_file(str(bad))[0].error_code == "invalid_json"
    with pytest.raises(FileNotFoundError):
        manual_posts.from_file(str(tmp_path / "missing.json"))
