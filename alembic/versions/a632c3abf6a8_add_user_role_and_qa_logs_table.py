"""initialize core tables and add user role

Revision ID: a632c3abf6a8
Revises:
Create Date: 2026-09-15 17:02:51.420974

该迁移同时兼容两种环境：
1. 全新数据库：创建 users、goals、tasks、documents、qa_logs。
2. 已手工建过业务表的旧数据库：跳过已有表，只补 role 字段和 qa_logs。
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a632c3abf6a8"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    """读取当前数据库已有的表名。"""
    return set(sa.inspect(op.get_bind()).get_table_names())


def _column_names(table_name: str) -> set[str]:
    """读取指定表已有的列名。"""
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    """读取指定表已有的索引名。"""
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    """创建核心业务表，并为旧数据库补齐企业级字段。"""
    tables = _table_names()

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False, comment="用户主键ID"),
            sa.Column("username", sa.String(length=50), nullable=False, comment="用户名"),
            sa.Column("password", sa.String(length=255), nullable=False, comment="用户密码"),
            sa.Column("email", sa.String(length=100), nullable=True, comment="邮箱地址"),
            sa.Column(
                "role",
                sa.String(length=20),
                server_default=sa.text("'user'"),
                nullable=False,
                comment="角色：user/admin",
            ),
            sa.Column("create_time", sa.DateTime(), nullable=True, comment="创建时间"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("username"),
        )
        tables.add("users")

    if "goals" not in tables:
        op.create_table(
            "goals",
            sa.Column("id", sa.Integer(), nullable=False, comment="目标主键ID"),
            sa.Column("user_id", sa.Integer(), nullable=False, comment="所属用户ID"),
            sa.Column("title", sa.String(length=100), nullable=False, comment="目标标题"),
            sa.Column("description", sa.Text(), nullable=True, comment="目标详细描述"),
            sa.Column("start_date", sa.Date(), nullable=True, comment="开始日期"),
            sa.Column("end_date", sa.Date(), nullable=True, comment="结束日期"),
            sa.Column(
                "status",
                sa.String(length=20),
                server_default=sa.text("'未开始'"),
                nullable=True,
                comment="目标状态：未开始/进行中/已完成",
            ),
            sa.Column("create_time", sa.DateTime(), nullable=True, comment="创建时间"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        tables.add("goals")

    if "tasks" not in tables:
        op.create_table(
            "tasks",
            sa.Column("id", sa.Integer(), nullable=False, comment="任务主键ID"),
            sa.Column("user_id", sa.Integer(), nullable=False, comment="所属用户ID"),
            sa.Column("goal_id", sa.Integer(), nullable=True, comment="所属目标ID"),
            sa.Column("content", sa.String(length=255), nullable=False, comment="任务内容"),
            sa.Column(
                "priority",
                sa.String(length=10),
                server_default=sa.text("'中'"),
                nullable=True,
                comment="优先级：高/中/低",
            ),
            sa.Column("deadline", sa.DateTime(), nullable=True, comment="截止时间"),
            sa.Column(
                "is_completed",
                sa.Boolean(),
                server_default=sa.text("0"),
                nullable=True,
                comment="是否已完成",
            ),
            sa.Column("create_time", sa.DateTime(), nullable=True, comment="创建时间"),
            sa.ForeignKeyConstraint(["goal_id"], ["goals.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        tables.add("tasks")

    if "documents" not in tables:
        op.create_table(
            "documents",
            sa.Column("id", sa.Integer(), nullable=False, comment="文档主键ID"),
            sa.Column("user_id", sa.Integer(), nullable=False, comment="所属用户ID"),
            sa.Column("filename", sa.String(length=255), nullable=False, comment="原始文件名"),
            sa.Column("file_type", sa.String(length=20), nullable=True, comment="文件类型:pdf/docx等"),
            sa.Column("file_path", sa.String(length=500), nullable=True, comment="本地存储路径"),
            sa.Column("content", sa.Text(), nullable=True, comment="解析后的文本内容"),
            sa.Column("file_size", sa.Integer(), nullable=True, comment="文件大小(字节)"),
            sa.Column("create_time", sa.DateTime(), nullable=True, comment="上传时间"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        tables.add("documents")

    if "role" not in _column_names("users"):
        op.add_column(
            "users",
            sa.Column(
                "role",
                sa.String(length=20),
                server_default=sa.text("'user'"),
                nullable=False,
                comment="角色：user/admin",
            ),
        )

    if "qa_logs" not in tables:
        op.create_table(
            "qa_logs",
            sa.Column("id", sa.Integer(), nullable=False, comment="日志主键ID"),
            sa.Column("user_id", sa.Integer(), nullable=False, comment="提问用户ID"),
            sa.Column("question", sa.Text(), nullable=False, comment="用户原始问题"),
            sa.Column(
                "answer_summary",
                sa.String(length=500),
                nullable=True,
                comment="回答摘要（前500字）",
            ),
            sa.Column("latency_ms", sa.Integer(), nullable=True, comment="耗时(毫秒)"),
            sa.Column("hit_knowledge", sa.Boolean(), nullable=True, comment="是否命中知识库"),
            sa.Column(
                "status",
                sa.String(length=20),
                server_default=sa.text("'success'"),
                nullable=False,
                comment="状态：success/failed",
            ),
            sa.Column("error_msg", sa.Text(), nullable=True, comment="错误信息"),
            sa.Column("create_time", sa.DateTime(), nullable=False, comment="创建时间"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    qa_log_indexes = _index_names("qa_logs")
    if "ix_qa_logs_id" not in qa_log_indexes:
        op.create_index("ix_qa_logs_id", "qa_logs", ["id"], unique=False)
    if "ix_qa_logs_user_id" not in qa_log_indexes:
        op.create_index("ix_qa_logs_user_id", "qa_logs", ["user_id"], unique=False)
    if "ix_qa_logs_create_time" not in qa_log_indexes:
        op.create_index("ix_qa_logs_create_time", "qa_logs", ["create_time"], unique=False)


def downgrade() -> None:
    """回滚本迁移创建的表和企业级字段。"""
    tables = _table_names()

    if "qa_logs" in tables:
        op.drop_table("qa_logs")
    if "role" in _column_names("users"):
        op.drop_column("users", "role")
    for table_name in ("documents", "tasks", "goals", "users"):
        if table_name in _table_names():
            op.drop_table(table_name)
