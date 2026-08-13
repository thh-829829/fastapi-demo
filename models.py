from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base

class User(Base):
    # 对应数据库中的表名
    __tablename__ = "users"

    # 字段定义：主键、自增ID
    id = Column(Integer, primary_key=True, index=True,comment="用户主键ID")
    # 用户名：非空、唯一
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    # 密码：非空
    password = Column(String(255), nullable=False, comment="用户密码")
    # 邮箱：允许为空
    email = Column(String(100), default=None, comment="邮箱地址")
    # 创建时间：默认当前时间
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    