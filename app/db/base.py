"""ORM 基类：所有数据库模型继承 Base。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """声明式基类。Alembic 自动迁移会扫描所有继承 Base 的模型。"""
