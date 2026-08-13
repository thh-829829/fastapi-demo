from sqlalchemy.orm import Session
from models import User

# 1、新增用户
def create_user(db: Session, username: str, password: str, email: str = None):
    db_user = User(username=username, password=password, email=email)
    db.add(db_user)   # 添加到会话
    db.commit()   # 提交到数据库
    db.refresh(db_user)  # 刷新对象，获取自增id等数据
    return db_user

# 2、根据ID查询用户
def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

# 3、根据用户名查询用户
def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

# 4、查询所有用户列表
def get_all_users(db: Session):
    return db.query(User).all()

# 5、更新用户信息
def update_user(db: Session, user_id: int, email: str = None, password: str = None):
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    if email:
        db_user.email = email
    if password:
        db_user.password = password
    db.commit()
    db.refresh(db_user)
    return db_user

# 6、删除用户
def delete_user(db: Session, user_id: int):
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    db.delete(db_user)
    db.commit()
    return True