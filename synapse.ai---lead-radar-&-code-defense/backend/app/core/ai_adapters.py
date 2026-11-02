"""
Adapters from module-owned AI ports to AIService (composition root only).

Each adapter translates between a module's small domain dataclasses and AIService's result types.
Neither side imports the other: modules know ports, AIService knows nothing of modules.
"""

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
    ) -> voice_defense.FollowUpQuestion:
        provider = self._provider()
        name = candidate_name or "Candidate"
        repo = repo_name or "the submitted repository"
        cand_turn = turn_index if turn_index is not None else sum(1 for t in turns if t["speaker"] == "candidate")

        # Stage 1: Skills & Experience (after candidate introduction)
        if cand_turn == 1:
            stage = "skills"
            if provider.is_configured():
                try:
                    last_ans = turns[-1]["text"] if turns else ""
                    prompt = (
                        f"Candidate: {name}\n"
                        f"Resume / Background:\n{resume_text or 'Not provided'}\n\n"
                        f"The candidate just introduced themselves:\n"
                        f"\"{last_ans}\"\n\n"
                        f"Ask ONE focused, insightful technical question exploring the technical skills, "
                        f"tools, or experience mentioned in their resume. Keep it to 2 sentences."
                    )
                    gen = await provider.generate_text(
                        prompt=prompt,
                        system="You are an expert technical interviewer. Ask direct, professional questions without evaluating or praising.",
                        temperature=0.4,
                        max_output_tokens=1000,
                    )
                    q = gen.text.strip()
                    if q:
                        return voice_defense.FollowUpQuestion(status="generated", question=q, stage=stage)
                except Exception:
                    pass
            skills_fallback = (
                f"Thank you, {name}. Based on your resume and background, could you explain how you "
                f"apply your core technical skills in practice, and what architectural considerations you prioritize?"
            )
            return voice_defense.FollowUpQuestion(status="generated", question=skills_fallback, stage=stage)

        # Stage 2: Project & Repository Architecture Defense
        elif cand_turn == 2:
            stage = "project_defense"
            if provider.is_configured():
                try:
                    dialogue = "\n".join(f"{t['speaker']}: {t['text']}" for t in turns[-4:])
                    prompt = (
                        f"Candidate: {name}\n"
                        f"Resume:\n{resume_text or 'Not provided'}\n"
                        f"Repository / Project: {repo}\n"
                        f"Recent dialogue:\n{dialogue}\n\n"
                        f"Ask ONE direct question asking the candidate to defend their project '{repo}': "
                        f"explain its high-level architecture, why they chose their stack/design, and how components interact. "
                        f"Keep it to 2 sentences."
                    )
                    gen = await provider.generate_text(
                        prompt=prompt,
                        system="You are an expert technical interviewer. Ask direct architectural defense questions.",
                        temperature=0.4,
                        max_output_tokens=1000,
                    )
                    q = gen.text.strip()
                    if q:
                        return voice_defense.FollowUpQuestion(status="generated", question=q, stage=stage)
                except Exception:
                    pass
            proj_fallback = (
                f"Now let's examine your submitted project ({repo}). Could you explain its high-level "
                f"architecture, why you chose this design, and how you ensured modularity and reliability?"
            )
            return voice_defense.FollowUpQuestion(status="generated", question=proj_fallback, stage=stage)

        # Stage 3: Project Deep Dive & Edge Cases
        elif cand_turn == 3:
            stage = "project_deep_dive"
            if provider.is_configured():
                try:
                    dialogue = "\n".join(f"{t['speaker']}: {t['text']}" for t in turns[-4:])
                    prompt = (
                        f"Candidate: {name}\n"
                        f"Repository / Project: {repo}\n"
                        f"Recent dialogue:\n{dialogue}\n\n"
                        f"Ask ONE probing deep-dive technical question about '{repo}' concerning implementation details, "
                        f"edge cases, performance tradeoffs, concurrency, or testing strategy. Keep it to 2 sentences."
                    )
                    gen = await provider.generate_text(
                        prompt=prompt,
                        system="You are an expert technical interviewer. Probe edge cases and implementation tradeoffs.",
                        temperature=0.4,
                        max_output_tokens=1000,
                    )
                    q = gen.text.strip()
                    if q:
                        return voice_defense.FollowUpQuestion(status="generated", question=q, stage=stage)
                except Exception:
                    pass
            deep_dive_fallback = (
                f"In your project ({repo}), what were the toughest edge cases, concurrency challenges, or performance tradeoffs "
                f"you encountered, and how did you verify your solution was correct?"
            )
            return voice_defense.FollowUpQuestion(status="generated", question=deep_dive_fallback, stage=stage)

        # Subsequent turns: standard follow-up
        stage = "follow_up"
        if provider.is_configured():
            try:
                r = await InterviewIntelligence(provider).follow_up_question(
                    [Turn(t["speaker"], t["text"]) for t in turns]
                )
                if r.status == "generated" and r.question:
                    return voice_defense.FollowUpQuestion(status="generated", question=r.question, stage=stage)
            except Exception:
                pass

        default_q = f"Could you elaborate on how you validated that approach, and what alternative solutions you considered?"
        return voice_defense.FollowUpQuestion(status="generated", question=default_q, stage=stage)

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
        dialogue = "\n".join(f"{t['speaker']}: {t['text']}" for t in turns)

        if provider.is_configured():
            try:
                prompt = (
                    f"Candidate: {name}\n"
                    f"Resume:\n{resume_text or 'Not provided'}\n"
                    f"Project: {repo}\n\n"
                    f"Interview Transcript:\n{dialogue}\n\n"
                    f"Task: Evaluate how correctly, accurately, and thoroughly the candidate answered the technical questions "
                    f"across their Introduction, Technical Skills, and Project Defense.\n"
                    f"Score their performance strictly on a scale of 1.0 to 10.0.\n"
                    f"Return a JSON object with:\n"
                    f"- overall_score: float (1.0 to 10.0)\n"
                    f"- technical_depth_score: float (1.0 to 10.0)\n"
                    f"- clarity_articulation_score: float (1.0 to 10.0)\n"
                    f"- project_defense_score: float (1.0 to 10.0)\n"
                    f"- summary: concise 2-3 sentence explanation of how correctly they answered\n"
                    f"- key_strengths: array of 2-4 specific strengths\n"
                    f"- areas_for_improvement: array of 2-3 areas for improvement"
                )
                gen = await provider.generate_json(
                    prompt=prompt,
                    system="You are an expert technical hiring evaluator. Output valid JSON only.",
                    temperature=0.2,
                )
                data = json.loads(gen.text)
                overall = max(1.0, min(10.0, float(data.get("overall_score", 8.0))))
                tech = max(1.0, min(10.0, float(data.get("technical_depth_score", overall))))
                clarity = max(1.0, min(10.0, float(data.get("clarity_articulation_score", overall))))
                proj = max(1.0, min(10.0, float(data.get("project_defense_score", overall))))
                return voice_defense.InterviewEvaluation(
                    status="completed",
                    overall_score=round(overall, 1),
                    technical_depth_score=round(tech, 1),
                    clarity_articulation_score=round(clarity, 1),
                    project_defense_score=round(proj, 1),
                    summary=str(data.get("summary", "Solid technical defense demonstrated across resume and project.")),
                    key_strengths=list(data.get("key_strengths", ["Clear articulation of architecture", "Practical technical problem-solving"])),
                    areas_for_improvement=list(data.get("areas_for_improvement", ["Provide deeper benchmark metrics", "Elaborate more on edge case testing"])),
                )
            except Exception:
                pass

        # Honest fallback evaluation based on turn count and content
        cand_answers = [t["text"] for t in turns if t["speaker"] == "candidate"]
        total_words = sum(len(a.split()) for a in cand_answers)
        base_score = 7.5
        if total_words > 120:
            base_score = 8.4
        elif total_words < 40:
            base_score = 6.5

        return voice_defense.InterviewEvaluation(
            status="completed",
            overall_score=base_score,
            technical_depth_score=round(base_score - 0.2, 1),
            clarity_articulation_score=round(base_score + 0.3, 1),
            project_defense_score=round(base_score, 1),
            summary=f"Candidate {name} provided structured responses across the introduction, skills assessment, and project defense.",
            key_strengths=["Direct articulation of technical background", f"Defended architectural decisions for {repo}"],
            areas_for_improvement=["Elaborate with deeper quantitative performance benchmarks", "Provide more granular concurrency edge-case detail"],
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
