from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from crud_user import get_user_by_id

# 配置加密上下文，使用bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain_password: str) -> str:
    """将明文密码加密为哈希值"""
    return pwd_context.hash(plain_password)

def verify_password(plain_password: str,hashed_password: str) -> bool:
    """验证明文密码和哈希值是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)

# ==================JWT配置 ========================
# 密钥：用户令牌签名，生产环境必须保密，本地开发用随机字符串即可
# 生成方式：终端执行 python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = "替换为你生成的32位随机密钥字符串"
# 签名算法
ALGORITHM = "HS256"
# 令牌默认有效期：30分钟
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    生成JWT访问令牌
    :param data: 要存入令牌的用户数据,一般存用户ID
    :param expires_delta: 自定义过期时间,不传则用默认值
    :return: JWT令牌字符串
    """
    # 复制数据，避免修改原字典
    to_encode = data.copy()

    # 设置过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # 把过期时间加入载荷
    to_encode.update({"exp": expire})

    # 生成并返回JWT令牌
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# OAuth2令牌提取方案，tokenUrl指定登录接口的路径
oauth2_scheme = HTTPBearer()


def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
):
    # 从认证凭证中提取 token 字符串
    token = credentials.credentials
    """
    全局鉴权依赖：解析令牌、验证有效性、返回当前登录用户
    令牌无效/过期/用户不存在时,直接抛出401未授权错误
    """
    # 定义统一的401错误
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效身份凭证,请重新登陆",
        headers={"WWW-Authenticate":"Bearer"},
    )

    try:
        # 1、解码并验证JWT令牌
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # 2、从载荷中取出用户ID（对应登录时存入的sub字段）
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        # 令牌篡改、过期、格式错误都会触发该异常
        raise credentials_exception
    
    # 3、根据用户ID查询数据库
    user = get_user_by_id(db, user_id=int(user_id))
    if user is None:
        raise credentials_exception

    # 4、返回完整用户对象，自动注入到接口函数中
    return user