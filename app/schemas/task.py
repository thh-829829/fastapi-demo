from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# 创建任务的请求体
class TaskCreate(BaseModel):
    content: str = Field(description="任务内容", max_length=255)
    goal_id: Optional[int] = Field(None, description="所属目标ID, 可为空")
    priority: Optional[str] = Field("中", description="优先级, 高/中/低")
    deadline: Optional[datetime] = Field(None, description="截止时间")

# 更新任务的请求体
class TaskUpdate(BaseModel):
    content: Optional[str] = Field(None, max_length=255)
    priority: Optional[str] = None
    deadline: Optional[datetime] = None
    is_completed: Optional[bool] = Field(None, description="是否完成")

# 返回给前端的响应模型
class TaskResponse(BaseModel):
    id: int
    content: str
    priority: str
    deadline: Optional[datetime]
    is_completed: bool
    goal_id: Optional[int]
    user_id: int
    create_time: datetime

    class Config:
        from_attributes = True










