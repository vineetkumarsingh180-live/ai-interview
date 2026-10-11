"""
Synapse.AI AIService: an internal Python package (no server, no database, no web framework).

Public surface: a provider (`GeminiProvider`) plus three capability classes that are handed a
provider. Callers own configuration, persistence, transactions and review states.
"""

from .code_intelligence import CodeAnalysis, CodeIntelligence, RepositoryEvidence, prepare_evidence
from .errors import (
    AIServiceError,
    InvalidProviderResponse,
    ProviderNotConfigured,
    ProviderRateLimited,
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
)
from .interview_intelligence import FollowUp, InterviewIntelligence, RepositoryQuestions, Turn
from .lead_intelligence import LeadAnalysis, LeadFields, LeadIntelligence, OutreachRequest, OutreachResult
from .providers import GeminiProvider, Generation, LLMProvider, Usage

__all__ = [
    "AIServiceError", "CodeAnalysis", "CodeIntelligence", "FollowUp", "GeminiProvider", "Generation",
    "InterviewIntelligence", "InvalidProviderResponse", "LLMProvider", "LeadAnalysis", "LeadFields",
    "LeadIntelligence", "OutreachRequest", "OutreachResult", "ProviderNotConfigured", "ProviderRateLimited",
    "ProviderRejected", "ProviderTimeout", "ProviderUnavailable", "RepositoryEvidence", "RepositoryQuestions",
    "Turn", "Usage", "prepare_evidence",
]
