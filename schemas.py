# 专门存放接口的输入输出模型

from pydantic import BaseModel, EmailStr
from typing import Optional

# 用户注册请求体模型
class UserCreate(BaseModel):
    username: str  # 用户名，必填
    password: str  # 密码，必填
    email: Optional[EmailStr] = None  # 邮箱，选填

# 用户信息返回模型（不返回密码）
class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None

    # 配置ORM模型自动转换Pydantic模型
    class Config:
        from_attributes = True

# 用户登录请求体
class LoginRequest(BaseModel):
    username: str  # 用户名，必填
    password: str  # 密码，必填
