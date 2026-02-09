"""Migration to add forum support tables.

Revision ID: 002_add_forum_tables
Revises:
Create Date: 2026-02-08

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_add_forum_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create forum support tables."""
    # Create forum_configs table
    op.create_table(
        "forum_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("forum_channel_id", sa.BigInteger(), nullable=False),
        sa.Column("auto_archive_duration", sa.Integer(), nullable=False, server_default="1440"),
        sa.Column("slowmode_delay", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("default_tags", sa.JSON(), nullable=True),
        sa.Column("auto_create_on_join", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("welcome_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("guild_id", "forum_channel_id", name="unique_guild_forum"),
    )

    # Create indexes for forum_configs
    op.create_index("idx_forum_configs_guild_id", "forum_configs", ["guild_id"])
    op.create_index("idx_forum_configs_channel_id", "forum_configs", ["forum_channel_id"])

    # Create forum_threads table
    op.create_table(
        "forum_threads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.BigInteger(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("forum_channel_id", sa.BigInteger(), nullable=False),
        sa.Column("creator_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("assigned_to", sa.BigInteger(), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_activity_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("closed_by", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id", name="unique_thread_id"),
    )

    # Create indexes for forum_threads
    op.create_index("idx_forum_threads_guild_id", "forum_threads", ["guild_id"])
    op.create_index("idx_forum_threads_forum_channel_id", "forum_threads", ["forum_channel_id"])
    op.create_index("idx_forum_threads_creator_id", "forum_threads", ["creator_id"])
    op.create_index("idx_forum_threads_status", "forum_threads", ["status"])
    op.create_index("idx_forum_threads_assigned_to", "forum_threads", ["assigned_to"])
    op.create_index("idx_forum_threads_priority", "forum_threads", ["priority"])


def downgrade() -> None:
    """Drop forum support tables."""
    # Drop forum_threads table and indexes
    op.drop_index("idx_forum_threads_priority", table_name="forum_threads")
    op.drop_index("idx_forum_threads_assigned_to", table_name="forum_threads")
    op.drop_index("idx_forum_threads_status", table_name="forum_threads")
    op.drop_index("idx_forum_threads_creator_id", table_name="forum_threads")
    op.drop_index("idx_forum_threads_forum_channel_id", table_name="forum_threads")
    op.drop_index("idx_forum_threads_guild_id", table_name="forum_threads")
    op.drop_table("forum_threads")

    # Drop forum_configs table and indexes
    op.drop_index("idx_forum_configs_channel_id", table_name="forum_configs")
    op.drop_index("idx_forum_configs_guild_id", table_name="forum_configs")
    op.drop_table("forum_configs")
