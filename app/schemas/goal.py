from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional

# 创建目标的请求体
class GoalCreate(BaseModel):
    title: str =Field(description="目标标题", max_length=100)
    description: Optional[str] = Field(None, description="目标描述", max_length=500)
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="截止日期")

# 更新目标的请求体
class GoalUpdate(BaseModel):
    title: Optional[str] = Field(None, description="目标标题", max_length=100)
    description: Optional[str] = Field(None, description="目标描述", max_length=500)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = Field(None, description="目标状态")

# 返回给前端的响应模型
class GoalResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    start_date: Optional[date]
    end_date: Optional[date]
    user_id: int
    create_time: datetime

    class Config:
        from_attributes = True
