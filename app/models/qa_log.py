from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from datetime import datetime
from app.db.database import Base


class QALog(Base):
    """问答日志：记录每次 RAG / Agent 问答的关键指标，供管理员审计与排障"""
    __tablename__ = "qa_logs"

    # 主键、自增ID
    id = Column(Integer, primary_key=True, index=True, comment="日志主键ID")
    # 提问用户ID，加索引便于按用户查
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="提问用户ID")
    # 用户原始问题
    question = Column(Text, nullable=False, comment="用户原始问题")
    # 回答摘要（截断存储，不存完整回答，避免表过大）
    answer_summary = Column(String(500), nullable=True, comment="回答摘要（前500字）")
    # 耗时（毫秒）
    latency_ms = Column(Integer, nullable=True, comment="耗时(毫秒)")
    # 是否命中知识库
    hit_knowledge = Column(Boolean, default=False, comment="是否命中知识库")
    # 状态：success / failed
    status = Column(String(20), nullable=False, server_default="success", comment="状态：success/failed")
    # 错误信息（失败时记录）
    error_msg = Column(Text, nullable=True, comment="错误信息")
    # 创建时间，加索引便于按时间范围筛选
    create_time = Column(DateTime, default=datetime.now, nullable=False, index=True, comment="创建时间")
