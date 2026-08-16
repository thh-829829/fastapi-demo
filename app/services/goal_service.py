from sqlalchemy.orm import Session
from app.models.goal import Goal
from app.schemas.goal import GoalCreate, GoalUpdate
from datetime import datetime

# 创建目标
def create_goal(db: Session, goal_in: GoalCreate, user_id: int):
    db_goal = Goal(
        title=goal_in.title,
        description=goal_in.description,
        start_date=goal_in.start_date,
        end_date=goal_in.end_date,
        user_id=user_id,
        status="未开始"
    )
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal

# 根据ID查询单个目标（仅当前用户）
def get_goal_by_id(db: Session, goal_id: int, user_id: int):
    return db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user_id).first()

# 查询当前用户的所有目标
def get_goal_list(db: Session, user_id: int, skip: int = 0, limit: int = 20):
    return db.query(Goal).filter(Goal.user_id == user_id).offset(skip).limit(limit).all()

# 更新目标
def update_goal(db: Session, goal_id: int, goal_in: GoalUpdate, user_id: int):
    db_goal = get_goal_by_id(db, goal_id, user_id)
    if not db_goal:
        return None
    update_data = goal_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_goal, key, value)
    db.commit()
    db.refresh(db_goal)
    return db_goal

# 删除目标
def delete_goal(db: Session, goal_id: int, user_id: int):
    db_goal = get_goal_by_id(db, goal_id, user_id)
    if not db_goal:
        return None
    db.delete(db_goal)
    db.commit()
    return True