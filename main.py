from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas import UserCreate, UserResponse
from crud_user import create_user, get_user_by_username
from security import hash_password 

app = FastAPI(title = "用户注册接口")

# 用户注册接口 - 明文密码版
@app.post("/register", response_model = UserResponse, summary = "用户注册")
def register(user: UserCreate, db: Session = Depends(get_db)):
    # 1、校验用户名是否已存在
    exist_user = get_user_by_username(db, user.username)
    if exist_user:
        # 抛出HTTP异常，返回400状态码和友好提示
        raise HTTPException(status_code=400, detail="用户名已存在，请更换")

    # 2、密码加密
    hashed_pwd = hash_password(user.password)

    # 3、创建用户
    db_user = create_user(db, user.username, hashed_pwd, user.email)
    return db_user


