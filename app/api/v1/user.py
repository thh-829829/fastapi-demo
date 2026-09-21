from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

# 下面所有导入全部改为绝对路径（app.xxx 开头）
from app.db.database import get_db
from app.schemas.user import UserCreate, UserResponse, LoginRequest
from app.services.user_service import create_user, get_user_by_username
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.core.response import success
from app.models.user import User

# 创建路由对象（替代原来的 app），tags 用于在接口文档里分组
router = APIRouter(tags=["用户模块"])


def _serialize_user(user: User) -> dict:
    """统一输出用户公开字段，避免密码等敏感信息被序列化返回"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "create_time": user.create_time
    }


# 用户注册接口 - 把 @app.post 改成 @router.post
@router.post("/register",  summary="用户注册")
def register(user: UserCreate, db: Session = Depends(get_db)):
    # 1、校验用户名是否已存在
    exist_user = get_user_by_username(db, user.username)
    if exist_user:
        raise HTTPException(status_code=400, detail="用户名已存在，请更换")

    # 2、密码加密
    hashed_pwd = hash_password(user.password)

    # 3、创建用户
    db_user = create_user(db, user.username, hashed_pwd, user.email)
    # 只返回公开字段，避免密码哈希被序列化
    return success(data=_serialize_user(db_user), message="注册成功")

# 用户登录接口
@router.post("/login", summary="用户登录, 返回JWT令牌")
def login(from_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1、根据用户名查询用户
    db_user = get_user_by_username(db, from_data.username)

    # 2、校验：用户不存在 或 密码错误，统一返回模糊提示
    if not db_user or not verify_password(from_data.password, db_user.password):
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    # 3、生成JWT令牌
    access_token = create_access_token(data={"sub": str(db_user.id), "role": db_user.role})

    # 4、直接返回标准OAuth2格式，不要套 success()
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# 获取当前登录用户信息接口
@router.get("/users/me", summary="获取当前登录用户信息(需登录)")
def get_my_info(current_user: User = Depends(get_current_user)):
    return success(data=_serialize_user(current_user), message="获取用户信息成功")


@router.get("/info", summary="获取当前用户信息")
def get_user_info(current_user: User = Depends(get_current_user)):
    return success(data=_serialize_user(current_user))
