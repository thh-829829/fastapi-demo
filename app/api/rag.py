import logging
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.rag_service import normal_rag_qa, stream_rag_qa

logger = logging.getLogger("rag-api")

router = APIRouter(prefix="/rag", tags=["RAG知识库"])


# 请求体模型
class AskRequest(BaseModel):
    question: str


@router.post(path="/ask", summary="基于文档的问答接口")
def ask_question(
    req: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    普通RAG问答接口，一次性返回完整回答
    """
    logger.info(f"[RAG接口] 收到问答请求，用户ID：{current_user.id}")
    result = normal_rag_qa(req.question, top_n=8)
    return {
        "code": 200,
        "message": "success",
        "data": result
    }


@router.post(path="/ask/stream", summary="流式文档问答接口（SSE逐字输出）")
def ask_question_stream(
    req: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    流式RAG问答接口，SSE格式逐字返回回答
    """
    logger.info(f"[RAG接口] 收到流式问答请求，用户ID：{current_user.id}")
    generator = stream_rag_qa(req.question, top_n=8)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
