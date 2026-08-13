from security import create_access_token, SECRET_KEY, ALGORITHM
from jose import jwt 

# 生成一个用户ID为1的令牌
token = create_access_token(data={"sub": "1"})
print("生成的JWT令牌:")
print(token)
print("\n令牌格式校验:","三段式" if token.count(".") == 2 else "格式错误")

# 解码令牌
payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
print("\n解析后的令牌载荷:", payload)
print("用户ID:", payload.get("sub"))