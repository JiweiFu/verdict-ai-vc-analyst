"""Add vc_analysis table.

Revision ID: c3f1a9b7e2d4
Revises: b25d38b0cd7c
Create Date: 2026-06-23 00:00:00.000000

SECURITY: The vcanalysis table has NO api_key column by design — the user's LLM
API key is never persisted.

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel  # noqa: F401

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f1a9b7e2d4"  # pragma: allowlist secret
down_revision: Union[str, Sequence[str], None] = "b25d38b0cd7c"  # pragma: allowlist secret
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "vcanalysis",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("company_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("raw_input", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("provider", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("model", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("recommendation", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("founder_segmentation", sa.Integer(), nullable=True),
        sa.Column("market_score", sa.Integer(), nullable=True),
        sa.Column("product_score", sa.Integer(), nullable=True),
        sa.Column("founder_competency", sa.Integer(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vcanalysis_company_name"), "vcanalysis", ["company_name"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_vcanalysis_company_name"), table_name="vcanalysis")
    op.drop_table("vcanalysis")
