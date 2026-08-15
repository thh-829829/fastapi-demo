from sqlalchemy import create_engine,text
from sqlalchemy.orm import declarative_base, sessionmaker,Session
from typing import Generator 


# 数据库连接地址：格式为 数据库类型+驱动：//用户名：密码@地址：端口/数据库名？字符集
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:root123456@localhost:3306/ai_agent_db?charset=utf8mb4"

# 创建数据库引擎
engine = create_engine(SQLALCHEMY_DATABASE_URL)

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