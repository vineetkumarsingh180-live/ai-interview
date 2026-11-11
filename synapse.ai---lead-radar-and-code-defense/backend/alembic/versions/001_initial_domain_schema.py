"""initial schema, generated from the ORM models (no hand edits needed)

Replaces the original 001, which had drifted from the models (different table names, missing
columns, no lead_embeddings table). No database ever ran the old file.

Revision ID: 001_initial_domain_schema
Revises:
Create Date: 2026-10-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy

revision: str = "001_initial_domain_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table('candidate_repos',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('candidate_name', sa.String(length=255), nullable=False),
    sa.Column('candidate_github_handle', sa.String(length=120), nullable=False),
    sa.Column('candidate_avatar_url', sa.String(length=512), nullable=True),
    sa.Column('repo_url', sa.String(length=512), nullable=False),
    sa.Column('repo_name', sa.String(length=255), nullable=False),
    sa.Column('target_role', sa.String(length=150), nullable=False),
    sa.Column('branch', sa.String(length=100), nullable=False),
    sa.Column('commit_sha', sa.String(length=64), nullable=False),
    sa.Column('language', sa.String(length=80), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('submitted_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_repos_candidate_github_handle'), 'candidate_repos', ['candidate_github_handle'], unique=False)
    op.create_index(op.f('ix_candidate_repos_candidate_name'), 'candidate_repos', ['candidate_name'], unique=False)
    op.create_index(op.f('ix_candidate_repos_id'), 'candidate_repos', ['id'], unique=False)
    op.create_index(op.f('ix_candidate_repos_repo_url'), 'candidate_repos', ['repo_url'], unique=False)
    op.create_index(op.f('ix_candidate_repos_status'), 'candidate_repos', ['status'], unique=False)
    op.create_index(op.f('ix_candidate_repos_submitted_at'), 'candidate_repos', ['submitted_at'], unique=False)
    op.create_table('raw_posts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('platform', sa.String(length=50), nullable=False),
    sa.Column('external_id', sa.String(length=255), nullable=False),
    sa.Column('author_handle', sa.String(length=120), nullable=False),
    sa.Column('author_name', sa.String(length=255), nullable=False),
    sa.Column('author_avatar_url', sa.String(length=512), nullable=True),
    sa.Column('raw_content', sa.Text(), nullable=False),
    sa.Column('source_channel', sa.String(length=120), nullable=False),
    sa.Column('ingested_at', sa.DateTime(), nullable=False),
    sa.Column('is_processed', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_raw_posts_author_handle'), 'raw_posts', ['author_handle'], unique=False)
    op.create_index(op.f('ix_raw_posts_external_id'), 'raw_posts', ['external_id'], unique=True)
    op.create_index(op.f('ix_raw_posts_id'), 'raw_posts', ['id'], unique=False)
    op.create_index(op.f('ix_raw_posts_ingested_at'), 'raw_posts', ['ingested_at'], unique=False)
    op.create_index(op.f('ix_raw_posts_is_processed'), 'raw_posts', ['is_processed'], unique=False)
    op.create_index(op.f('ix_raw_posts_platform'), 'raw_posts', ['platform'], unique=False)
    op.create_table('benchmark_suites',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('repo_id', sa.UUID(), nullable=False),
    sa.Column('test_coverage_pct', sa.Float(), nullable=False),
    sa.Column('cyclomatic_complexity', sa.Float(), nullable=False),
    sa.Column('sec_vulnerabilities_count', sa.Integer(), nullable=False),
    sa.Column('ai_generated_probability', sa.Float(), nullable=False),
    sa.Column('execution_time_ms', sa.Integer(), nullable=False),
    sa.Column('suite_log_output', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['repo_id'], ['candidate_repos.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('repo_id')
    )
    op.create_table('code_evaluation_results',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('repo_id', sa.UUID(), nullable=False),
    sa.Column('composite_health_score', sa.Float(), nullable=False),
    sa.Column('architecture_score', sa.Float(), nullable=False),
    sa.Column('concurrency_safety_score', sa.Float(), nullable=False),
    sa.Column('maintainability_score', sa.Float(), nullable=False),
    sa.Column('anti_cheat_confidence', sa.Float(), nullable=False),
    sa.Column('summary_verdict', sa.Text(), nullable=False),
    sa.Column('rubric_breakdown', sa.JSON(), nullable=False),
    sa.Column('flagged_anomalies', sa.JSON(), nullable=False),
    sa.Column('recommended_defense_topics', sa.JSON(), nullable=False),
    sa.Column('evaluated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['repo_id'], ['candidate_repos.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('repo_id')
    )
    op.create_table('job_leads',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('raw_post_id', sa.UUID(), nullable=False),
    sa.Column('role_title', sa.String(length=255), nullable=False),
    sa.Column('company_name', sa.String(length=255), nullable=False),
    sa.Column('company_stage', sa.String(length=100), nullable=True),
    sa.Column('comp_min', sa.Float(), nullable=True),
    sa.Column('comp_max', sa.Float(), nullable=True),
    sa.Column('comp_currency', sa.String(length=10), nullable=False),
    sa.Column('equity_note', sa.String(length=120), nullable=True),
    sa.Column('tech_stack', sa.JSON(), nullable=False),
    sa.Column('location_mode', sa.String(length=50), nullable=False),
    sa.Column('clearance_required', sa.Boolean(), nullable=False),
    sa.Column('is_hiring', sa.Boolean(), nullable=False),
    sa.Column('match_score', sa.Float(), nullable=False),
    sa.Column('urgency_tier', sa.String(length=50), nullable=False),
    sa.Column('contact_anchor', sa.String(length=255), nullable=True),
    sa.Column('enrichment_metadata', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['raw_post_id'], ['raw_posts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('raw_post_id')
    )
    op.create_index(op.f('ix_job_leads_company_name'), 'job_leads', ['company_name'], unique=False)
    op.create_index(op.f('ix_job_leads_created_at'), 'job_leads', ['created_at'], unique=False)
    op.create_index(op.f('ix_job_leads_id'), 'job_leads', ['id'], unique=False)
    op.create_index(op.f('ix_job_leads_is_hiring'), 'job_leads', ['is_hiring'], unique=False)
    op.create_index(op.f('ix_job_leads_role_title'), 'job_leads', ['role_title'], unique=False)
    op.create_table('voice_sessions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('repo_id', sa.UUID(), nullable=True),
    sa.Column('candidate_name', sa.String(length=255), nullable=False),
    sa.Column('session_status', sa.String(length=50), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=False),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('duration_seconds', sa.Integer(), nullable=False),
    sa.Column('technical_depth_score', sa.Float(), nullable=False),
    sa.Column('clarity_articulation_score', sa.Float(), nullable=False),
    sa.Column('architecture_defense_score', sa.Float(), nullable=False),
    sa.Column('final_composite_score', sa.Float(), nullable=False),
    sa.Column('defense_verdict', sa.String(length=50), nullable=False),
    sa.Column('transcript_turns', sa.JSON(), nullable=False),
    sa.Column('key_takeaways', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['repo_id'], ['candidate_repos.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_voice_sessions_candidate_name'), 'voice_sessions', ['candidate_name'], unique=False)
    op.create_index(op.f('ix_voice_sessions_defense_verdict'), 'voice_sessions', ['defense_verdict'], unique=False)
    op.create_index(op.f('ix_voice_sessions_id'), 'voice_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_voice_sessions_repo_id'), 'voice_sessions', ['repo_id'], unique=False)
    op.create_index(op.f('ix_voice_sessions_session_status'), 'voice_sessions', ['session_status'], unique=False)
    op.create_index(op.f('ix_voice_sessions_started_at'), 'voice_sessions', ['started_at'], unique=False)
    op.create_table('lead_embeddings',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('lead_id', sa.UUID(), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=768), nullable=True),
    sa.Column('text_content', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['lead_id'], ['job_leads.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lead_embeddings_lead_id'), 'lead_embeddings', ['lead_id'], unique=True)
    op.create_table('leaderboard_scores',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('candidate_name', sa.String(length=255), nullable=False),
    sa.Column('candidate_avatar_url', sa.String(length=512), nullable=True),
    sa.Column('candidate_handle', sa.String(length=120), nullable=False),
    sa.Column('target_role', sa.String(length=150), nullable=False),
    sa.Column('repo_name', sa.String(length=255), nullable=False),
    sa.Column('code_health_score', sa.Float(), nullable=False),
    sa.Column('voice_defense_score', sa.Float(), nullable=False),
    sa.Column('composite_percentile', sa.Float(), nullable=False),
    sa.Column('rank_tier', sa.String(length=50), nullable=False),
    sa.Column('status_tag', sa.String(length=50), nullable=False),
    sa.Column('recorded_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['voice_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_id')
    )
    op.create_index(op.f('ix_leaderboard_scores_candidate_handle'), 'leaderboard_scores', ['candidate_handle'], unique=False)
    op.create_index(op.f('ix_leaderboard_scores_candidate_name'), 'leaderboard_scores', ['candidate_name'], unique=False)
    op.create_index(op.f('ix_leaderboard_scores_composite_percentile'), 'leaderboard_scores', ['composite_percentile'], unique=False)
    op.create_index(op.f('ix_leaderboard_scores_id'), 'leaderboard_scores', ['id'], unique=False)
    op.create_index(op.f('ix_leaderboard_scores_rank_tier'), 'leaderboard_scores', ['rank_tier'], unique=False)
    op.create_index(op.f('ix_leaderboard_scores_recorded_at'), 'leaderboard_scores', ['recorded_at'], unique=False)
    op.create_table('outreach_drafts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('lead_id', sa.UUID(), nullable=False),
    sa.Column('tone', sa.String(length=50), nullable=False),
    sa.Column('pitch_subject', sa.String(length=255), nullable=False),
    sa.Column('generated_pitch', sa.Text(), nullable=False),
    sa.Column('candidate_profile_context', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('model_version', sa.String(length=80), nullable=False),
    sa.Column('prompt_tokens', sa.Integer(), nullable=False),
    sa.Column('completion_tokens', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['lead_id'], ['job_leads.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_outreach_drafts_created_at'), 'outreach_drafts', ['created_at'], unique=False)
    op.create_index(op.f('ix_outreach_drafts_id'), 'outreach_drafts', ['id'], unique=False)
    op.create_index(op.f('ix_outreach_drafts_lead_id'), 'outreach_drafts', ['lead_id'], unique=False)


def downgrade() -> None:
    op.drop_table('outreach_drafts')
    op.drop_table('leaderboard_scores')
    op.drop_table('lead_embeddings')
    op.drop_table('voice_sessions')
    op.drop_table('job_leads')
    op.drop_table('code_evaluation_results')
    op.drop_table('benchmark_suites')
    op.drop_table('raw_posts')
    op.drop_table('candidate_repos')
