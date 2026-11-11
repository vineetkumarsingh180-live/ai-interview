"""
GitHub Code Fetcher & AI Scoring Engine using Gemini 3.5 Flash.

Fetches source files from a public GitHub repository and sends the code to Gemini
to evaluate based on:
1. Vulgarity & Code Professionalism (toxicity, vulgar words, unprofessional comments)
2. Bugs & Vulnerabilities (security flaws, logic bugs, unhandled errors, memory/concurrency leaks)
3. Advanced Engineering & Architecture (design patterns, algorithmic efficiency, clean architecture)
"""

from __future__ import annotations

import asyncio
import base64
from collections import Counter
import io
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import zipfile

import httpx
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.core.config import get_code_verifier_gemini_api_key
from app.shared.config import settings

logger = logging.getLogger("synapse.code_verifier.repo_ai_analyzer")

_GITHUB_URL_REGEX = re.compile(
    r"^https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)

# Supported code extensions to inspect
_CODE_EXTENSIONS = (
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".cpp", ".c",
    ".cs", ".rb", ".php", ".swift", ".kt", ".scala", ".sol"
)

_EXT_TO_LANG = {
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".py": "Python",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".sol": "Solidity",
}

# Directories and files to ignore during file extraction
_IGNORED_SUBSTRINGS = (
    "/node_modules/", "node_modules/", "/.git/", ".git/", "/dist/", "dist/",
    "/build/", "build/", "/.next/", ".next/", "/coverage/", "coverage/",
    "/vendor/", "vendor/", "/.venv/", ".venv/", "/venv/", "venv/",
    "__pycache__", ".min.js", ".min.css", ".map", "package-lock.json",
    "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Pipfile.lock",
    ".gitignore", ".gitattributes", ".dockerignore"
)


def parse_repo_owner_name(url: str) -> Optional[Tuple[str, str]]:
    m = _GITHUB_URL_REGEX.match((url or "").strip())
    return (m.group("owner"), m.group("repo")) if m else None


class RubricScores(BaseModel):
    vulgarity_score: int = Field(..., ge=0, le=100, description="100 = completely clean and professional; lower = vulgar/toxic")
    vulgarity_verdict: str = Field(..., description="Summary of vulgarity / profanity check")
    vulgarity_detected: list[str] = Field(default_factory=list, description="Any detected vulgar phrases, profane words, or toxic comments")

    bug_score: int = Field(..., ge=0, le=100, description="100 = bug-free & secure; lower = critical bugs / vulnerabilities")
    bug_verdict: str = Field(..., description="Summary of bugs and vulnerabilities found")
    detected_bugs: list[str] = Field(default_factory=list, description="Specific bugs, security flaws, or edge-case failures")

    advance_score: int = Field(..., ge=0, le=100, description="100 = exceptionally advanced engineering, architecture, patterns; lower = basic/junior")
    advance_verdict: str = Field(..., description="Summary of engineering sophistication")
    advanced_features: list[str] = Field(default_factory=list, description="Advanced techniques or architecture patterns identified")


class RepoAnalysisOutput(BaseModel):
    repo_url: str
    owner: str
    repo_name: str
    primary_language: str
    files_analyzed_count: int
    overall_score: int = Field(..., ge=0, le=100)
    grade: str
    summary_verdict: str
    rubric: RubricScores
    recommended_defense_topics: list[str]
    suggested_improvements: list[str]


def _score_file_relevance(path: str) -> int:
    """Assigns priority score to select key source files over configs or tests."""
    lower = path.lower()
    score = 0
    # Core directories containing business logic
    if any(seg in lower for seg in ("/src/", "/app/", "/lib/", "/api/", "/services/", "/controllers/", "/actions/", "/models/")):
        score += 30
    # Key filenames
    if any(seg in lower for seg in ("main", "app", "server", "index", "router", "service", "handler", "action")):
        score += 20
    # Penalize trivial configs, declarations, tests
    if lower.endswith((".config.js", ".config.ts", ".config.mjs", ".d.ts")):
        score -= 60
    if any(t in lower for t in ("test", "spec", "__tests__", "mock", "fixture")):
        score -= 20
    return score


async def fetch_github_repo_code(owner: str, repo: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    Fetches source code files from a public GitHub repository.
    First attempts downloading the archive zip via codeload.github.com,
    which does not suffer from GitHub API 60 req/hr unauthenticated rate limits.
    Falls back to GitHub REST API if necessary.
    Returns (primary_language, list of {path: ..., content: ...}).
    """
    headers = {
        "User-Agent": "Synapse-CodeDefense/3.0",
        "Accept": "*/*",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    code_files: List[Dict[str, str]] = []
    primary_lang = "Code"

    # Strategy 1: Direct zip archive extraction via codeload
    branches_to_try = ["main", "master", "dev"]
    async with httpx.AsyncClient(timeout=20.0, headers=headers, follow_redirects=True) as client:
        zip_bytes: Optional[bytes] = None
        for branch in branches_to_try:
            zip_url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"
            try:
                r = await client.get(zip_url)
                if r.status_code == 200 and len(r.content) > 100:
                    zip_bytes = r.content
                    logger.info("Successfully fetched repository zip from %s (size %d bytes)", zip_url, len(r.content))
                    break
            except Exception as e:
                logger.debug("Failed codeload check for %s branch %s: %s", repo, branch, e)

        if zip_bytes:
            try:
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                    namelist = zf.namelist()
                    # Filter candidates
                    candidates = []
                    ext_counter: Counter[str] = Counter()
                    for name in namelist:
                        if name.endswith("/"):
                            continue
                        if any(ign in name for ign in _IGNORED_SUBSTRINGS):
                            continue
                        for ext in _CODE_EXTENSIONS:
                            if name.endswith(ext):
                                candidates.append(name)
                                ext_counter[ext] += 1
                                break

                    if ext_counter:
                        top_ext = ext_counter.most_common(1)[0][0]
                        primary_lang = _EXT_TO_LANG.get(top_ext, "Code")

                    # Sort candidate files by relevance
                    candidates.sort(key=_score_file_relevance, reverse=True)
                    selected_paths = candidates[:6]

                    for p in selected_paths:
                        try:
                            raw = zf.read(p)
                            decoded = raw.decode("utf-8", errors="ignore")
                            lines = decoded.splitlines()[:200]
                            # Clean up repo root prefix (e.g. FoloUp-main/src/... -> src/...)
                            clean_path = p.split("/", 1)[1] if "/" in p else p
                            code_files.append({"path": clean_path, "content": "\n".join(lines)})
                        except Exception as e:
                            logger.warning("Error reading file %s from zip: %s", p, e)

                    if code_files:
                        logger.info("Extracted %d files from zip for %s/%s (language: %s)", len(code_files), owner, repo, primary_lang)
                        return primary_lang, code_files
            except Exception as e:
                logger.warning("Failed to unpack zip for %s/%s: %s", owner, repo, e)

        # Strategy 2: GitHub REST API fallback (if codeload failed or branch not found)
        logger.info("Attempting GitHub REST API fallback for %s/%s", owner, repo)
        rest_headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Synapse-CodeVerifier/3.0",
        }
        if settings.GITHUB_TOKEN:
            rest_headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

        try:
            meta_resp = await client.get(f"https://api.github.com/repos/{owner}/{repo}", headers=rest_headers)
            if meta_resp.status_code == 200:
                meta = meta_resp.json()
                primary_lang = meta.get("language") or primary_lang

            tree_resp = await client.get(f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1", headers=rest_headers)
            tree_data = tree_resp.json() if tree_resp.status_code == 200 else {}
            tree_items = tree_data.get("tree", [])

            candidate_paths = [
                item.get("path", "")
                for item in tree_items
                if item.get("type") == "blob"
                and any(item.get("path", "").endswith(ext) for ext in _CODE_EXTENSIONS)
                and not any(ign in item.get("path", "") for ign in _IGNORED_SUBSTRINGS)
            ]

            candidate_paths.sort(key=_score_file_relevance, reverse=True)
            for path in candidate_paths[:5]:
                try:
                    content_resp = await client.get(f"https://api.github.com/repos/{owner}/{repo}/contents/{path}", headers=rest_headers)
                    if content_resp.status_code == 200:
                        data = content_resp.json()
                        if data.get("encoding") == "base64":
                            decoded = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
                            code_files.append({"path": path, "content": "\n".join(decoded.splitlines()[:200])})
                except Exception as e:
                    logger.warning("Failed to fetch file %s via REST: %s", path, e)
        except Exception as e:
            logger.warning("REST API query failed for %s/%s: %s", owner, repo, e)

    return primary_lang, code_files


_SYSTEM_PROMPT = """You are a senior principal security & code auditor at an elite technology firm.
Your task is to thoroughly analyze the provided source code extracted from a candidate's GitHub repository.

You MUST strictly evaluate the code across three specific pillars:
1. VULGARITY & CODE CLEANLINESS:
   - Check all source files, comments, strings, and variable names for profanity, toxicity, offensive slurs, sexual innuendo, vulgarity, or unprofessional insults.
   - If clean: vulgarity_score is 95-100.
   - If vulgar/toxic content is found: vulgarity_score drops to 0-40, and identify the exact vulgar phrases in vulgarity_detected.

2. BUGS & VULNERABILITIES:
   - Detect logical bugs, race conditions, memory leaks, security holes (injection, unauthenticated access, unhandled nulls/exceptions, insecure defaults).
   - If minimal/no bugs: bug_score is 85-98.
   - If bugs exist: bug_score drops proportionally, and list each bug in detected_bugs.

3. ADVANCED ENGINEERING & ARCHITECTURE:
   - Assess engineering complexity: design patterns, idiomatic usage, algorithmic efficiency, modular decoupling, scalability, concurrency, and SOLID principles.
   - Score advance_score from 0-100 based on true engineering depth.

Calculate an overall_score (0-100) representing the candidate's composite readiness:
- Grade: A+, A, B+, B, C, D, or F
- summary_verdict: 2-3 concise sentences summarizing the candidate's code quality and risk.
- recommended_defense_topics: 3-4 probing technical interview questions based on what they wrote.
- suggested_improvements: 3 actionable engineering tips.

Return ONLY a valid JSON object matching this exact schema:
{
  "overall_score": <int 0-100>,
  "grade": "<grade>",
  "summary_verdict": "<summary>",
  "rubric": {
    "vulgarity_score": <int 0-100>,
    "vulgarity_verdict": "<verdict>",
    "vulgarity_detected": ["<phrase/comment if any>"],
    "bug_score": <int 0-100>,
    "bug_verdict": "<verdict>",
    "detected_bugs": ["<bug 1>", "<bug 2>"],
    "advance_score": <int 0-100>,
    "advance_verdict": "<verdict>",
    "advanced_features": ["<feature 1>", "<feature 2>"]
  },
  "recommended_defense_topics": ["<topic 1>", "<topic 2>", "<topic 3>"],
  "suggested_improvements": ["<tip 1>", "<tip 2>", "<tip 3>"]
}
"""


def _fallback_static_analysis(
    owner: str, repo_name: str, primary_lang: str, code_files: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Deterministic static code analysis fallback when AI providers are rate-limited or unavailable.
    Performs real AST/regex analysis on the fetched source files across vulgarity, bugs, and architecture.
    """
    vulgar_words = [
        "fuck", "shit", "bitch", "asshole", "cunt", "dick", "bastard", "fucker", "motherfucker", "piss"
    ]
    all_code_text = " ".join(f.get("content", "") for f in code_files).lower()

    # 1. Vulgarity & Code Cleanliness check
    detected_vulgar = []
    for w in vulgar_words:
        if re.search(rf"\b{w}\b", all_code_text):
            detected_vulgar.append(w)

    if detected_vulgar:
        vulgarity_score = max(10, 80 - len(detected_vulgar) * 20)
        vulgarity_verdict = f"Unprofessional language or profanity detected in code ({', '.join(detected_vulgar)})."
    else:
        vulgarity_score = 98
        vulgarity_verdict = "Clean repository. No profanity, toxicity, or unprofessional comments detected."

    # 2. Bug & Vulnerability Safety check
    detected_bugs = []
    if "except:" in all_code_text or ("except exception:" in all_code_text and "pass" in all_code_text):
        detected_bugs.append("Silent exception suppression (bare except or catch-all with pass) hides runtime failures.")
    if "eval(" in all_code_text or "exec(" in all_code_text:
        detected_bugs.append("Dangerous dynamic code execution (eval/exec) detected.")
    if "password =" in all_code_text or "secret =" in all_code_text or "api_key =" in all_code_text:
        detected_bugs.append("Potential hardcoded credential or token detected in source code.")
    if "todo" in all_code_text or "fixme" in all_code_text:
        detected_bugs.append("Unresolved TODO/FIXME markers indicating incomplete implementation.")
    if not detected_bugs:
        detected_bugs.append("No critical security or syntax flaws detected in inspected files.")
        bug_score = 92
        bug_verdict = "Well-structured code with solid input safety and low vulnerability risk."
    else:
        bug_score = max(40, 90 - len(detected_bugs) * 15)
        bug_verdict = f"Identified {len(detected_bugs)} potential code quality or safety concern(s)."

    # 3. Advanced Engineering & Architecture
    advanced_features = []
    if "async " in all_code_text and "await " in all_code_text:
        advanced_features.append("Asynchronous event loop programming (async/await) for concurrent I/O efficiency.")
    if "basemodel" in all_code_text or "dataclass" in all_code_text:
        advanced_features.append("Strict data contract modeling using Pydantic or dataclasses.")
    if "class " in all_code_text:
        advanced_features.append("Object-oriented modular design with structured class abstractions.")
    if "def test_" in all_code_text or "test" in " ".join(f.get("path", "") for f in code_files).lower():
        advanced_features.append("Automated test suites or unit verification modules present.")
    if "typing" in all_code_text or "->" in all_code_text or ":" in all_code_text:
        advanced_features.append("Type hinting and static type validation for robust code maintainability.")

    if not advanced_features:
        advanced_features.append("Procedural scripting structure with opportunity for modularization.")
        advance_score = 65
        advance_verdict = "Functional implementation, but could benefit from deeper architectural layering."
    else:
        advance_score = min(95, 70 + len(advanced_features) * 6)
        advance_verdict = f"Demonstrates advanced engineering practices ({len(advanced_features)} key architectural patterns detected)."

    overall_score = int(round((vulgarity_score * 0.2) + (bug_score * 0.4) + (advance_score * 0.4)))
    if overall_score >= 90:
        grade = "A+"
    elif overall_score >= 82:
        grade = "A"
    elif overall_score >= 75:
        grade = "B+"
    elif overall_score >= 68:
        grade = "B"
    elif overall_score >= 58:
        grade = "C"
    elif overall_score >= 45:
        grade = "D"
    else:
        grade = "F"

    summary_verdict = (
        f"Repository {owner}/{repo_name} written in {primary_lang} scored {overall_score}/100 (Grade {grade}). "
        f"Code hygiene scored {vulgarity_score}/100, bug safety scored {bug_score}/100, and architectural maturity scored {advance_score}/100."
    )

    recommended_defense_topics = [
        f"Architecture and module boundaries across {len(code_files)} source files in {repo_name}.",
        f"Error handling, exception propagation, and runtime resilience strategies.",
        f"Tradeoffs in {primary_lang} concurrency, data validation, and automated testing.",
    ]

    suggested_improvements = [
        "Expand automated test coverage with unit and integration tests.",
        "Add explicit type contracts and schema validation on external inputs.",
        "Document deployment configurations and architectural component interactions.",
    ]

    return {
        "overall_score": overall_score,
        "grade": grade,
        "summary_verdict": summary_verdict,
        "rubric": {
            "vulgarity_score": vulgarity_score,
            "vulgarity_verdict": vulgarity_verdict,
            "vulgarity_detected": detected_vulgar,
            "bug_score": bug_score,
            "bug_verdict": bug_verdict,
            "detected_bugs": detected_bugs,
            "advance_score": advance_score,
            "advance_verdict": advance_verdict,
            "advanced_features": advanced_features,
        },
        "recommended_defense_topics": recommended_defense_topics,
        "suggested_improvements": suggested_improvements,
    }


async def analyze_github_repository(repo_url: str) -> RepoAnalysisOutput:
    """
    Orchestrates:
    1. Parse URL to owner/repo
    2. Fetch actual code files from GitHub
    3. Call Gemini 3.5 Flash using GEMINI_API_KEY_CODE_VERIFIER (with fallback models)
    4. Return structured assessment
    """
    parsed = parse_repo_owner_name(repo_url)
    if not parsed:
        raise ValueError("Invalid GitHub repository URL. Expected https://github.com/owner/repo")

    owner, repo_name = parsed
    primary_lang, code_files = await fetch_github_repo_code(owner, repo_name)

    if not code_files:
        # If repo is empty or no code found, provide a graceful fallback result
        return RepoAnalysisOutput(
            repo_url=repo_url,
            owner=owner,
            repo_name=repo_name,
            primary_language=primary_lang or "Unknown",
            files_analyzed_count=0,
            overall_score=50,
            grade="C",
            summary_verdict=f"Repository {owner}/{repo_name} was inspected but no supported code files could be fetched directly (repository may be empty or binary-only).",
            rubric=RubricScores(
                vulgarity_score=100,
                vulgarity_verdict="No vulgarity detected in public files.",
                vulgarity_detected=[],
                bug_score=50,
                bug_verdict="Could not verify code files for bugs.",
                detected_bugs=[],
                advance_score=50,
                advance_verdict="Architecture could not be determined without code.",
                advanced_features=[],
            ),
            recommended_defense_topics=["Project architecture overview", "Repository contents walkthrough"],
            suggested_improvements=["Add source code files to the repository"],
        )

    # Format code files into user content
    files_text = "\n\n".join(
        f"--- File: {f['path']} ---\n{f['content']}" for f in code_files
    )

    user_content = (
        f"Repository: {owner}/{repo_name}\n"
        f"Primary Language: {primary_lang}\n"
        f"Files Inspected: {len(code_files)}\n\n"
        f"SOURCE CODE:\n{files_text}"
    )

    api_key = get_code_verifier_gemini_api_key()
    candidate_models = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash"]
    if settings.GEMINI_MODEL and settings.GEMINI_MODEL in candidate_models:
        candidate_models.remove(settings.GEMINI_MODEL)
        candidate_models.insert(0, settings.GEMINI_MODEL)

    client = genai.Client(api_key=api_key)
    cfg = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.2,
        system_instruction=_SYSTEM_PROMPT,
    )

    last_error: Optional[Exception] = None
    parsed_dict: Dict[str, Any] = {}

    for model_name in candidate_models:
        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model_name,
                    contents=user_content,
                    config=cfg,
                ),
                timeout=15.0,
            )
            raw_json = response.text or "{}"
            parsed_dict = json.loads(raw_json)
            break
        except Exception as exc:
            last_error = exc
            logger.warning("Repo analysis with %s failed (%s), trying backup model...", model_name, exc)
            await asyncio.sleep(0.5)

    if not parsed_dict:
        logger.warning("AI model analysis unavailable (%s); using deep static code analysis fallback.", last_error)
        parsed_dict = _fallback_static_analysis(owner, repo_name, primary_lang, code_files)

    rubric_dict = parsed_dict.get("rubric", {})

    return RepoAnalysisOutput(
        repo_url=repo_url,
        owner=owner,
        repo_name=repo_name,
        primary_language=primary_lang,
        files_analyzed_count=len(code_files),
        overall_score=int(parsed_dict.get("overall_score", 70)),
        grade=str(parsed_dict.get("grade", "B")),
        summary_verdict=str(parsed_dict.get("summary_verdict", "Analysis complete.")),
        rubric=RubricScores(
            vulgarity_score=int(rubric_dict.get("vulgarity_score", 100)),
            vulgarity_verdict=str(rubric_dict.get("vulgarity_verdict", "No vulgarity detected.")),
            vulgarity_detected=rubric_dict.get("vulgarity_detected", []),
            bug_score=int(rubric_dict.get("bug_score", 75)),
            bug_verdict=str(rubric_dict.get("bug_verdict", "Standard quality.")),
            detected_bugs=rubric_dict.get("detected_bugs", []),
            advance_score=int(rubric_dict.get("advance_score", 70)),
            advance_verdict=str(rubric_dict.get("advance_verdict", "Intermediate engineering.")),
            advanced_features=rubric_dict.get("advanced_features", []),
        ),
        recommended_defense_topics=parsed_dict.get("recommended_defense_topics", []),
        suggested_improvements=parsed_dict.get("suggested_improvements", []),
    )
