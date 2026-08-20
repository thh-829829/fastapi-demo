from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.document_service import get_user_all_documents_content
from app.utils.llm_client import llm_client
from app.utils.prompt_templates import build_rag_qa_prompt

router = APIRouter(prefix="/rag", tags=["RAG知识库"])

# 请求体模型
class AskRequest(BaseModel):
    question: str

@router.post("/ask", summary="基于文档的问答接口")
def ask_question(
        req: AskRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1、读取当前用户所有文档内容
    doc_content = get_user_all_documents_content(db, current_user.id)

    # 2、无文档时返回友好提示
    if not doc_content.strip():
        raise HTTPException(status_code=400, detail="当前暂无上传文档，请先上传文档后再提问")

    # 3、构建结构化Prompt（系统提示词 + 用户问题）
    messages = build_rag_qa_prompt(doc_content, req.question)

    # 4、调用大模型
    try:
        answer = llm_client.chat_with_messages(messages, temperature=0.3)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=f"大模型调用失败:{str(e)}")

    # 5、返回结果
    return {
        "code": 200,
        "message": "success",
        "data":{
            "question": req.question,
            "answer": answer
        }
    }