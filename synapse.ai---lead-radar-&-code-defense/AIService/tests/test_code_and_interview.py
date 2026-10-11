import pytest

from aiservice import (
    CodeIntelligence,
    InterviewIntelligence,
    ProviderTimeout,
    Turn,
    prepare_evidence,
)
from aiservice.code_intelligence.evidence import MAX_FILES, RepositoryEvidence

pytestmark = pytest.mark.anyio

FILES = [
    ("src/main.py", "def handler(event):\n    return cache.get(event.key)\n"),
    ("tests/test_main.py", "def test_handler():\n    assert True\n"),
    ("requirements.txt", "httpx==0.28.1\n"),
    ("src/lib.rs", "pub fn run() {}\n"),
]


# ---- evidence preparation (deterministic, no provider) -----------------------------------------
def test_sensitive_and_binary_files_are_excluded_before_any_prompt():
    ev = prepare_evidence("https://github.com/o/r", FILES + [
        (".env", "API_KEY=abc"), ("deploy/id_rsa", "x"), ("certs/server.pem", "x"),
        ("src/conf.py", "token = 'AKIAABCDEFGHIJKLMNOP'"), ("logo.png", "\x00\x01"), ("../etc/passwd", "root"),
    ])
    assert ev.paths == ["src/main.py", "tests/test_main.py", "requirements.txt", "src/lib.rs"]
    assert set(ev.excluded.values()) == {"sensitive_filename", "secret_like_content", "binary", "invalid_path"}
    assert all("API_KEY" not in f.content for f in ev.files)


def test_limits_are_enforced_and_reported():
    many = [(f"f{i}.py", "x = 1\n") for i in range(MAX_FILES + 5)]
    ev = prepare_evidence("u", many)
    assert len(ev.files) == MAX_FILES and ev.truncated and ev.excluded["f%d.py" % MAX_FILES] == "file_limit"
    big = prepare_evidence("u", [("big.py", "a" * 50_000)])
    assert len(big.files[0].content) == 12_000 and big.truncated


def test_facts_are_counted_not_guessed():
    facts = prepare_evidence("u", FILES).facts()
    assert facts["files_inspected"] == 4
    assert facts["languages_by_file_count"] == {"Python": 2, "Rust": 1}
    assert facts["test_files"] == ["tests/test_main.py"] and facts["dependency_manifests"] == ["requirements.txt"]
    assert "coverage" not in " ".join(facts)          # coverage is never claimed


# ---- code intelligence ---------------------------------------------------------------------------
async def test_metadata_only_repository_stays_unanalysed_and_never_calls_the_provider(fake):
    p = fake({"summary": "x"})
    r = await CodeIntelligence(p).analyze(RepositoryEvidence(repo_url="https://github.com/o/r"))
    assert (r.status, r.reason) == ("unavailable", "repository_content_not_available") and p.prompts == []


async def test_without_a_key_only_deterministic_facts_are_returned(fake):
    r = await CodeIntelligence(fake(configured=False)).analyze(prepare_evidence("u", FILES))
    assert r.status == "unavailable" and r.reason == "not_configured"
    assert r.facts["files_inspected"] == 4 and r.summary is None and r.findings == []


async def test_only_cited_and_quoted_claims_survive(fake):
    reply = {
        "summary": "A small handler with a cache lookup.", "summary_paths": ["src/main.py", "ghost.py"],
        "findings": [
            {"statement": "Reads from a cache", "path": "src/main.py", "quote": "cache.get(event.key)"},
            {"statement": "Uses eval", "path": "src/main.py", "quote": "eval(user_input)"},         # not in file
            {"statement": "Has a backdoor", "path": "src/other.py", "quote": "x"},                  # not supplied
        ],
        "interview_topics": ["Cache invalidation", " "],
    }
    r = await CodeIntelligence(fake(reply)).analyze(prepare_evidence("u", FILES))
    assert r.status == "analyzed" and r.summary_paths == ["src/main.py"]
    assert [f.path for f in r.findings] == ["src/main.py"] and r.discarded_claims == 2
    assert r.interview_topics == ["Cache invalidation"]


async def test_summary_without_a_valid_citation_is_discarded(fake):
    r = await CodeIntelligence(fake({"summary": "Looks fine", "summary_paths": []})).analyze(prepare_evidence("u", FILES))
    assert r.summary is None and r.discarded_claims == 1


async def test_invalid_json_from_provider_keeps_facts(fake):
    r = await CodeIntelligence(fake("nope")).analyze(prepare_evidence("u", FILES))
    assert r.status == "invalid_response" and r.facts["files_inspected"] == 4


# ---- interview intelligence -----------------------------------------------------------------------
DIALOGUE = [Turn("ai_interviewer", "Walk me through it."), Turn("candidate", "I use an LRU cache.")]


async def test_follow_up_is_generated_from_the_real_dialogue(fake):
    p = fake("How do you evict stale entries?")
    r = await InterviewIntelligence(p).follow_up_question(DIALOGUE)
    assert (r.status, r.question) == ("generated", "How do you evict stale entries?")
    assert "candidate: I use an LRU cache." in p.prompts[0]


async def test_follow_up_unavailable_without_key_and_no_canned_question(fake):
    r = await InterviewIntelligence(fake(configured=False)).follow_up_question(DIALOGUE)
    assert (r.status, r.question) == ("unavailable", None)


async def test_follow_up_requires_an_actual_candidate_answer(fake):
    p = fake("Q?")
    r = await InterviewIntelligence(p).follow_up_question([Turn("ai_interviewer", "Walk me through it.")])
    assert r.status == "invalid_response" and p.prompts == []


async def test_follow_up_provider_timeout_is_unavailable(fake):
    r = await InterviewIntelligence(fake(error=ProviderTimeout("slow"))).follow_up_question(DIALOGUE)
    assert (r.status, r.reason) == ("unavailable", "timeout")


async def test_repository_questions_need_repository_content(fake):
    r = await InterviewIntelligence(fake({"questions": []})).repository_questions(RepositoryEvidence(repo_url="u"))
    assert (r.status, r.reason) == ("unavailable", "repository_content_not_available")


async def test_repository_questions_must_cite_supplied_files(fake):
    reply = {"questions": [
        {"question": "Why cache by event.key?", "paths": ["src/main.py"]},
        {"question": "Explain your Kubernetes operator", "paths": ["k8s/operator.go"]},   # not supplied
        {"question": "Generic question", "paths": []},
    ]}
    r = await InterviewIntelligence(fake(reply)).repository_questions(prepare_evidence("u", FILES))
    assert r.status == "generated" and [q.paths for q in r.questions] == [["src/main.py"]] and r.discarded == 2


async def test_all_uncited_questions_is_an_invalid_response_not_a_generic_fallback(fake):
    r = await InterviewIntelligence(fake({"questions": [{"question": "Tell me about yourself", "paths": []}]})).repository_questions(prepare_evidence("u", FILES))
    assert r.status == "invalid_response" and r.questions == []
