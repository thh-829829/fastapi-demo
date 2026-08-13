from database import SessionLocal
from crud_user import *

db = SessionLocal()

# 测试1：新增用户
user1 = create_user(db, "test_user2", "123456", "test2@example.com")
print("新增用户成功：", user1.id, user1.username)

# 测试2：根据ID查询
user = get_user_by_id(db, user1.id)
print("查询结果：", user.username, user.email)

# 测试3：更新用户
updated_user = update_user(db, user1.id, email="new_test1@example.com")
print("更新后邮箱：", updated_user.email)

# 测试4：删除用户
result = delete_user(db, user1.id)
print("删除结果：", result)

db.close()