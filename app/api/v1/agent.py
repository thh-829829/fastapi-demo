from fastapi import FastAPI, APIRouter, HTTPException
from app.schemas.agent_schema import AgentChatRequest, AgentChatResponse, AgentChatData
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
        # 调用业务服务层
        session_id, reply = agent_service.chat(
            user_id=request.user_id,
            session_id=request.session_id,
            message=request.message
        )

        # 简易意图识别
        if "状态确认" in reply and "已成功更新" in reply:
            intent_type = "task_complete"
        elif "全局进度总量" in reply and "分维度进度拆解" in reply:
            intent_type = "progress_query"
        elif "目标任务拆解总览" in reply and "每日执行计划" in reply:
            intent_type = "plan_generate"
        else:
            intent_type = "unknown"

        # 封装成功响应
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
        # 统一异常处理，返回500错误
        raise HTTPException(
            status_code=500,
            detail=f"内部服务错误：{str(e)}"
        )

