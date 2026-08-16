from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.services import task_service
from app.core.deps import get_current_user
from app.models.user import User
from typing import List, Optional

router = APIRouter(prefix="/tasks", tags=["任务管理"])

# 创建任务
@router.post("", response_model=TaskResponse, summary="创建新任务")
def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return task_service.create_task(db, task_in, current_user.id)

# 获取任务列表
@router.get("", response_model=List[TaskResponse], summary="获取我的任务列表")
def get_tasks(
    goal_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return task_service.get_task_list(db, current_user.id, goal_id, skip, limit)

# 获取单个任务详情
@router.get("/{task_id}", response_model=TaskResponse, summary="获取任务详情")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = task_service.get_task_by_id(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

# 更新任务
@router.put("/{task_id}", response_model=TaskResponse, summary="更新任务")
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = task_service.update_task(db, task_id, task_in, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

# 删除任务
@router.delete("/{task_id}", summary="删除任务")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = task_service.delete_task(db, task_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"message": "删除成功"}