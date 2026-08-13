from passlib.context import CryptContext

# 配置加密上下文，使用bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain_password: str) -> str:
    """将明文密码加密为哈希值"""
    return pwd_context.hash(plain_password)

def verify_password(plain_password: str,hashed_password: str) -> bool:
    """验证明文密码和哈希值是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)
