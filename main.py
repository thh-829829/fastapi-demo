from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/")
def root():
    return{"msg":"hello world"}

#路径参数接口：{user_id}嵌入URL路径
@app.get("/user/{user_id}")
def get_user_info(user_id:int):
    return {"user_id":user_id,"type":"路径参数"}

# 查询参数：URL？后拼接，函数内未在路径声明的参数自动识别
@app.get("/search")
def search_item(keyword: str,page: int = 1):
    return{
        "search_keyword":keyword,
        "current_page":page ,
        "type":"查询参数"
    }

# 定义请求数据模型
class UserCreate(BaseModel):
    username: str      #必填字符串
    age: int           # 必填整数
    email: str | None =None  # 可选邮箱

# POST接口接收JSON请求体
@app.post("/user/create")
def create_user(uesr:UserCreate):
    return {
        "msg":"用户创建成功",
        "submit_data" : user.model_dump()
    }