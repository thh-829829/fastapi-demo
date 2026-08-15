from app.db.database import engine, Base

# 导入模型，确保Base能识别到(必须显式导入，否则不会自动建表)
from app.models.user import User
from app.models.goal import Goal
from app.models.task import Task
from app.models.document import Document

# 增加调试打印！ 看程序识别到哪些表
print("当前Base识别到哪些表:", Base.metadata.tables.keys())

# 自动创建所有继承Base的模型对应的表
Base.metadata.create_all(bind=engine)
print("所有表创建完成")