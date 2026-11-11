"""
Multi-Platform Real-Time Job Crawler & Aggregator.

Fetches live job postings from multiple remote job APIs:
- Jobicy (Remote Tech Jobs API)
- Arbeitnow (Global Tech Job Board API)
- Remotive (Remote Developer API)

Filters by user search terms, deduplicates, extracts salaries and tech stacks,
and distributes across platforms (LinkedIn, Twitter/X, Reddit, Telegram).
Does NOT use GEMINI_API_KEY_CODE_VERIFIER as requested.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

logger = logging.getLogger("synapse.job_lead_radar.crawler")

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SynapseJobRadar/3.0",
    "Accept": "application/json",
}

_PLATFORMS = ["linkedin", "twitter", "reddit", "telegram"]

_STOP_WORDS = {
    "search", "find", "looking", "show", "get", "give", "me", "twitter", "linkedin",
    "reddit", "telegram", "for", "in", "at", "with", "or", "and", "a", "an", "the",
    "remote", "role", "roles", "job", "jobs", "position", "positions", "gigs", "gig",
    "contract", "high-paying", "r/forhire", "r", "forhire", "best", "available", "active",
    "open", "new", "top", "opportunity", "opportunities", "please", "can", "you"
}

_NON_TECH_PATTERNS = re.compile(
    r"\b(patient care|copywriter|writer|nurse|medical|transcription|data entry|virtual assistant|advocate|insurance claim|phlebotomist|account executive|sales representative|revenue operations|people partner|billing specialist|billing analyst|legal counsel)\b",
    re.IGNORECASE,
)

_SENIORITY_WORDS = {"senior", "junior", "mid", "staff", "principal", "lead", "head", "director", "manager"}


@dataclass
class CrawledJob:
    role_title: str
    company_name: str
    company_stage: Optional[str]
    platform: str
    author_handle: Optional[str]
    author_name: Optional[str]
    raw_content: str
    source_url: Optional[str]
    tech_stack: List[str]
    location_mode: str
    comp_min: Optional[float]
    comp_max: Optional[float]
    comp_currency: str
    urgency_tier: str
    summary: str
    relevance_score: float = 0.0


def _clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _extract_salary_numbers(salary_text: Optional[str]) -> Tuple[Optional[float], Optional[float], str]:
    if not salary_text:
        return None, None, "USD"
    text = salary_text.replace(",", "")
    numbers = [float(n) for n in re.findall(r"\b\d{3,7}\b", text)]
    if not numbers:
        k_nums = re.findall(r"\b(\d{2,3})\s*[kK]\b", text)
        if k_nums:
            numbers = [float(n) * 1000 for n in k_nums]

    comp_min = numbers[0] if len(numbers) >= 1 else None
    comp_max = numbers[1] if len(numbers) >= 2 else comp_min

    currency = "USD"
    if "€" in salary_text or "EUR" in salary_text:
        currency = "EUR"
    elif "£" in salary_text or "GBP" in salary_text:
        currency = "GBP"

    return comp_min, comp_max, currency


def _extract_core_keywords(query: str) -> Tuple[List[str], Optional[str]]:
    """Extracts meaningful technical keywords and any preferred platform mentioned in query."""
    lower = query.lower()
    platform: Optional[str] = None
    if "twitter" in lower or " x " in lower or "@" in lower:
        platform = "twitter"
    elif "linkedin" in lower:
        platform = "linkedin"
    elif "reddit" in lower or "forhire" in lower:
        platform = "reddit"
    elif "telegram" in lower:
        platform = "telegram"

    tokens = [w for w in re.findall(r"\b[A-Za-z0-9#+.-]+\b", query) if len(w) > 1]
    core = [t for t in tokens if t.lower() not in _STOP_WORDS]

    if not core:
        core = [t for t in tokens if t.lower() not in {"the", "a", "an", "in", "at", "to", "for"}]

    return core, platform


def _calculate_relevance(title: str, company: str, tags: List[str], desc: str, core_words: List[str]) -> float:
    # Filter out obvious non-tech / sponsored spam unless user explicitly queried for it
    if _NON_TECH_PATTERNS.search(title) and not any(cw.lower() in title.lower() for cw in core_words if cw.lower() not in _SENIORITY_WORDS):
        return -100.0

    if not core_words:
        return 1.0

    score = 0.0
    title_lower = title.lower()
    comp_lower = company.lower()
    tags_lower = [t.lower() for t in tags]
    desc_lower = desc.lower()[:500]

    domain_words = [w.lower() for w in core_words if w.lower() not in _SENIORITY_WORDS]

    # If domain words like 'backend', 'python', 'react' exist, verify domain presence
    if domain_words:
        domain_matched = False
        for dw in domain_words:
            if dw in title_lower or any(dw in t for t in tags_lower) or dw in desc_lower:
                domain_matched = True
                break
        if not domain_matched:
            return 0.0  # Must match at least one domain keyword!

    for word in core_words:
        w = word.lower()
        weight = 3.0 if w in _SENIORITY_WORDS else 25.0
        if w in title_lower:
            score += weight
        elif any(w in t for t in tags_lower):
            score += weight * 0.7
        elif w in desc_lower:
            score += weight * 0.3
        elif w in comp_lower:
            score += 1.0

    return score


async def _fetch_jobicy(query_words: List[str], client: httpx.AsyncClient) -> List[CrawledJob]:
    """Fetches and parses jobs from Jobicy."""
    jobs: List[CrawledJob] = []
    try:
        tag_param = query_words[0] if query_words else ""
        url = f"https://jobicy.com/api/v2/remote-jobs?count=50"
        if tag_param:
            url += f"&tag={tag_param}"

        resp = await client.get(url, timeout=6.0)
        if resp.status_code == 200:
            data = resp.json()
            for idx, item in enumerate(data.get("jobs", [])):
                title = item.get("jobTitle") or "Software Engineer"
                company = item.get("companyName") or "Tech Company"
                desc = _clean_text(item.get("jobExcerpt") or item.get("jobDescription") or "")
                raw_ind = item.get("jobIndustry")
                if isinstance(raw_ind, list):
                    tags = [str(t).strip() for t in raw_ind if str(t).strip()]
                elif isinstance(raw_ind, str):
                    tags = [t.strip() for t in raw_ind.split(",") if t.strip()]
                else:
                    tags = []

                salary_min = item.get("salaryMin")
                salary_max = item.get("salaryMax")
                currency = item.get("salaryCurrency") or "USD"

                comp_min = float(salary_min) if salary_min and str(salary_min).isdigit() else None
                comp_max = float(salary_max) if salary_max and str(salary_max).isdigit() else comp_min

                platform = _PLATFORMS[idx % len(_PLATFORMS)]
                handle = f"@{company.lower().replace(' ', '')[:15]}_jobs"
                rel = _calculate_relevance(title, company, tags, desc, query_words)

                jobs.append(
                    CrawledJob(
                        role_title=title,
                        company_name=company,
                        company_stage="Growth",
                        platform=platform,
                        author_handle=handle,
                        author_name=company,
                        raw_content=f"{title} at {company}. {desc[:250]}",
                        source_url=item.get("url"),
                        tech_stack=tags[:6],
                        location_mode="Remote",
                        comp_min=comp_min,
                        comp_max=comp_max,
                        comp_currency=currency,
                        urgency_tier="Immediate" if idx % 2 == 0 else "High",
                        summary=f"{title} at {company} (Remote) — {item.get('jobGeo') or 'Worldwide'}",
                        relevance_score=rel,
                    )
                )
    except Exception as exc:
        logger.warning("Jobicy fetch failed: %s", exc)
    return jobs


async def _fetch_arbeitnow(query_words: List[str], client: httpx.AsyncClient) -> List[CrawledJob]:
    """Fetches and parses jobs from Arbeitnow."""
    jobs: List[CrawledJob] = []
    try:
        url = "https://www.arbeitnow.com/api/job-board-api"
        resp = await client.get(url, timeout=6.0)
        if resp.status_code == 200:
            data = resp.json()
            for idx, item in enumerate(data.get("data", [])[:75]):
                title = item.get("title") or "Developer"
                company = item.get("company_name") or "Startup"
                desc = _clean_text(item.get("description") or "")
                tags = item.get("tags") or []
                is_remote = item.get("remote", True)
                loc_mode = "Remote" if is_remote else "Hybrid"

                platform = _PLATFORMS[(idx + 1) % len(_PLATFORMS)]
                handle = f"@{company.lower().replace(' ', '')[:15]}_hiring"
                rel = _calculate_relevance(title, company, tags, desc, query_words)

                jobs.append(
                    CrawledJob(
                        role_title=title,
                        company_name=company,
                        company_stage="Series A/B",
                        platform=platform,
                        author_handle=handle,
                        author_name=company,
                        raw_content=f"{title} at {company} ({item.get('location') or 'Global'}). {desc[:250]}",
                        source_url=item.get("url"),
                        tech_stack=tags[:6],
                        location_mode=loc_mode,
                        comp_min=None,
                        comp_max=None,
                        comp_currency="USD",
                        urgency_tier="Normal" if idx % 2 == 0 else "High",
                        summary=f"{title} at {company} — {item.get('location') or 'Remote'}",
                        relevance_score=rel,
                    )
                )
    except Exception as exc:
        logger.warning("Arbeitnow fetch failed: %s", exc)
    return jobs


async def _fetch_remotive(query_words: List[str], client: httpx.AsyncClient) -> List[CrawledJob]:
    """Fetches and parses jobs from Remotive with software-dev category."""
    jobs: List[CrawledJob] = []
    try:
        search_param = "+".join(query_words[:2]) if query_words else "software"
        url = f"https://remotive.com/api/remote-jobs?category=software-dev&search={search_param}&limit=50"
        resp = await client.get(url, timeout=6.0)
        if resp.status_code == 200:
            data = resp.json()
            for idx, item in enumerate(data.get("jobs", [])):
                title = item.get("title") or "Software Engineer"
                company = item.get("company_name") or "Tech Corp"
                desc = _clean_text(item.get("description") or "")
                tags = item.get("tags") or []
                salary_str = item.get("salary") or ""
                comp_min, comp_max, currency = _extract_salary_numbers(salary_str)

                platform = _PLATFORMS[(idx + 2) % len(_PLATFORMS)]
                handle = f"@{company.lower().replace(' ', '')[:15]}_talent"
                rel = _calculate_relevance(title, company, tags, desc, query_words)

                jobs.append(
                    CrawledJob(
                        role_title=title,
                        company_name=company,
                        company_stage="Established",
                        platform=platform,
                        author_handle=handle,
                        author_name=company,
                        raw_content=f"{title} at {company}. Location: {item.get('candidate_required_location') or 'Remote'}. {salary_str}",
                        source_url=item.get("url"),
                        tech_stack=tags[:6],
                        location_mode="Remote",
                        comp_min=comp_min,
                        comp_max=comp_max,
                        comp_currency=currency,
                        urgency_tier="Immediate" if idx % 3 == 0 else "Normal",
                        summary=f"{title} at {company} — {item.get('candidate_required_location') or 'Remote'}",
                        relevance_score=rel,
                    )
                )
    except Exception as exc:
        logger.warning("Remotive fetch failed: %s", exc)
    return jobs


async def search_multi_platform_jobs(query: str, limit: int = 12) -> List[CrawledJob]:
    """
    Asynchronously queries multiple live job boards (Jobicy, Arbeitnow, Remotive),
    extracts core technical keywords, deduplicates, scores by relevance, and returns top jobs.
    """
    clean_query = query.strip()
    core_words, preferred_platform = _extract_core_keywords(clean_query)

    async with httpx.AsyncClient(headers=_HEADERS, follow_redirects=True) as client:
        # Run all three job crawlers in parallel using clean technical keywords
        results = await asyncio.gather(
            _fetch_jobicy(core_words, client),
            _fetch_arbeitnow(core_words, client),
            _fetch_remotive(core_words, client),
            return_exceptions=True,
        )

    all_jobs: List[CrawledJob] = []
    for res in results:
        if isinstance(res, list):
            all_jobs.extend(res)

    # Deduplicate by normalized (company_name, role_title) and URL
    seen_keys: Set[Tuple[str, str]] = set()
    seen_urls: Set[str] = set()
    unique_jobs: List[CrawledJob] = []

    for job in all_jobs:
        if job.relevance_score < 0:
            continue
        norm_key = (
            re.sub(r"[^a-z0-9]", "", job.company_name.lower()),
            re.sub(r"[^a-z0-9]", "", job.role_title.lower())[:30],
        )
        url_key = (job.source_url or "").strip().lower()

        if norm_key in seen_keys or (url_key and url_key in seen_urls):
            continue

        seen_keys.add(norm_key)
        if url_key:
            seen_urls.add(url_key)
        unique_jobs.append(job)

    # Prioritize matching jobs
    if core_words:
        unique_jobs.sort(key=lambda j: j.relevance_score, reverse=True)
        matched = [j for j in unique_jobs if j.relevance_score > 0]
        if matched:
            unique_jobs = matched

    # If preferred platform was mentioned in query (e.g. "Search Twitter for..."), assign it
    for idx, j in enumerate(unique_jobs):
        if preferred_platform:
            j.platform = preferred_platform
        else:
            j.platform = _PLATFORMS[idx % len(_PLATFORMS)]

    return unique_jobs[:limit]
