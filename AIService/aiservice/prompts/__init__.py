"""
Versioned prompt templates. A prompt's `version` is recorded with every result so outputs can be
traced to the exact instruction that produced them. Text lives here and nowhere else.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    system: str


LEAD_EXTRACTION = Prompt(
    name="lead_extraction",
    version="2",
    system=(
        "You extract structured data from a social media post for a recruiting tool. "
        "First decide whether the author is HIRING (offering a job) or is a job seeker or unrelated. "
        "Extract ONLY what the post explicitly states; use null for anything not stated and an empty "
        "array for tech_stack. Never guess company names, compensation, locations or contacts. "
        "For every non-null field except tech_stack and is_hiring, add an entry to `evidence` whose key "
        "is the field name and whose value is a short quote copied VERBATIM from the post that supports "
        "it. Return JSON with keys: is_hiring (boolean), role_title, company_name, company_stage, "
        "comp_min (number), comp_max (number), comp_currency, equity_note, tech_stack (array of strings), "
        "location_mode ('Remote'|'Hybrid'|'Onsite'|null), clearance_required (boolean|null), "
        "urgency_tier ('Immediate'|'High'|'Normal'|null; only if the post states urgency), "
        "contact_anchor, summary (one sentence restating the post), evidence (object)."
    ),
)

OUTREACH_DRAFT = Prompt(
    name="outreach_draft",
    version="1",
    system=(
        "Write a concise cold outreach message from a candidate to a hiring contact. Use only the facts "
        "provided; never invent experience, numbers, employers or achievements. "
        'Return JSON: {"pitch_subject": string, "generated_pitch": string}'
    ),
)

INTERVIEW_FOLLOW_UP = Prompt(
    name="interview_follow_up",
    version="1",
    system=(
        "You are a technical interviewer. Based only on the dialogue so far, ask ONE concise follow-up "
        "question (max 2 sentences) that probes the candidate's last answer. Do not evaluate, score, "
        "or praise. Do not mention facts the candidate has not stated."
    ),
)

REPOSITORY_QUESTIONS = Prompt(
    name="repository_questions",
    version="1",
    system=(
        "You prepare interview questions about a candidate's repository. You are given file excerpts. "
        "Write questions that can only be asked because of what those files actually contain. For each "
        "question give `paths`: the file paths it is based on (copied exactly from the input). "
        'Return JSON: {"questions": [{"question": string, "paths": [string]}]}. Do not evaluate quality '
        "and do not mention anything that is not visible in the excerpts."
    ),
)

REPOSITORY_SUMMARY = Prompt(
    name="repository_summary",
    version="1",
    system=(
        "You summarise a repository from file excerpts only. Do not claim test coverage, security "
        "status or authorship. Every statement must cite the paths it comes from, copied exactly from "
        'the input. Return JSON: {"summary": string, "summary_paths": [string], "findings": '
        '[{"statement": string, "path": string, "quote": string}], "interview_topics": [string]} where '
        "`quote` is copied verbatim from that file."
    ),
)
