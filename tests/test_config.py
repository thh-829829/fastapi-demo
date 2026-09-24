"""9 月 20 日环境配置治理测试。"""

from pathlib import Path

from app.core.config import get_settings
from app.core.security import SECRET_KEY
from app.db.database import SQLALCHEMY_DATABASE_URL


def test_database_url_comes_from_settings():
    settings = get_settings()
    assert SQLALCHEMY_DATABASE_URL == settings.database_url
    assert SQLALCHEMY_DATABASE_URL.startswith("mysql+pymysql://")


def test_jwt_secret_comes_from_settings():
    settings = get_settings()
    assert SECRET_KEY
    assert SECRET_KEY == settings.jwt_secret_key.get_secret_value()


def test_env_example_contains_required_configuration():
    content = Path(".env.example").read_text(encoding="utf-8")
    required_keys = {
        "HOST",
        "PORT",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_MODEL",
        "SILICONFLOW_API_KEY",
        "SILICONFLOW_BASE_URL",
        "SILICONFLOW_EMBEDDING_MODEL",
        "DB_HOST",
        "DB_PORT",
        "DB_USER",
        "DB_PASSWORD",
        "DB_NAME",
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_PASSWORD",
        "JWT_SECRET_KEY",
        "JWT_ALGORITHM",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "CHROMADB_PATH",
        "CHROMA_HOST",
        "CHROMA_PORT",
        "UPLOAD_DIR",
        "MAX_FILE_SIZE",
    }
    for key in required_keys:
        assert f"{key}=" in content


def test_alembic_config_does_not_store_database_credentials():
    """迁移配置只能引用环境变量，不能保存固定数据库连接串。"""
    content = Path("alembic.ini").read_text(encoding="utf-8")
    assert "mysql+pymysql://" not in content
    assert "sqlalchemy.url =" in content
