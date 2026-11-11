"""
Adapters from module-owned AI ports to AIService (composition root only).

Each adapter translates between a module's small domain dataclasses and AIService's result types.
Neither side imports the other: modules know ports, AIService knows nothing of modules.
"""

import json
import logging
from typing import Callable, Dict, List, Optional, Tuple

from aiservice import (
    CodeIntelligence,
    InterviewIntelligence,
    LeadIntelligence,
    LLMProvider,
    OutreachRequest,
    Turn,
    prepare_evidence,
)

from app.modules import code_verifier, job_lead_radar, voice_defense

ProviderFactory = Callable[[], LLMProvider]
logger = logging.getLogger("synapse.ai_adapters")


class AIServiceLeadAnalyzer:
    def __init__(self, provider: ProviderFactory) -> None:
        self._provider = provider

    async def analyze_post(self, text: str, platform: str) -> job_lead_radar.PostAnalysis:
        r = await LeadIntelligence(self._provider()).analyze_post(text, platform)
        f = r.fields
        return job_lead_radar.PostAnalysis(
            status=r.status, reason=r.reason, is_hiring=r.is_hiring,
            role_title=f.role_title, company_name=f.company_name, company_stage=f.company_stage,
            comp_min=f.comp_min, comp_max=f.comp_max, comp_currency=f.comp_currency, equity_note=f.equity_note,
            tech_stack=list(f.tech_stack), location_mode=f.location_mode, clearance_required=f.clearance_required,
            urgency_tier=f.urgency_tier, contact_anchor=f.contact_anchor, summary=f.summary,
            evidence=dict(r.evidence), dropped_fields=list(r.dropped_fields),
            model=r.model, prompt_version=r.prompt_version,
        )


class AIServiceOutreachDrafter:
    def __init__(self, provider: ProviderFactory) -> None:
        self._provider = provider

    async def draft(
        self, *, role_title: str, company_name: str, tone: str, tech_stack: List[str],
        comp_min: Optional[float], comp_max: Optional[float], comp_currency: Optional[str],
        candidate_background: Optional[str],
    ) -> job_lead_radar.OutreachDraftResult:
        r = await LeadIntelligence(self._provider()).draft_outreach(
            OutreachRequest(
                role_title=role_title, company_name=company_name, tone=tone, tech_stack=tech_stack,
                comp_min=comp_min, comp_max=comp_max, comp_currency=comp_currency,
                candidate_background=candidate_background,
            )
        )
        return job_lead_radar.OutreachDraftResult(
            status=r.status, reason=r.reason, subject=r.subject, pitch=r.pitch, model=r.model,
            prompt_tokens=r.usage.prompt_tokens, completion_tokens=r.usage.completion_tokens,
        )


def analyze_candidate_quality(turns: List[Dict[str, str]]) -> Tuple[bool, int, str]:
    """
    Evaluates candidate responses to determine if they are answering on-topic with genuine technical depth.
    Returns:
        (is_good: bool, target_questions: int, reason: str)
        - If struggling / off-topic / rubbish: is_good=False, target_questions=7 or 8.
        - If good technical answers: is_good=True, target_questions=12 (10-13 questions).
    """
    cand_turns = [
        str(t.get("text", "")).strip()
        for t in turns
        if t.get("speaker") == "candidate" and str(t.get("text", "")).strip()
    ]
    if not cand_turns:
        return True, 12, "Interview starting"

    tech_lexicon = {
        "architecture", "backend", "frontend", "fullstack", "database", "sql", "nosql",
        "postgres", "postgresql", "mysql", "sqlite", "mongodb", "redis", "api", "rest",
        "graphql", "grpc", "websocket", "endpoint", "controller", "service", "model",
        "schema", "migration", "orm", "async", "await", "promise", "thread", "concurrency",
        "lock", "mutex", "queue", "kafka", "rabbitmq", "event", "microservice", "monolith",
        "docker", "kubernetes", "ci", "cd", "pipeline", "test", "testing", "unit",
        "integration", "e2e", "pytest", "jest", "mock", "stub", "latency", "throughput",
        "caching", "cache", "ttl", "invalidation", "scale", "scaling", "load", "balancer",
        "replica", "sharding", "partition", "index", "indexing", "tradeoff", "benchmark",
        "security", "auth", "authentication", "authorization", "jwt", "oauth", "token",
        "session", "encryption", "rate", "limit", "circuit", "breaker", "retry", "backoff",
        "idempotent", "idempotency", "transaction", "acid", "consistency", "git", "github",
        "commit", "branch", "pr", "component", "state", "props", "redux", "context",
        "fastapi", "django", "flask", "express", "react", "vue", "node", "python",
        "typescript", "javascript", "golang", "rust", "java", "performance", "memory",
        "garbage", "profiling", "observability", "metrics", "prometheus", "grafana",
        "logging", "tracing", "distributed", "system", "payload", "serialization"
    }

    rubbish_indicators = [
        "rubbish", "nonsense", "gibberish", "blah", "idk", "don't know", "dont know",
        "no idea", "asdf", "qwerty", "whatever", "skip", "pass", "random", "joke",
        "next question", "don't care", "dont care", "who cares", "not interested"
    ]

    total_turns = len(cand_turns)
    good_turns = 0.0
    weak_turns = 0.0
    all_text = " ".join(cand_turns).lower()

    for turn_txt in cand_turns:
        txt_lower = turn_txt.lower()
        words = txt_lower.split()
        word_count = len(words)

        has_rubbish = any(r in txt_lower for r in rubbish_indicators)
        tech_words_in_turn = sum(1 for term in tech_lexicon if term in txt_lower)

        is_just_doubt = (
            ("?" in turn_txt or "clarify" in txt_lower or "doubt" in txt_lower)
            and word_count < 20
            and tech_words_in_turn == 0
        )
        if is_just_doubt:
            continue

        if has_rubbish or (word_count < 12 and tech_words_in_turn == 0):
            weak_turns += 1.0
        elif tech_words_in_turn >= 2 and word_count >= 15:
            good_turns += 1.0
        elif tech_words_in_turn >= 1:
            good_turns += 0.5
        else:
            weak_turns += 0.5

    all_tech_terms_found = len([t for t in tech_lexicon if t in all_text])

    if total_turns >= 2:
        if weak_turns > good_turns or all_tech_terms_found < 3:
            return False, 8, f"Struggling candidate: {weak_turns} weak turns vs {good_turns} solid turns, {all_tech_terms_found} technical concepts"
        else:
            return True, 12, f"Good candidate: {good_turns} solid turns, {all_tech_terms_found} technical concepts"

    return True, 12, "Early interview turn"


GOOD_CANDIDATE_STAGES = [
    ("intro", "skills", lambda name, repo: f"Thank you, {name}. Based on your background, what core programming languages, runtimes, and engineering principles do you specialize in when building production software?"),
    ("skills", "project_defense", lambda name, repo: f"Now let's examine your submitted project ({repo}). Walk me through its high-level architecture, how major components interact, and why you made those design choices."),
    ("project_defense", "data_modeling", lambda name, repo: f"Regarding the data layer in {repo}, how did you design the schema, handle indexing and queries, and balance normalization versus read performance?"),
    ("data_modeling", "api_design", lambda name, repo: f"Let's look at your API design in {repo}. What protocols and serialization did you use, and how do you ensure API contracts, idempotency, and status codes are strictly maintained?"),
    ("api_design", "concurrency", lambda name, repo: f"In {repo}, how do you handle concurrency, asynchronous execution, race conditions, or background tasks without causing deadlocks or state inconsistencies?"),
    ("concurrency", "caching", lambda name, repo: f"How do you approach caching in {repo}? What is your cache invalidation strategy, TTL configuration, and how do you prevent cache stampedes or stale data?"),
    ("caching", "scalability", lambda name, repo: f"If traffic to {repo} spiked tenfold overnight, where would the primary bottlenecks emerge, and how would you scale the services and database horizontally?"),
    ("scalability", "resilience", lambda name, repo: f"Tell me about resilience and fault tolerance in {repo}. How do you handle downstream timeouts, retries with backoff, circuit breakers, and graceful degradation?"),
    ("resilience", "security", lambda name, repo: f"What security controls and OWASP defenses did you implement in {repo}, specifically around authentication, token validation, and input sanitization?"),
    ("security", "testing_ci_cd", lambda name, repo: f"Walk me through your automated testing strategy for {repo}. What is your coverage across unit, integration, and end-to-end tests, and how is it enforced in CI/CD?"),
    ("testing_ci_cd", "tradeoffs", lambda name, repo: f"What was the most difficult architectural tradeoff or production bug you had to solve in {repo}, and why did you choose that approach over the alternatives?"),
    ("tradeoffs", "observability", lambda name, repo: f"Finally, how do you monitor {repo} in production? What key metrics, logs, distributed traces, and alerting rules would tell you the system is unhealthy?"),
    ("observability", "ready_for_eval", lambda name, repo: f"Excellent defense, {name}. We have thoroughly covered the architectural, operational, and system design aspects of your project.")
]

STRUGGLING_CANDIDATE_STAGES = [
    ("intro", "skills", lambda name, repo: f"Thank you, {name}. To start, could you tell me about the programming languages and tools you feel most comfortable working with day-to-day?"),
    ("skills", "project_overview", lambda name, repo: f"Looking at your submitted project ({repo}), what core problem does it solve and what are the main features you built?"),
    ("project_overview", "data_flow", lambda name, repo: f"Can you explain the basic flow of a request in {repo}, from when a user interacts with the app to how the server processes it?"),
    ("data_flow", "data_storage", lambda name, repo: f"What kind of database or storage did you use in {repo}, and what main tables or data entities did you create?"),
    ("data_storage", "error_handling", lambda name, repo: f"When something goes wrong in {repo}, how does your code handle errors or invalid inputs, and how did you debug issues?"),
    ("error_handling", "testing_verification", lambda name, repo: f"How did you test or verify that your project ({repo}) was working properly before considering it complete?"),
    ("testing_verification", "reflection", lambda name, repo: f"Looking back at {repo}, what was the most challenging part for you, and what is one thing you would do differently?"),
    ("reflection", "ready_for_eval", lambda name, repo: f"Thank you, {name}. That covers the key areas of our technical interview.")
]


class AIServiceInterviewer:
    def __init__(self, provider: ProviderFactory) -> None:
        self._provider = provider

    async def follow_up(
        self,
        turns: List[Dict[str, str]],
        *,
        candidate_name: Optional[str] = None,
        resume_text: Optional[str] = None,
        repo_name: Optional[str] = None,
        turn_index: Optional[int] = None,
        current_stage: Optional[str] = None,
    ) -> voice_defense.FollowUpQuestion:
        provider = self._provider()
        name = candidate_name or "Candidate"
        repo = repo_name or "the submitted repository"
        stage = current_stage or "intro"
        cand_turn = turn_index if turn_index is not None else sum(1 for t in turns if t.get("speaker") == "candidate")

        last_cand_text = ""
        for t in reversed(turns):
            if t.get("speaker") == "candidate":
                last_cand_text = str(t.get("text", "")).strip()
                break

        # Check for candidate doubts, questions, or clarification requests
        doubt_keywords = [
            "?", "doubt", "question", "clarify", "clarification", "what do you mean",
            "could you explain", "can you explain", "can i ask", "could i ask", "can i explain",
            "should i focus", "what does", "how does", "why does", "what should i",
            "not clear", "confused", "repeat the question", "pardon"
        ]
        text_lower = last_cand_text.lower()
        has_doubt_heuristic = any(k in text_lower for k in doubt_keywords)

        # Baseline heuristic quality check
        heuristic_is_good, heuristic_target, heuristic_reason = analyze_candidate_quality(turns)

        if not provider.is_configured():
            return voice_defense.FollowUpQuestion(status="unavailable", question=None)

        try:
            dialogue = "\n".join(
                f"{'Interviewer' if t.get('speaker') == 'ai_interviewer' else name}: {t.get('text', '')}"
                for t in turns[-8:]
            )

            prompt = (
                f"You are conducting a live, voice-interactive technical defense interview with candidate {name}.\n\n"
                f"CONTEXT:\n"
                f"- Candidate Name: {name}\n"
                f"- Resume / Background: {resume_text or 'Not provided'}\n"
                f"- Submitted Project / Repository: {repo}\n"
                f"- Current Candidate Turn Number: {cand_turn}\n"
                f"- Current Stage: {stage}\n\n"
                f"RECENT INTERVIEW DIALOGUE:\n"
                f"{dialogue}\n\n"
                f"LATEST MESSAGE FROM CANDIDATE:\n"
                f"\"{last_cand_text}\"\n\n"
                f"INSTRUCTIONS FOR YOUR RESPONSE:\n"
                f"1. CANDIDATE DOUBTS & CLARIFICATION REQUESTS:\n"
                f"   Check if {name} asked a question, expressed doubt, or asked for clarification (e.g. asking what you mean, asking about expectations, asking if they can explain X first).\n"
                f"   - If YES:\n"
                f"     * Directly and warmly answer their question/doubt first (1-2 clear, helpful sentences).\n"
                f"     * If they have not answered the current topic yet, encourage them to answer.\n"
                f"     * Set is_doubt: true, stage_advance: false, next_stage: '{stage}'.\n"
                f"2. EVALUATE CANDIDATE PERFORMANCE & QUALITY:\n"
                f"   - Classify candidate as 'good' vs 'struggling':\n"
                f"     * 'struggling': Candidate gives off-topic, evasive, very short/vague answers, gibberish/refusals, or cannot explain concepts.\n"
                f"       Target: Ask a total of 7 to 8 questions covering accessible, foundational topics. When reaching turn 7 or 8, set next_stage to 'ready_for_eval'.\n"
                f"     * 'good': Candidate answers topics on-topic with genuine technical depth, clear software engineering concepts, and architectural reasoning.\n"
                f"       Target: Ask a total of 10 to 13 questions deeply probing their architecture, data modeling, APIs, concurrency, caching, scaling, resilience, security, testing, and tradeoffs. When reaching turn 11 to 13, set next_stage to 'ready_for_eval'.\n"
                f"3. CRAFT NEXT QUESTION OR EVALUATION TRANSITION:\n"
                f"   - If not a pure doubt, acknowledge their answer naturally and ask ONE focused follow-up question appropriate for their current level and stage.\n"
                f"   - Set stage_advance: true.\n"
                f"   - Style: Keep spoken response concise (2-4 sentences total), friendly and natural for Voice TTS. No markdown symbols or bullet points.\n\n"
                f"Return JSON strictly matching this schema:\n"
                f"{{\n"
                f'  "is_doubt": boolean,\n'
                f'  "answer_to_doubt": string or null,\n'
                f'  "candidate_quality": "good" | "struggling",\n'
                f'  "candidate_quality_reason": string,\n'
                f'  "target_total_questions": number (7 or 8 for struggling, 10 to 13 for good),\n'
                f'  "interviewer_reply": string,\n'
                f'  "stage_advance": boolean,\n'
                f'  "next_stage": string\n'
                f"}}"
            )

            gen = await provider.generate_json(
                prompt=prompt,
                system="You are an expert, empathetic human technical interviewer. Return JSON only.",
                temperature=0.3,
            )
            try:
                data = json.loads(gen.text)
                reply = str(data.get("interviewer_reply") or "").strip()
                is_doubt = bool(data.get("is_doubt", False))
                advance = bool(data.get("stage_advance", not is_doubt))
                next_stage = str(data.get("next_stage") or stage).strip()
                cand_quality = str(data.get("candidate_quality", "")).lower()
                if cand_quality == "struggling":
                    is_good_cand = False
                    target_q = 8
                elif cand_quality == "good":
                    is_good_cand = True
                    target_q = 12
                else:
                    is_good_cand = heuristic_is_good
                    target_q = heuristic_target
            except Exception:
                reply = gen.text.strip()
                is_doubt = False
                advance = True
                next_stage = stage
                is_good_cand = heuristic_is_good
                target_q = heuristic_target

            if reply:
                return voice_defense.FollowUpQuestion(
                    status="generated",
                    question=reply,
                    stage=next_stage if advance else stage,
                    is_doubt_or_question=is_doubt,
                    advance_stage=advance,
                    next_stage=next_stage,
                    is_good_candidate=is_good_cand,
                    target_questions=target_q,
                )
            return voice_defense.FollowUpQuestion(status="unavailable", question=None)
        except Exception as exc:
            logger.warning("Voice defense turn failed: %s; using intelligent fallback.", exc)

        # Fallback when AI generation is rate-limited, quota-exhausted, or temporarily unavailable
        if has_doubt_heuristic:
            clarifications = {
                "intro": f"No problem at all, {name}! You can highlight any areas of your experience you're most comfortable with, whether backend, frontend, or infrastructure. Whenever you're ready, please walk me through your background.",
                "skills": f"Great question! We're focusing on the technical tools and technologies you use day-to-day. How do you apply those in real projects?",
                "project_defense": f"Good question! By architecture, I mean how your services, API, and database communicate and why you structured them that way in {repo}. Whenever you're ready, walk me through that structure.",
                "data_modeling": f"We're looking at your data storage choices, schema relationships, and indexing decisions in {repo}. Whenever you're ready, tell me about that structure.",
                "api_design": f"I'm referring to how clients communicate with your server in {repo}, such as endpoint conventions, status codes, and payload contracts.",
                "concurrency": f"I mean how your application prevents race conditions, handles background tasks, or manages multiple simultaneous users safely.",
                "caching": f"We're exploring whether you cache frequently accessed data, how you expire it, and how you keep it fresh.",
                "scalability": f"Imagine your user base multiplied by ten overnight—which component in {repo} would slow down first, and how would you adapt?",
                "resilience": f"We're interested in how your application recovers from external service failures, network drops, or unhandled exceptions.",
                "security": f"We're focusing on how you protect user credentials, secure endpoints, and sanitize inputs in {repo}.",
                "testing_ci_cd": f"Tell me about how you verify code correctness, whether unit tests, integration tests, or automated workflows.",
                "tradeoffs": f"Every architecture involves compromises—like speed versus complexity, or flexibility versus strict schemas. What compromises did you make in {repo}?",
                "observability": f"We want to know what alerts, log aggregation, or health checks you use to verify {repo} is performing reliably in production.",
            }
            clarification_reply = clarifications.get(stage, f"Of course, {name}! Take your time to explain your technical reasoning and design decisions whenever you're ready.")
            return voice_defense.FollowUpQuestion(
                status="generated",
                question=clarification_reply,
                stage=stage,
                is_doubt_or_question=True,
                advance_stage=False,
                next_stage=stage,
                is_good_candidate=heuristic_is_good,
                target_questions=heuristic_target,
            )

        # Pick appropriate stage list based on candidate quality
        stages_list = GOOD_CANDIDATE_STAGES if heuristic_is_good else STRUGGLING_CANDIDATE_STAGES
        idx = min(cand_turn - 1, len(stages_list) - 1)
        if idx < 0:
            idx = 0

        curr_def, next_stg, q_factory = stages_list[idx]
        q_text = q_factory(name, repo)

        return voice_defense.FollowUpQuestion(
            status="generated",
            question=q_text,
            stage=next_stg,
            is_doubt_or_question=False,
            advance_stage=True,
            next_stage=next_stg,
            is_good_candidate=heuristic_is_good,
            target_questions=heuristic_target,
        )

    async def evaluate_interview(
        self,
        turns: List[Dict[str, str]],
        *,
        candidate_name: Optional[str] = None,
        resume_text: Optional[str] = None,
        repo_name: Optional[str] = None,
    ) -> voice_defense.InterviewEvaluation:
        import json
        provider = self._provider()
        name = candidate_name or "Candidate"
        repo = repo_name or "the submitted repository"
        dialogue = "\n".join(f"{'Interviewer' if t.get('speaker') == 'ai_interviewer' else name}: {t.get('text', '')}" for t in turns)

        if provider.is_configured():
            try:
                prompt = (
                    f"You are a rigorous, highly discerning Senior Principal Engineer evaluating candidate {name} on their live technical interview defense.\n\n"
                    f"CANDIDATE INFO:\n"
                    f"- Candidate Name: {name}\n"
                    f"- Target Project: {repo}\n"
                    f"- Resume / Background: {resume_text or 'Not provided'}\n\n"
                    f"INTERVIEW TRANSCRIPT:\n"
                    f"{dialogue}\n\n"
                    f"EVALUATION CRITERIA & STRICT RUBRIC (Scale 1.0 to 10.0):\n"
                    f"- 1.0 - 2.5 (Rubbish / Non-Answer / Nonsense / Gibberish / Refusal): The candidate gave nonsense, random letters, sarcastic jokes, filler phrases, off-topic ramblings, or refused to answer technical questions. ZERO technical competency demonstrated.\n"
                    f"- 2.6 - 4.5 (Weak / Unqualified): Answers are largely inaccurate, superficial, or confused about basic concepts (cannot explain basic components or stack).\n"
                    f"- 4.6 - 6.5 (Mediocre / Junior): Basic textbook definitions, but cannot explain their actual architecture, lacks concrete reasoning for tradeoffs, or struggles on deep-dives.\n"
                    f"- 6.6 - 8.0 (Solid / Competent): Clear technical explanations, sound architectural choices, good communication, addresses most edge cases.\n"
                    f"- 8.1 - 10.0 (Exceptional / Principal): Deep mastery of concurrency, distributed systems, precise performance benchmarks, clear articulation of complex tradeoffs.\n\n"
                    f"CRITICAL INSTRUCTIONS:\n"
                    f"- Carefully examine what {name} ACTUALLY said in response to each interviewer question.\n"
                    f"- If the candidate spoke rubbish, spam, filler, jokes, or non-technical answers, YOU MUST SCORE THEM STRICTLY BETWEEN 1.0 AND 2.5.\n"
                    f"- Be completely honest and accurate in your summary, strengths, and areas for improvement. If the candidate gave poor or nonsense answers, explicitly state that in the summary and improvements.\n\n"
                    f"Return JSON strictly matching this schema:\n"
                    f"{{\n"
                    f'  "overall_score": float (1.0 to 10.0),\n'
                    f'  "technical_depth_score": float (1.0 to 10.0),\n'
                    f'  "clarity_articulation_score": float (1.0 to 10.0),\n'
                    f'  "project_defense_score": float (1.0 to 10.0),\n'
                    f'  "summary": string,\n'
                    f'  "key_strengths": array of string,\n'
                    f'  "areas_for_improvement": array of string\n'
                    f"}}"
                )
                gen = await provider.generate_json(
                    prompt=prompt,
                    system="You are a rigorous, honest, and objective technical evaluator. Never inflate scores for poor or rubbish answers. Output valid JSON only.",
                    temperature=0.1,
                )
                data = json.loads(gen.text)
                overall = max(1.0, min(10.0, float(data.get("overall_score", 1.0))))
                tech = max(1.0, min(10.0, float(data.get("technical_depth_score", overall))))
                clarity = max(1.0, min(10.0, float(data.get("clarity_articulation_score", overall))))
                proj = max(1.0, min(10.0, float(data.get("project_defense_score", overall))))
                summary = str(data.get("summary") or "").strip()
                if not summary:
                    summary = f"Evaluation completed for {name} with an overall defense score of {round(overall, 1)}/10."
                strengths = list(data.get("key_strengths", ["Interview participation"]))
                improvements = list(data.get("areas_for_improvement", ["Deepen technical defense answers"]))

                return voice_defense.InterviewEvaluation(
                    status="completed",
                    overall_score=round(overall, 1),
                    technical_depth_score=round(tech, 1),
                    clarity_articulation_score=round(clarity, 1),
                    project_defense_score=round(proj, 1),
                    summary=summary,
                    key_strengths=strengths,
                    areas_for_improvement=improvements,
                )
            except Exception as exc:
                logger.warning("Voice defense AI evaluation call failed: %s; using rigorous semantic fallback.", exc)

        # Rigorous semantic fallback evaluation
        cand_answers = [t["text"] for t in turns if t.get("speaker") == "candidate"]
        cand_text = " ".join(cand_answers).lower()
        all_words = cand_text.split()
        total_words = len(all_words)

        tech_lexicon = {
            "architecture", "backend", "frontend", "database", "sql", "api", "rest",
            "microservice", "service", "cache", "redis", "concurrency", "async", "latency",
            "throughput", "schema", "query", "index", "docker", "kubernetes", "testing",
            "test", "pipeline", "component", "state", "server", "http", "socket", "endpoint",
            "scaling", "load", "balancer", "tradeoff", "benchmark", "git", "python",
            "javascript", "typescript", "react", "fastapi", "postgres", "sqlite", "node",
            "framework", "deploy", "ci", "cd", "orm", "session", "model", "controller",
            "security", "auth", "token", "jwt", "event", "queue", "kafka", "rabbitmq"
        }
        rubbish_indicators = [
            "rubbish", "nonsense", "gibberish", "blah", "idk", "don't know", "dont know",
            "no idea", "asdf", "qwerty", "lol", "haha", "nothing", "foo bar", "random", "joke"
        ]

        found_tech_terms = [w for w in tech_lexicon if w in cand_text]
        tech_score = len(found_tech_terms)
        has_rubbish_flags = any(r in cand_text for r in rubbish_indicators)

        if total_words < 15 or tech_score == 0 or has_rubbish_flags:
            base_score = 1.5 if has_rubbish_flags or total_words < 10 else 2.5
            summary = (
                f"Candidate {name} provided non-technical, superficial, or nonsensical responses "
                f"that failed to address the technical defense questions for {repo}."
            )
            key_strengths = ["Participated in the interview session"]
            areas_for_improvement = [
                "Directly answer technical questions with factual software engineering concepts",
                "Demonstrate core architecture and design knowledge for the submitted project",
                "Avoid non-technical, dismissive, or off-topic responses during technical defense"
            ]
        elif tech_score <= 2:
            base_score = 4.0
            summary = f"Candidate {name} introduced basic concepts but lacked depth when defending technical decisions for {repo}."
            key_strengths = ["Mentioned foundational technologies"]
            areas_for_improvement = ["Elaborate on architectural tradeoffs", "Provide deeper implementation details"]
        elif tech_score <= 5:
            base_score = 6.8
            summary = f"Candidate {name} demonstrated good general understanding of {repo} architecture and stack components."
            key_strengths = [f"Familiarity with {repo} architecture", "Clear communication on technical choices"]
            areas_for_improvement = ["Deepen quantitative performance metrics", "Provide concrete edge-case concurrency handling"]
        else:
            base_score = 8.5
            summary = f"Candidate {name} demonstrated strong technical depth and articulately defended architectural choices for {repo}."
            key_strengths = ["Comprehensive architectural knowledge", "Detailed explanation of technical tradeoffs"]
            areas_for_improvement = ["Continue expanding on distributed system scaling benchmarks"]

        return voice_defense.InterviewEvaluation(
            status="completed",
            overall_score=round(base_score, 1),
            technical_depth_score=round(max(1.0, base_score - 0.2), 1),
            clarity_articulation_score=round(min(10.0, base_score + 0.3), 1),
            project_defense_score=round(base_score, 1),
            summary=summary,
            key_strengths=key_strengths,
            areas_for_improvement=areas_for_improvement,
        )


class AIServiceRepositoryAnalyzer:
    def __init__(self, provider: ProviderFactory) -> None:
        self._provider = provider

    async def analyze(
        self, *, repo_url: str, commit_sha: Optional[str], files: List[Tuple[str, str]]
    ) -> code_verifier.RepositoryAnalysis:
        evidence = prepare_evidence(repo_url, files, commit_sha=commit_sha)
        r = await CodeIntelligence(self._provider()).analyze(evidence)
        return code_verifier.RepositoryAnalysis(
            status=r.status, reason=r.reason, facts=dict(r.facts), summary=r.summary,
            interview_topics=list(r.interview_topics), model=r.model,
        )
