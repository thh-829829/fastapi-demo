from database import engine, Base
# 导入模型，确保Base能识别到
import models

# 自动创建所有继承Base的模型对应的表
Base.metadata.create_all(bind=engine)
print("所有表创建完成")