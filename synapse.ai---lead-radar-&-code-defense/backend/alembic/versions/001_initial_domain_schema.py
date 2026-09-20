"""initial domain schema with pgvector

Revision ID: 001_initial_domain_schema
Revises: 
Create Date: 2026-03-03 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial_domain_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. raw_posts
    op.create_table(
        'raw_posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('platform', sa.String(32), nullable=False),
        sa.Column('external_id', sa.String(128), nullable=False, unique=True),
        sa.Column('author_handle', sa.String(128), nullable=False),
        sa.Column('author_name', sa.String(128), nullable=False),
        sa.Column('author_avatar_url', sa.String(512), nullable=True),
        sa.Column('raw_content', sa.Text(), nullable=False),
        sa.Column('source_channel', sa.String(128), nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_processed', sa.Boolean(), default=False, nullable=False)
    )

    # 2. job_leads
    op.create_table(
        'job_leads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('raw_post_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('raw_posts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_title', sa.String(128), nullable=False),
        sa.Column('company_name', sa.String(128), nullable=False),
        sa.Column('company_stage', sa.String(64), nullable=True),
        sa.Column('comp_min', sa.Numeric(12, 2), nullable=True),
        sa.Column('comp_max', sa.Numeric(12, 2), nullable=True),
        sa.Column('comp_currency', sa.String(8), default='USD', nullable=False),
        sa.Column('equity_note', sa.String(128), nullable=True),
        sa.Column('tech_stack', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('location_mode', sa.String(32), default='Remote', nullable=False),
        sa.Column('clearance_required', sa.Boolean(), default=False, nullable=False),
        sa.Column('is_hiring', sa.Boolean(), default=True, nullable=False),
        sa.Column('match_score', sa.Float(), default=0.0, nullable=False),
        sa.Column('urgency_tier', sa.String(32), default='Normal', nullable=False),
        sa.Column('contact_anchor', sa.String(256), nullable=True),
        sa.Column('enrichment_metadata', postgresql.JSONB(), default=dict, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )

    # 3. outreach_drafts
    op.create_table(
        'outreach_drafts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('job_leads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tone', sa.String(64), nullable=False),
        sa.Column('pitch_subject', sa.String(256), nullable=False),
        sa.Column('generated_pitch', sa.Text(), nullable=False),
        sa.Column('candidate_profile_context', sa.Text(), nullable=True),
        sa.Column('status', sa.String(32), default='DRAFT', nullable=False),
        sa.Column('model_version', sa.String(64), default='gemini-2.5-flash', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )

    # 4. candidate_repositories
    op.create_table(
        'candidate_repositories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('candidate_name', sa.String(128), nullable=False),
        sa.Column('candidate_github_handle', sa.String(128), nullable=False),
        sa.Column('candidate_avatar_url', sa.String(512), nullable=True),
        sa.Column('repo_url', sa.String(512), nullable=False),
        sa.Column('repo_name', sa.String(128), nullable=False),
        sa.Column('target_role', sa.String(128), nullable=False),
        sa.Column('branch', sa.String(64), default='main', nullable=False),
        sa.Column('commit_sha', sa.String(64), nullable=False),
        sa.Column('language', sa.String(64), nullable=False),
        sa.Column('status', sa.String(32), default='PENDING', nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False)
    )

    # 5. benchmark_suites
    op.create_table(
        'benchmark_suites',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('repo_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidate_repositories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('test_coverage_pct', sa.Float(), nullable=False),
        sa.Column('cyclomatic_complexity', sa.Float(), nullable=False),
        sa.Column('sec_vulnerabilities_count', sa.Integer(), default=0, nullable=False),
        sa.Column('ai_generated_probability', sa.Float(), default=0.0, nullable=False),
        sa.Column('execution_time_ms', sa.Integer(), nullable=False),
        sa.Column('suite_log_output', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )

    # 6. code_evaluations
    op.create_table(
        'code_evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('repo_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidate_repositories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('composite_health_score', sa.Float(), nullable=False),
        sa.Column('architecture_score', sa.Float(), nullable=False),
        sa.Column('concurrency_safety_score', sa.Float(), nullable=False),
        sa.Column('maintainability_score', sa.Float(), nullable=False),
        sa.Column('anti_cheat_confidence', sa.Float(), nullable=False),
        sa.Column('summary_verdict', sa.Text(), nullable=False),
        sa.Column('rubric_breakdown', postgresql.JSONB(), default=dict, nullable=False),
        sa.Column('flagged_anomalies', postgresql.JSONB(), default=list, nullable=False),
        sa.Column('recommended_defense_topics', postgresql.ARRAY(sa.String()), default=list, nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False)
    )

    # 7. voice_sessions
    op.create_table(
        'voice_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('repo_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidate_repositories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_name', sa.String(128), nullable=False),
        sa.Column('session_status', sa.String(32), default='INITIALIZED', nullable=False),
        sa.Column('defense_depth_score', sa.Float(), default=0.0, nullable=False),
        sa.Column('composite_score', sa.Float(), default=0.0, nullable=False),
        sa.Column('verdict', sa.String(32), default='PENDING', nullable=False),
        sa.Column('transcript', postgresql.JSONB(), default=list, nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 8. assessment_leaderboards
    op.create_table(
        'assessment_leaderboards',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('voice_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_name', sa.String(128), nullable=False),
        sa.Column('candidate_handle', sa.String(128), nullable=False),
        sa.Column('target_role', sa.String(128), nullable=False),
        sa.Column('repo_name', sa.String(128), nullable=False),
        sa.Column('code_health_score', sa.Float(), nullable=False),
        sa.Column('voice_defense_score', sa.Float(), nullable=False),
        sa.Column('composite_percentile', sa.Float(), nullable=False),
        sa.Column('rank_tier', sa.String(64), nullable=False),
        sa.Column('status_tag', sa.String(64), default='Passed Defense', nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False)
    )

def downgrade() -> None:
    op.drop_table('assessment_leaderboards')
    op.drop_table('voice_sessions')
    op.drop_table('code_evaluations')
    op.drop_table('benchmark_suites')
    op.drop_table('candidate_repositories')
    op.drop_table('outreach_drafts')
    op.drop_table('job_leads')
    op.drop_table('raw_posts')
