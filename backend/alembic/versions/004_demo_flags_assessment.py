"""demo flags for interview sessions and leaderboard rows

Additive and non-destructive: `is_demo` on voice_sessions and leaderboard_scores so labelled
showcase rows can be told apart from (and removed independently of) genuine ones.

Revision ID: 004_demo_flags_assessment
Revises: 003_ingestion_provenance
Create Date: 2026-10-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_demo_flags_assessment"
down_revision: Union[str, None] = "003_ingestion_provenance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("voice_sessions", "leaderboard_scores")


def upgrade() -> None:
    for t in TABLES:
        op.add_column(t, sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        op.create_index(f"ix_{t}_is_demo", t, ["is_demo"])


def downgrade() -> None:
    for t in TABLES:
        op.drop_index(f"ix_{t}_is_demo", table_name=t)
        op.drop_column(t, "is_demo")
