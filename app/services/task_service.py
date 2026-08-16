from sqlalchemy.orm import Session
from app.models.task import Task
from app.models.goal import Goal
from app.schemas.task import TaskCreate, TaskUpdate
from fastapi import HTTPException


# 创建任务
def create_task(db: Session, task_in: TaskCreate, user_id: int):
    # 如果传了目标ID，校验目标是否存在且属于当前用户
    if task_in.goal_id:
        goal = db.query(Goal).filter(Goal.id == task_in.goal_id, Goal.user_id == user_id).first()
        if not goal:
            raise HTTPException(status_code=404, detail="所属目标不存在，无法创建任务")

    db_task = Task(
        content=task_in.content,
        goal_id=task_in.goal_id,
        priority=task_in.priority,
        deadline=task_in.deadline,
        user_id=user_id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


# 根据ID查询单个任务（仅当前用户）
def get_task_by_id(db: Session, task_id: int, user_id: int):
    return db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()


# 查询当前用户的任务列表，支持按目标筛选
def get_task_list(db: Session, user_id: int, goal_id: int = None, skip: int = 0, limit: int = 20):
    query = db.query(Task).filter(Task.user_id == user_id)
    if goal_id:
        query = query.filter(Task.goal_id == goal_id)
    return query.offset(skip).limit(limit).all()


# 更新任务
def update_task(db: Session, task_id: int, task_in: TaskUpdate, user_id: int):
    db_task = get_task_by_id(db, task_id, user_id)
    if not db_task:
        return None
    update_data = task_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    return db_task


# 删除任务
def delete_task(db: Session, task_id: int, user_id: int):
    db_task = get_task_by_id(db, task_id, user_id)
    if not db_task:
        return None
    db.delete(db_task)
    db.commit()
    return True


