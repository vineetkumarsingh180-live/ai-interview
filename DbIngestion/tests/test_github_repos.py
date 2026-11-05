"""GitHub metadata ingestion through the supported REST API (mocked transport; no network)."""
import httpx
import pytest

from app.modules import code_verifier
from app.shared.github import GitHubClient, GitHubError
from app.shared.ingestion_log import IngestContext
from dbingestion import runner
from dbingestion.sources import github_repos

pytestmark = pytest.mark.anyio

REPO = {
    "id": 424242, "name": "engine", "full_name": "ada/engine", "html_url": "https://github.com/ada/engine",
    "description": "A tiny engine", "default_branch": "trunk", "language": "Rust", "stargazers_count": 7,
    "forks_count": 2, "open_issues_count": 1, "license": {"spdx_id": "MIT"}, "topics": ["engine", "rust"],
    "visibility": "public", "archived": False, "fork": False, "size": 321,
    "created_at": "2024-01-02T03:04:05Z", "pushed_at": "2025-05-06T07:08:09Z", "updated_at": "2025-05-06T07:08:09Z",
    "owner": {"login": "ada", "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4"},
}
SHA = "0123456789abcdef0123456789abcdef01234567"


def make_client(repo=REPO, *, languages=None, branch_status=200, repo_status=200, headers=None, calls=None, token=""):
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append((request.method, request.url.path, dict(request.headers)))
        path = request.url.path
        if path == f"/repos/ada/engine" or path.endswith("/engine") and "/repos/" in path and path.count("/") == 3:
            return httpx.Response(repo_status, json=repo if repo_status == 200 else {"message": "x"}, headers=headers or {})
        if path.endswith("/languages"):
            return httpx.Response(200, json=languages if languages is not None else {"Rust": 9000, "Shell": 100})
        if "/branches/" in path:
            return httpx.Response(branch_status, json={"commit": {"sha": SHA}} if branch_status == 200 else {"message": "Branch not found"})
        return httpx.Response(404, json={"message": "not mocked"})

    return GitHubClient(token=token, base_url="https://api.github.test", transport=httpx.MockTransport(handler))


def one(url="https://github.com/ada/engine", **over):
    return github_repos.from_urls([url], **over)


async def test_only_github_returned_facts_are_persisted(session_factory, read):
    s = await runner.run_github(one(), client=make_client(), label="unit", session_factory=session_factory)
    assert s.results[0].status == "created"
    (r,) = await read("select candidate_name, candidate_github_handle, candidate_avatar_url, repo_url, repo_name, "
                      "branch, commit_sha, language, status, source_type, verification_status, is_demo, github_repo_id, "
                      "github_metadata, metadata_fetched_at is not null, target_role from candidate_repos")
    assert r[:3] == ("ada", "ada", "https://avatars.githubusercontent.com/u/1?v=4")   # no real name known: owner login
    assert r[3:8] == ("https://github.com/ada/engine", "engine", "trunk", SHA, "Rust")
    assert r[8:12] == ("awaiting_analysis", "github_api", "github_metadata", False)
    assert r[12] == 424242 and r[14] is True and r[15] is None
    meta = r[13]
    assert meta["stars"] == 7 and meta["license"] == "MIT" and meta["topics"] == ["engine", "rust"]
    assert meta["languages_bytes"] == {"Rust": 9000, "Shell": 100}
    assert await read("select count(*) from benchmark_suites") == [(0,)]
    assert await read("select count(*) from code_evaluation_results") == [(0,)]


async def test_operator_supplied_name_and_role_are_kept_as_provided(session_factory, read):
    await runner.run_github(one(candidate_name="Ada Lovelace", target_role="Backend"), client=make_client(), session_factory=session_factory)
    assert await read("select candidate_name, target_role, candidate_github_handle from candidate_repos") == [("Ada Lovelace", "Backend", "ada")]


async def test_nothing_is_invented_when_github_returns_no_language_or_head_commit(session_factory, read):
    repo = {**REPO, "language": None, "license": None, "topics": []}
    await runner.run_github(one(), client=make_client(repo, languages={}, branch_status=409), session_factory=session_factory)
    (r,) = await read("select language, commit_sha, github_metadata->>'license' from candidate_repos")
    assert r == (None, None, None)


async def test_reingest_unchanged_is_duplicate_and_changed_is_updated(session_factory, read):
    await runner.run_github(one(), client=make_client(), session_factory=session_factory)
    same = await runner.run_github(one(), client=make_client(), session_factory=session_factory)
    assert (same.results[0].status, same.results[0].code) == ("duplicate", "unchanged")

    changed = await runner.run_github(one(), client=make_client({**REPO, "stargazers_count": 99}), session_factory=session_factory)
    assert (changed.results[0].status, changed.results[0].code) == ("updated", "metadata_refreshed")
    assert await read("select count(*), max((github_metadata->>'stars')::int) from candidate_repos") == [(1, 99)]


async def test_github_facts_attach_to_a_row_that_was_typed_in_earlier(session_factory, read):
    ctx = IngestContext(source_type="api_manual")
    async with session_factory() as db:
        r = await code_verifier.register_repository_url(db, code_verifier.RepoRecord("https://github.com/Ada/Engine", "Ada L."), ctx)
        await db.commit()
    assert r.status == "created"
    s = await runner.run_github(one(), client=make_client(), session_factory=session_factory)
    assert s.results[0].status == "updated"
    assert await read("select count(*), min(candidate_name), min(language), min(verification_status) from candidate_repos") == [(1, "Ada L.", "Rust", "github_metadata")]


@pytest.mark.parametrize("kwargs,status,code", [
    (dict(repo_status=404), "rejected", "github_not_found"),
    (dict(repo_status=500), "failed", "github_unavailable"),
    (dict(repo_status=403, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1700000000"}), "failed", "github_rate_limited"),
    (dict(repo_status=403), "rejected", "github_forbidden"),
])
async def test_github_errors_become_structured_results_and_write_nothing(session_factory, read, kwargs, status, code):
    s = await runner.run_github(one(), client=make_client(**kwargs), session_factory=session_factory)
    assert (s.results[0].status, s.results[0].code) == (status, code) and s.results[0].message
    assert await read("select count(*) from candidate_repos") == [(0,)]
    assert (await read("select status from ingestion_runs"))[0][0] == "completed_with_errors"


async def test_malformed_payload_and_transport_failure(session_factory):
    bad = make_client({"unexpected": True})
    s = await runner.run_github(one(), client=bad, session_factory=session_factory)
    assert (s.results[0].status, s.results[0].code) == ("failed", "github_invalid_response")

    def boom(_req):
        raise httpx.ConnectError("no route")

    down = GitHubClient(token="", base_url="https://api.github.test", transport=httpx.MockTransport(boom))
    s2 = await runner.run_github(one(), client=down, session_factory=session_factory)
    assert (s2.results[0].status, s2.results[0].code) == ("failed", "github_unavailable")


async def test_non_github_urls_are_rejected_without_any_network_call(session_factory):
    calls = []
    items = github_repos.from_urls(["https://gitlab.com/a/b", "not a url", "https://github.com/onlyowner"])
    s = await runner.run_github(items, client=make_client(calls=calls), session_factory=session_factory)
    assert [r.code for r in s.results] == ["invalid_github_url"] * 3 and calls == []


async def test_token_is_optional_and_only_sent_when_configured():
    calls = []
    await make_client(calls=calls).fetch_repository("ada", "engine")
    assert all("authorization" not in h for _, _, h in calls)
    calls2 = []
    await make_client(calls=calls2, token="ghp_example").fetch_repository("ada", "engine")
    assert all(h.get("authorization") == "Bearer ghp_example" for _, _, h in calls2)
    # only metadata endpoints are used: no archive/tarball/contents/git endpoints
    assert {p.split("/")[-1] for _, p, _ in calls} <= {"engine", "languages", "trunk"}


async def test_dry_run_fetches_but_writes_nothing(session_factory, read):
    s = await runner.run_github(one(), client=make_client(), dry_run=True, session_factory=session_factory)
    assert s.results[0].status == "created" and s.run_id is None
    assert await read("select count(*) from candidate_repos") == [(0,)]


def test_github_file_sources(tmp_path):
    f = tmp_path / "repos.txt"
    f.write_text("# comment\nhttps://github.com/a/b\n\nhttps://github.com/c/d\n")
    assert [i.value.repo_url for i in github_repos.from_file(str(f))] == ["https://github.com/a/b", "https://github.com/c/d"]
    j = tmp_path / "repos.json"
    j.write_text('[{"repo_url":"https://github.com/a/b","candidate_name":"X"},{"nope":1}]')
    items = github_repos.from_file(str(j))
    assert items[0].value.candidate_name == "X" and items[1].error_code == "invalid_input"
