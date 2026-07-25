# 导入FastAPI框架
from fastapi import FastAPI

# 创建应用实例，整个项目核心对象
app = FastAPI(title="Hello Demo", version="1.0")

# 定义根路径GET请求接口：访问 127.0.0.1:8000/
@app.get("/")
def root_api():
    # 直接返回字典，FastAPI会自动转为标准JSON
    return {"hello": "world"}