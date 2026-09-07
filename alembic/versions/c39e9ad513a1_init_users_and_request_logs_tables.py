"""init users and request_logs tables

Revision ID: c39e9ad513a1
Revises: 
Create Date: 2026-09-07 14:21:31.115600

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c39e9ad513a1'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """初始建表：users（用户）+ request_logs（大模型调用历史）。"""
    # ===== users 用户表 =====
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ===== request_logs 调用历史表 =====
    op.create_table(
        "request_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("task_type", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("input_length", sa.Integer(), nullable=False),
        sa.Column("output_length", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # 支撑"我的历史分页查询"与"按任务类型统计"
    op.create_index("ix_request_logs_user_created", "request_logs", ["user_id", "created_at"])
    op.create_index("ix_request_logs_task_type", "request_logs", ["task_type"])


def downgrade() -> None:
    """回滚：先删子表，再删父表。"""
    op.drop_index("ix_request_logs_task_type", table_name="request_logs")
    op.drop_index("ix_request_logs_user_created", table_name="request_logs")
    op.drop_table("request_logs")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
