from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, text
from datetime import datetime
from app.db.database import Base

class Goal(Base):
    # 对应数据库中的表名
    __tablename__ = "goals"

    # 主键、自增ID
    id = Column(Integer, primary_key=True, index=True, comment="目标主键ID")
    # 所属用户ID，关联用户表，一对多关系
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="所属用户ID")
    # 目标标题，非空
    title = Column(String(100), nullable=False, comment="目标标题")
    # 目标描述：允许为空
    description = Column(Text, nullable = True, comment="目标详细描述")
    # 开始日期
    start_date = Column(Date, nullable=True, comment="开始日期")
    # 截止日期
    end_date = Column(Date, nullable=True, comment="结束日期")
    # 目标状态：默认未开始  
    status = Column(String(20), server_default=text("'未开始'"), comment="目标状态：未开始/进行中/已完成")
    # 创建时间：默认当前时间
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")