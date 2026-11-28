"""0009 allow GROQ generation records (IMD-223).

Revision ID: 0009
Revises: 0008
"""

from pathlib import Path

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | None = None
depends_on: str | None = None

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
NAME = "0009_groq_provider"


def upgrade() -> None:
    op.execute((SQL_DIR / f"{NAME}.sql").read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute((SQL_DIR / "down" / f"{NAME}.down.sql").read_text(encoding="utf-8"))
