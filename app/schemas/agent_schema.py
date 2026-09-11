from pydantic import BaseModel, Field
from typing import Optional, List

# ========== 对话接口模型 ==========
class AgentChatRequest(BaseModel):
    user_id: int = Field(..., ge=1, description="用户ID")
    session_id: Optional[str] = Field(None, max_length=64, description="会话ID，不传则自动生成")
    message: str = Field(..., min_length=1, max_length=2000, description="用户输入消息")


class AgentChatData(BaseModel):
    session_id: str = Field(..., description="会话ID")
    intent_type: str = Field(..., description="识别的意图类型")
    reply: str = Field(..., description="Agent回复内容")


class AgentChatResponse(BaseModel):
    code: int = Field(200, description="状态码")
    message: str = Field("success", description="状态描述")
    data: Optional[AgentChatData] = Field(None, description="响应数据")


# ========== 会话管理模型 ==========
class SessionInfo(BaseModel):
    session_id: str = Field(..., description="会话ID")
    created_at: str = Field(..., description="创建时间")
    last_active_at: str = Field(..., description="最后活跃时间")
    message_count: int = Field(..., description="消息总数")


class SessionListData(BaseModel):
    total: int = Field(..., description="会话总数")
    sessions: List[SessionInfo] = Field(..., description="会话列表")


class SessionListResponse(BaseModel):
    code: int = Field(200, description="状态码")
    message: str = Field("success", description="状态描述")
    data: Optional[SessionListData] = Field(None, description="响应数据")


class SessionHistoryResponse(BaseModel):
    code: int = Field(200, description="状态码")
    message: str = Field("success", description="状态描述")
    data: Optional[List[dict]] = Field(None, description="对话历史消息列表")
