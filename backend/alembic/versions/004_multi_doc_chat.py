"""Add multi-document chat support and follow-up suggestions."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_session_documents",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id", "document_id"),
    )
    op.create_index(
        "ix_chat_session_documents_document_id",
        "chat_session_documents",
        ["document_id"],
    )

    op.add_column(
        "chat_messages",
        sa.Column("suggested_followups", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.execute(
        """
        INSERT INTO chat_session_documents (session_id, document_id)
        SELECT id, document_id FROM chat_sessions
        """
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "suggested_followups")
    op.drop_index("ix_chat_session_documents_document_id", table_name="chat_session_documents")
    op.drop_table("chat_session_documents")
