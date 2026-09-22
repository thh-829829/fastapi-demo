from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings


settings = get_settings()

# 数据库连接地址从环境变量读取，避免在源码中保存账号和密码。
SQLALCHEMY_DATABASE_URL = settings.database_url

# 创建数据库引擎
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

# 创建会话工厂，用于生成数据库操作会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建模型基类，所有ORM模型都能继承这个类
Base = declarative_base()


if __name__ =="__main__":
    # 创建一个会话
    db = SessionLocal()
    # 执行简单查询测试连接
    result = db.execute(text("SELECT VERSION()"))
    print("数据库连接成功,MYSQL版本:",result.fetchone()[0])
    db.close()

# 数据库会话依赖，每个请求自动创建一个会话，结束自动关闭
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db  # 把会话交给接口使用
    finally:
        db.close() # 请求结束后自动关闭会话
