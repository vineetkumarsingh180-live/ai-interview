"""honest data model: unmeasured values are NULL, no fabricated defaults

* raw_posts.classification (hiring | seeking | NULL = not analysed yet)
* is_demo flag on leads and repositories (clearly labelled development fixtures)
* every score/benchmark/measurement column becomes nullable (NULL = not measured)
* dropped: benchmark_suites.ai_generated_probability, code_evaluation_results.anti_cheat_confidence
  (no reliable method exists; never presented as evidence)

Revision ID: 002_honest_nullable_data
Revises: 001_initial_domain_schema
Create Date: 2026-10-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_honest_nullable_data"
down_revision: Union[str, None] = "001_initial_domain_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# table -> columns that become nullable (type is needed by ALTER on some backends)
_NULLABLE = {
    "job_leads": [
        ("comp_currency", sa.String(10)),
        ("location_mode", sa.String(50)),
        ("clearance_required", sa.Boolean()),
        ("match_score", sa.Float()),
        ("urgency_tier", sa.String(50)),
    ],
    "outreach_drafts": [("prompt_tokens", sa.Integer()), ("completion_tokens", sa.Integer())],
    "candidate_repos": [
        ("target_role", sa.String(150)),
        ("branch", sa.String(100)),
        ("commit_sha", sa.String(64)),
        ("language", sa.String(80)),
    ],
    "benchmark_suites": [
        ("test_coverage_pct", sa.Float()),
        ("cyclomatic_complexity", sa.Float()),
        ("sec_vulnerabilities_count", sa.Integer()),
        ("execution_time_ms", sa.Integer()),
        ("suite_log_output", sa.Text()),
    ],
    "code_evaluation_results": [
        ("composite_health_score", sa.Float()),
        ("architecture_score", sa.Float()),
        ("concurrency_safety_score", sa.Float()),
        ("maintainability_score", sa.Float()),
        ("summary_verdict", sa.Text()),
    ],
    "voice_sessions": [
        ("technical_depth_score", sa.Float()),
        ("clarity_articulation_score", sa.Float()),
        ("architecture_defense_score", sa.Float()),
        ("final_composite_score", sa.Float()),
    ],
    "leaderboard_scores": [
        ("candidate_handle", sa.String(120)),
        ("target_role", sa.String(150)),
        ("repo_name", sa.String(255)),
        ("code_health_score", sa.Float()),
        ("voice_defense_score", sa.Float()),
        ("composite_percentile", sa.Float()),
        ("rank_tier", sa.String(50)),
    ],
}


def upgrade() -> None:
    op.add_column("raw_posts", sa.Column("classification", sa.String(length=20), nullable=True))
    op.create_index("ix_raw_posts_classification", "raw_posts", ["classification"])

    for table in ("job_leads", "candidate_repos"):
        op.add_column(table, sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False))
        op.create_index(f"ix_{table}_is_demo", table, ["is_demo"])

    for table, columns in _NULLABLE.items():
        for name, type_ in columns:
            op.alter_column(table, name, existing_type=type_, nullable=True)

    op.drop_column("benchmark_suites", "ai_generated_probability")
    op.drop_column("code_evaluation_results", "anti_cheat_confidence")


def downgrade() -> None:
    op.add_column("code_evaluation_results", sa.Column("anti_cheat_confidence", sa.Float(), nullable=True))
    op.add_column("benchmark_suites", sa.Column("ai_generated_probability", sa.Float(), nullable=True))
    # Re-tightening nullable columns is unsafe once NULLs exist, so the downgrade keeps them nullable.
    for table in ("candidate_repos", "job_leads"):
        op.drop_index(f"ix_{table}_is_demo", table_name=table)
        op.drop_column(table, "is_demo")
    op.drop_index("ix_raw_posts_classification", table_name="raw_posts")
    op.drop_column("raw_posts", "classification")
