"""Add category, tags, and sentiment columns to documents."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("category", sa.String(length=128), nullable=True))
    op.add_column(
        "documents",
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("documents", sa.Column("sentiment", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "sentiment")
    op.drop_column("documents", "tags")
    op.drop_column("documents", "category")
