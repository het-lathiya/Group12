"""0008 live destinations: data tier, provider reference and import state on destinations (A2 §4.1).

Revision ID: 0008
Revises: 0007

Executes migrations/sql/0008_live_destinations.sql; downgrade runs
sql/down/0008_live_destinations.down.sql (§5.5).
"""

from pathlib import Path

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | None = None
depends_on: str | None = None

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
NAME = "0008_live_destinations"


def upgrade() -> None:
    op.execute((SQL_DIR / f"{NAME}.sql").read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute((SQL_DIR / "down" / f"{NAME}.down.sql").read_text(encoding="utf-8"))
