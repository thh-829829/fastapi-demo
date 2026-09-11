from fastapi import APIRouter, HTTPException, Query, Path
from app.schemas.agent_schema import (
    AgentChatRequest,
    AgentChatResponse,
    AgentChatData,
    SessionListResponse,
    SessionListData,
    SessionHistoryResponse
)
from app.services.agent_service import agent_service

router = APIRouter(tags=["智能学习管家"])


@router.post("/chat", response_model=AgentChatResponse, summary="统一对话接口")
def agent_chat(request: AgentChatRequest):
    """
    智能学习管家统一对话接口
    - 支持任务完成汇报、进度查询分析、学习规划生成三大能力
    - 自动识别用户意图，同一会话保留上下文
    """
    try:
        session_id, reply, intent_type = agent_service.chat(
            user_id=request.user_id,
            session_id=request.session_id,
            message=request.message
        )

        return AgentChatResponse(
            code=200,
            message="success",
            data=AgentChatData(
                session_id=session_id,
                intent_type=intent_type,
                reply=reply
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"服务内部错误：{str(e)}"
        )


@router.get("/sessions", response_model=SessionListResponse, summary="查询用户会话列表")
def get_user_sessions(user_id: int = Query(..., ge=1, description="用户ID")):
    """
    查询指定用户的所有会话列表，按最后活跃时间倒序排列
    """
    try:
        sessions = agent_service.list_sessions(user_id)
        return SessionListResponse(
            code=200,
            message="success",
            data=SessionListData(
                total=len(sessions),
                sessions=sessions
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"服务内部错误：{str(e)}"
        )


@router.get("/sessions/{session_id}", response_model=SessionHistoryResponse, summary="获取会话详细历史")
def get_session_detail(
    session_id: str = Path(..., description="会话ID"),
    user_id: int = Query(..., ge=1, description="用户ID")
):
    """
    获取指定会话的完整对话历史，包含用户、助手、工具调用全部消息
    """
    try:
        history, err = agent_service.get_session_history(user_id, session_id)
        if err:
            raise HTTPException(status_code=400, detail=err)

        return SessionHistoryResponse(
            code=200,
            message="success",
            data=history
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"服务内部错误：{str(e)}"
        )


@router.delete("/sessions/{session_id}", response_model=SessionListResponse, summary="删除指定会话")
def delete_session(
    session_id: str = Path(..., description="会话ID"),
    user_id: int = Query(..., ge=1, description="用户ID")
):
    """
    清空并删除指定会话，删除后历史不可恢复
    """
    try:
        success, err = agent_service.delete_session(user_id, session_id)
        if err:
            raise HTTPException(status_code=400, detail=err)

        # 删除成功后返回最新的会话列表
        sessions = agent_service.list_sessions(user_id)
        return SessionListResponse(
            code=200,
            message="删除成功",
            data=SessionListData(
                total=len(sessions),
                sessions=sessions
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"服务内部错误：{str(e)}"
        )
