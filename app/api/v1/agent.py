import logging

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from app.schemas.agent_schema import (
    AgentChatRequest,
    AgentChatResponse,
    AgentChatData,
    SessionListResponse,
    SessionListData,
    SessionHistoryResponse
)
from app.services.agent_service import agent_service
from app.core.deps import get_current_user
from app.models.user import User


logger = logging.getLogger("agent-api")

router = APIRouter(tags=["智能学习管家"])


@router.post("/chat", response_model=AgentChatResponse, summary="统一对话接口")
def agent_chat(
    request: AgentChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    智能学习管家统一对话接口
    - 支持任务完成汇报、进度查询分析、学习规划生成三大能力
    - 自动识别用户意图，同一会话保留上下文
    """
    try:
        session_id, reply, intent_type = agent_service.chat(
            user_id=current_user.id,
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

    except HTTPException:
        raise
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("[Agent接口] 对话失败：%s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="服务内部错误，请稍后重试"
        )


@router.get("/sessions", response_model=SessionListResponse, summary="查询我的会话列表")
def get_user_sessions(current_user: User = Depends(get_current_user)):
    """
    查询当前登录用户的所有会话列表，按最后活跃时间倒序排列
    """
    try:
        sessions = agent_service.list_sessions(current_user.id)
        return SessionListResponse(
            code=200,
            message="success",
            data=SessionListData(
                total=len(sessions),
                sessions=sessions
            )
        )
    except Exception as e:
        logger.error("[Agent接口] 会话列表失败：%s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="服务内部错误，请稍后重试"
        )

@router.get("/sessions/{session_id}", response_model=SessionHistoryResponse, summary="获取会话详细历史")
def get_session_detail(
    session_id: str = Path(..., description="会话ID"),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定会话的完整对话历史，仅本人可查看
    """
    try:
        history, err = agent_service.get_session_history(current_user.id, session_id)

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
        logger.error("[Agent接口] 会话历史失败：%s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="服务内部错误，请稍后重试"
        )

@router.delete("/sessions/{session_id}", response_model=SessionListResponse, summary="删除指定会话")
def delete_session(
    session_id: str = Path(..., description="会话ID"),
    current_user: User = Depends(get_current_user)
):
    """
    清空并删除指定会话，仅本人可操作，删除后历史不可恢复
    """
    try:
        success, err = agent_service.delete_session(current_user.id, session_id)
        if err:
            raise HTTPException(status_code=400, detail=err)

        # 删除成功后返回最新的会话列表
        sessions = agent_service.list_sessions(current_user.id)
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
        logger.error("[Agent接口] 删除会话失败：%s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="服务内部错误，请稍后重试"
        )
