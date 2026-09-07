"""request_logs 表模型：记录每次大模型调用。

隐私设计：不存储用户输入/输出的原文，只存长度、模型、耗时、状态等元数据。
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RequestLog(Base):
    __tablename__ = "request_logs"
    __table_args__ = (
        # 支撑"我的历史分页查询"与"按任务类型统计"
        Index("ix_request_logs_user_created", "user_id", "created_at"),
        Index("ix_request_logs_task_type", "task_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    task_type: Mapped[str] = mapped_column(String(20), nullable=False)  # summarize / translate
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    input_length: Mapped[int] = mapped_column(Integer, nullable=False)
    output_length: Mapped[int | None] = mapped_column(Integer, nullable=True)

    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success / failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="request_logs")
