from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.goal import GoalCreate, GoalUpdate, GoalResponse
from app.services import goal_service
from app.core.deps import get_current_user
from app.models.user import User
from typing import List

router = APIRouter(prefix="/goals", tags=["目标管理"])

# 创建目标
@router.post("", response_model=GoalResponse, summary="创建新目标")
def create_goal(
        goal_in: GoalCreate,
        db:Session =Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    return goal_service.create_goal(db, goal_in, current_user.id)

# 获取目标列表
@router.get("", response_model=List[GoalResponse], summary="获取我的目标列表")
def get_goals(
        skip: int = 0,
        limit: int = 20,
        db:Session =Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    return goal_service.get_goal_list(db, current_user.id,skip, limit)

# 获取单个目标详情
@router.get("/{goal_id}", response_model=GoalResponse, summary="获取目标详情")
def get_goal(
        goal_id: int,
        db:Session =Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    goal = goal_service.get_goal_by_id(db, goal_id, current_user.id)
    if not goal:
        raise HTTPException(status_code=404, detail="目标不存在")
    return goal

# 更新目标
@router.put("/{goal_id}", response_model=GoalResponse, summary="更新目标")
def update_goal(
        goal_id: int,
        goal_in: GoalUpdate,
        db:Session =Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    goal = goal_service.update_goal(db, goal_id, goal_in, current_user.id)
    if not goal:
        raise HTTPException(status_code=404, detail="目标不存在")
    return goal

# 删除目标
@router.delete("/{goal_id}", summary="删除目标")
def delete_goal(
        goal_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    result = goal_service.delete_goal(db, goal_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404,detail="目标不存在")
    return {"message": "删除成功"}











