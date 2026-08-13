from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas import UserCreate, UserResponse, LoginRequest
from crud_user import create_user, get_user_by_username
from security import hash_password ,verify_password, create_access_token



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

# 添加登录接口
@app.post("/login", summary="用户登录, 返回JWT令牌")
def login(user_data: LoginRequest, db: Session = Depends(get_db)):
    # 1、根据用户名查询用户
    db_user = get_user_by_username(db, user_data.username)

    # 2、校验：用户不存在 或 密码错误，统一返回模糊提示
    # 安全规范：不区分“用户不存在”和“密码错误”，防止攻击者枚举有效账号
    if not db_user or not verify_password(user_data.password, db_user.password):
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    # 3、生成JWT令牌，载荷存入用户ID（sub是JWT标准字段，代表主体）
    access_token = create_access_token(data={"sub": str(db_user.id)})

    # 4、返回标准格式（行业通用格式，前端可直接适配）
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }