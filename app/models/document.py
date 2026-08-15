from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.db.database import Base


class Document(Base):
    # 对应数据库中的表名
    __tablename__ = "documents"

    # 主键、自增ID
    id = Column(Integer, primary_key=True, index=True, comment="文档主键ID")
    # 所属用户ID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="所属用户ID")
    # 原始文件名：非空
    filename = Column(String(255), nullable=False, comment="原始文件名")
    # 文件类型
    file_type = Column(String(20), nullable=True, comment="文件类型:pdf/docx等")
    # 文件本地存储路径
    file_path = Column(String(500), nullable=True, comment="本地存储路径")
    # 解析后的文本内容（长文本，用Text类型）
    content = Column(Text, nullable=True, comment="解析后的文本内容")
    # 文件大小（单位：字节）
    file_size = Column(Integer, nullable=True, comment="文件大小(字节)")
    # 上传时间：默认当前时间
    create_time = Column(DateTime, default=datetime.now, comment="上传时间")