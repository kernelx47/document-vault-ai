"""Add upload_batches table and batch_id FK on documents."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "upload_batches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("label", sa.String(256), nullable=False),
        sa.Column("total_files", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "documents",
        sa.Column("batch_id", UUID(as_uuid=True), sa.ForeignKey("upload_batches.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_documents_batch_id", "documents", ["batch_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_batch_id", "documents")
    op.drop_column("documents", "batch_id")
    op.drop_table("upload_batches")
