"""
Dependency wiring (composition root).

Binds the ports declared by a consuming module to implementations, so modules never import each
other and never import the AI package:

    Voice Defense   --LeaderboardPublisher-->  Leaderboard   (publishes session results)
    Voice Defense   --RepositoryLookup------>  Code Verifier (reads repository facts)
    Job Lead Radar  --LeadAnalyzer/OutreachDrafter--> AIService (lead intelligence)
    Voice Defense   --Interviewer------------> AIService (interview intelligence)
    Code Verifier   --RepositoryAnalyzer----> AIService (code intelligence)
"""

from fastapi import FastAPI

from app.modules import code_verifier, job_lead_radar, leaderboard, voice_defense
from app.shared.ai import get_provider

from .ai_adapters import (
    AIServiceInterviewer,
    AIServiceLeadAnalyzer,
    AIServiceOutreachDrafter,
    AIServiceRepositoryAnalyzer,
)


def wire_dependencies(app: FastAPI) -> None:
    recorder = leaderboard.LeaderboardRecorder()
    directory = code_verifier.RepositoryDirectory()
    app.dependency_overrides[voice_defense.get_leaderboard_publisher] = lambda: recorder
    app.dependency_overrides[voice_defense.get_repository_lookup] = lambda: directory

    lead_analyzer = AIServiceLeadAnalyzer(get_provider)
    outreach = AIServiceOutreachDrafter(get_provider)
    interviewer = AIServiceInterviewer(get_provider)
    repository_analyzer = AIServiceRepositoryAnalyzer(get_provider)
    app.dependency_overrides[job_lead_radar.get_lead_analyzer] = lambda: lead_analyzer
    app.dependency_overrides[job_lead_radar.get_outreach_drafter] = lambda: outreach
    app.dependency_overrides[voice_defense.get_interviewer] = lambda: interviewer
    app.dependency_overrides[code_verifier.get_repository_analyzer] = lambda: repository_analyzer
