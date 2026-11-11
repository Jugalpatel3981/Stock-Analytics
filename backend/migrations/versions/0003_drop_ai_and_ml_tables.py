"""drop the AI assistant and ML prediction tables

The AI assistant, news sentiment and price prediction features were removed, so their
tables are no longer used.

Revision ID: 0003_drop_ai_ml_tables
Revises: 0002_model_artifacts
Create Date: 2026-11-11 12:00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_drop_ai_ml_tables"
down_revision: str | None = "0002_model_artifacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Children first, so foreign keys never point at a dropped table.
REMOVED_TABLES = (
    "chat_message_sources",
    "chat_messages",
    "chat_sessions",
    "ml_training_runs",
    "ml_models",
    "historical_prices",
)


def upgrade() -> None:
    for table in REMOVED_TABLES:
        op.drop_table(table)


def downgrade() -> None:
    raise NotImplementedError(
        "The AI assistant and ML prediction features were removed; their tables and data "
        "cannot be restored by a downgrade."
    )
