"""Add document version tracking columns."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("document_group_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("version_number", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "documents",
        sa.Column("is_latest", sa.Boolean(), server_default="true", nullable=False),
    )
    op.create_index("ix_documents_document_group_id", "documents", ["document_group_id"])
    op.create_index("ix_documents_is_latest", "documents", ["is_latest"])

    op.execute("UPDATE documents SET document_group_id = id WHERE document_group_id IS NULL")


def downgrade() -> None:
    op.drop_index("ix_documents_is_latest", table_name="documents")
    op.drop_index("ix_documents_document_group_id", table_name="documents")
    op.drop_column("documents", "is_latest")
    op.drop_column("documents", "version_number")
    op.drop_column("documents", "document_group_id")
