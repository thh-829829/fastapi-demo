from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey,text, Text
from datetime import datetime
from app.db.database import Base

class Task(Base):
    # 对应数据库中的表名
    __tablename__ = "tasks"

    # 主键、自增ID
    id = Column(Integer, primary_key=True, index=True, comment="任务主键ID")
    # 所属用户ID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="所属用户ID")
    # 所属目标ID，允许为空（独立任务可以不归属目标）
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=True, comment="所属目标ID")
    # 任务内容：非空
    content = Column(String(255), nullable=False, comment="任务内容")
    # 优先级：默认中
    priority = Column(String(10), server_default=text("'中'"), comment="优先级：高/中/低")
    # 截止时间：允许为空
    deadline = Column(DateTime, nullable=True, comment="截止时间")
    # 是否完成，默认未完成
    is_completed = Column(Boolean, default=False, comment="是否已完成")
    # 创建时间：默认当前时间
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")

