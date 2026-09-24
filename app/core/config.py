"""项目统一配置入口。

敏感配置全部从环境变量或 .env 读取，业务模块不再直接写死 JWT、数据库、
Redis、模型名称和外部服务密钥。
"""

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置模型。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "学习助手API"
    app_version: str = "1.0.0"
    host: str
    port: int

    db_host: str
    db_port: int
    db_user: str
    db_password: SecretStr
    db_name: str

    redis_host: str
    redis_port: int
    redis_db: int
    redis_password: str = ""

    jwt_secret_key: SecretStr
    jwt_algorithm: str
    access_token_expire_minutes: int

    deepseek_api_key: SecretStr
    deepseek_base_url: str
    deepseek_model: str
    siliconflow_api_key: SecretStr
    siliconflow_base_url: str
    siliconflow_embedding_model: str
    llm_timeout_seconds: int
    llm_max_retries: int

    # 原必填字段改为可选，保留默认值兼容本地开发
    chromadb_path: str = "./data/chroma_db"
    chromadb_collection: str
    # 新增独立服务配置
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    upload_dir: str
    max_file_size: int

    @property
    def database_url(self) -> str:
        """构造 MySQL SQLAlchemy 连接串，并转义用户名和密码。"""
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password.get_secret_value())
        return (
            f"mysql+pymysql://{user}:{password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    """返回进程内复用的配置单例。"""
    return Settings()
