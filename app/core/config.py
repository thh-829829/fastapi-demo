# ==================JWT配置 ========================
# 密钥：用户令牌签名，生产环境必须保密，本地开发用随机字符串即可
# 生成方式：终端执行 python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = "替换为你生成的32位随机密钥字符串"
# 签名算法
ALGORITHM = "HS256"
# 令牌默认有效期：30分钟
ACCESS_TOKEN_EXPIRE_MINUTES = 30