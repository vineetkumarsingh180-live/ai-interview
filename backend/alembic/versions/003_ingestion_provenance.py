"""ingestion provenance: run log + source/verification/dedup columns

Additive and non-destructive:
* new table `ingestion_runs` (audit trail + rollback handle)
* raw_posts: source_type, verification_status, source_url, posted_at, content_hash (unique),
  provenance, is_demo, ingestion_run_id
* job_leads: entry_source
* candidate_repos: source_type, verification_status, github_repo_id (unique), github_metadata,
  metadata_fetched_at, ingestion_run_id
Existing rows are backfilled: demo fixtures are labelled `demo_fixture`; content hashes are
computed in SQL for existing posts.

Revision ID: 003_ingestion_provenance
Revises: 002_honest_nullable_data
Create Date: 2026-10-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_ingestion_provenance"
down_revision: Union[str, None] = "002_honest_nullable_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_label", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("triggered_by", sa.String(length=80), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("records_seen", sa.Integer(), nullable=False),
        sa.Column("records_created", sa.Integer(), nullable=False),
        sa.Column("records_updated", sa.Integer(), nullable=False),
        sa.Column("records_duplicate", sa.Integer(), nullable=False),
        sa.Column("records_rejected", sa.Integer(), nullable=False),
        sa.Column("records_failed", sa.Integer(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_runs_source_type", "ingestion_runs", ["source_type"])
    op.create_index("ix_ingestion_runs_status", "ingestion_runs", ["status"])
    op.create_index("ix_ingestion_runs_started_at", "ingestion_runs", ["started_at"])

    # ---- raw_posts
    op.add_column("raw_posts", sa.Column("source_type", sa.String(length=40), server_default="api_manual", nullable=False))
    op.add_column("raw_posts", sa.Column("verification_status", sa.String(length=40), server_default="unverified", nullable=False))
    op.add_column("raw_posts", sa.Column("source_url", sa.String(length=1024), nullable=True))
    op.add_column("raw_posts", sa.Column("posted_at", sa.DateTime(), nullable=True))
    op.add_column("raw_posts", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column("raw_posts", sa.Column("provenance", sa.JSON(), server_default="{}", nullable=False))
    op.add_column("raw_posts", sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("raw_posts", sa.Column("ingestion_run_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_raw_posts_ingestion_run", "raw_posts", "ingestion_runs", ["ingestion_run_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_raw_posts_source_type", "raw_posts", ["source_type"])
    op.create_index("ix_raw_posts_is_demo", "raw_posts", ["is_demo"])
    op.create_index("ix_raw_posts_ingestion_run_id", "raw_posts", ["ingestion_run_id"])

    # ---- job_leads
    op.add_column("job_leads", sa.Column("entry_source", sa.String(length=30), server_default="ai_extracted", nullable=False))

    # ---- candidate_repos
    op.add_column("candidate_repos", sa.Column("source_type", sa.String(length=40), server_default="api_manual", nullable=False))
    op.add_column("candidate_repos", sa.Column("verification_status", sa.String(length=40), server_default="unverified", nullable=False))
    op.add_column("candidate_repos", sa.Column("github_repo_id", sa.BigInteger(), nullable=True))
    op.add_column("candidate_repos", sa.Column("github_metadata", sa.JSON(), nullable=True))
    op.add_column("candidate_repos", sa.Column("metadata_fetched_at", sa.DateTime(), nullable=True))
    op.add_column("candidate_repos", sa.Column("ingestion_run_id", sa.UUID(), nullable=True))
    op.create_unique_constraint("uq_candidate_repos_github_repo_id", "candidate_repos", ["github_repo_id"])
    op.create_foreign_key("fk_candidate_repos_ingestion_run", "candidate_repos", "ingestion_runs", ["ingestion_run_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_candidate_repos_source_type", "candidate_repos", ["source_type"])
    op.create_index("ix_candidate_repos_ingestion_run_id", "candidate_repos", ["ingestion_run_id"])

    # ---- backfill existing rows (nothing is deleted)
    op.execute(
        "UPDATE raw_posts SET is_demo = true, source_type = 'demo_fixture', verification_status = 'demo_fixture' "
        "WHERE external_id LIKE 'demo-fixture-%'"
    )
    op.execute(
        "UPDATE raw_posts SET content_hash = encode(sha256(convert_to("
        "lower(platform) || E'\\n' || normalize(btrim(regexp_replace(raw_content, '\\s+', ' ', 'g')), NFC), 'UTF8')), 'hex')"
    )
    op.create_index("ix_raw_posts_content_hash", "raw_posts", ["content_hash"], unique=True)
    op.execute("UPDATE job_leads SET entry_source = 'demo_fixture' WHERE is_demo")
    op.execute(
        "UPDATE candidate_repos SET source_type = 'demo_fixture', verification_status = 'demo_fixture' WHERE is_demo"
    )


def downgrade() -> None:
    op.drop_index("ix_candidate_repos_ingestion_run_id", table_name="candidate_repos")
    op.drop_index("ix_candidate_repos_source_type", table_name="candidate_repos")
    op.drop_constraint("fk_candidate_repos_ingestion_run", "candidate_repos", type_="foreignkey")
    op.drop_constraint("uq_candidate_repos_github_repo_id", "candidate_repos", type_="unique")
    for col in ("ingestion_run_id", "metadata_fetched_at", "github_metadata", "github_repo_id", "verification_status", "source_type"):
        op.drop_column("candidate_repos", col)
    op.drop_column("job_leads", "entry_source")
    op.drop_index("ix_raw_posts_content_hash", table_name="raw_posts")
    op.drop_index("ix_raw_posts_ingestion_run_id", table_name="raw_posts")
    op.drop_index("ix_raw_posts_is_demo", table_name="raw_posts")
    op.drop_index("ix_raw_posts_source_type", table_name="raw_posts")
    op.drop_constraint("fk_raw_posts_ingestion_run", "raw_posts", type_="foreignkey")
    for col in ("ingestion_run_id", "is_demo", "provenance", "content_hash", "posted_at", "source_url", "verification_status", "source_type"):
        op.drop_column("raw_posts", col)
    op.drop_index("ix_ingestion_runs_started_at", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_status", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_source_type", table_name="ingestion_runs")
    op.drop_table("ingestion_runs")
