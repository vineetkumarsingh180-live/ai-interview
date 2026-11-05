"""Job Lead Radar module public API. Import from here only (never from submodules)."""

from . import models  # noqa: F401  (registers tables with SQLAlchemy metadata)
from .router import router
from .ingestion import PLATFORMS, PostRecord, StructuredLead, delete_posts, ingest_post_record
from .interfaces import (
    JobSearchChatbot,
    LeadAnalyzer,
    OutreachDraftResult,
    OutreachDrafter,
    PostAnalysis,
    get_job_search_chatbot,
    get_lead_analyzer,
    get_outreach_drafter,
)
from .provenance import content_hash, normalize_post_text

__all__ = [
    "JobSearchChatbot",
    "LeadAnalyzer",
    "OutreachDraftResult",
    "OutreachDrafter",
    "PostAnalysis",
    "get_job_search_chatbot",
    "get_lead_analyzer",
    "get_outreach_drafter",
    "router",
    "PLATFORMS",
    "PostRecord",
    "StructuredLead",
    "ingest_post_record",
    "delete_posts",
    "content_hash",
    "normalize_post_text",
]

