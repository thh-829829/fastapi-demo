"""9 月 23 日容器化竣工验收的静态配置测试。"""

from pathlib import Path

from app.utils.vector_store import vector_store


def test_vector_store_connection_is_lazy():
    """导入应用时不能因为ChromaDB未启动而阻塞测试或接口启动。"""
    assert vector_store._client is None


def test_compose_uses_container_service_names_and_runs_migrations():
    """Compose必须覆盖本机地址，并在启动应用前执行数据库迁移。"""
    content = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "DB_HOST: mysql" in content
    assert "REDIS_HOST: redis" in content
    assert "CHROMA_HOST: chromadb" in content
    assert "CHROMA_PORT: 8000" in content
    assert "alembic upgrade head" in content
    assert "condition: service_healthy" in content
    assert content.count("condition: service_healthy") >= 3
    assert "mysql_data:/var/lib/mysql" in content
    assert "redis_data:/data" in content
    assert "chroma_data:/chroma/chroma" in content
    assert "/api/v2/heartbeat" in content


def test_migration_can_create_a_clean_database():
    """初始迁移必须包含从空库创建全部核心表的定义。"""
    migration = Path(
        "alembic/versions/a632c3abf6a8_add_user_role_and_qa_logs_table.py"
    ).read_text(encoding="utf-8")

    for table_name in ("users", "goals", "tasks", "documents", "qa_logs"):
        assert f'"{table_name}"' in migration
    assert 'if "role" not in _column_names("users")' in migration
