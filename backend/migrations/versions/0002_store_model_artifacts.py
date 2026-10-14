"""store model artifacts in the database

Revision ID: 0002_model_artifacts
Revises: 0001_initial_schema
Create Date: 2026-10-14 23:10:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_model_artifacts"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ml_models", sa.Column("artifact", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("ml_models", "artifact")
