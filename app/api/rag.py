from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

import json

from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.document_service import get_user_all_documents_content
from app.utils.llm_client import llm_client
from app.utils.prompt_templates import build_rag_qa_prompt
from app.utils.vector_store import VectorStore

router = APIRouter(prefix="/rag", tags=["RAG知识库"])

# 全局实例化向量库，避免每次请求重复创造连接
vector_store = VectorStore()

# 请求体模型
class AskRequest(BaseModel):
    question: str

@router.post("/ask", summary="基于文档的问答接口")
def ask_question(
        req: AskRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1、将用户问题向量化（与入库使用同一模型，保证向量空间一致）
    query_embedding = llm_client.get_embeddings([req.question])[0]

    # 2、从向量库检索 Top3 最相关的文档片段
    related_chunks = vector_store.search_similar(query_embedding, top_n=8)

    # 3、无匹配内容时返回友好提示
    if not related_chunks:
        raise HTTPException(status_code=400, detail="知识库中未找到相关内容，请先上传文档后再提问")

    # 4、拼接检索到的片段作为参考上下文
    context_parts = []
    for idx, chunk in enumerate(related_chunks, 1):
        context_parts.append(f"[参考资料{idx}]\n{chunk['content']}")
    doc_content = "\n\n".join(context_parts)

    # 组装引用来源信息
    sources = []
    for chunk in related_chunks:
        sources.append({
            "document_id": chunk["metadata"].get("document_id"),
            "chunk_index": chunk["metadata"].get("chunk_index"),
            "content_preview": chunk["content"][:100]
        })

    # 5、 复用你原有的 Prompt 构建函数，无需改动模板
    messages = build_rag_qa_prompt(doc_content, req.question)

    # 6、调用大模型生成回答
    try:
        answer = llm_client.chat_with_messages(messages, temperature=0.3)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=f"大模型调用失败：{str(e)}")

    # 7、返回结果
    return {
        "code": 200,
        "message": "success",
        "data": {
            "question": req.question,
            "answer": answer,
            "sources": sources
        }
    }


@router.post(path="/ask/stream", summary="流式文档问答接口（SSE逐字输出）")
def ask_question_stream(
        req: AskRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    #  1、将用户问题向量化（与入库使用同一模型，保证向量空间一致）
    query_embedding = llm_client.get_embeddings([req.question])[0]

    # 2、从向量库检索 Top8 最相关的文档片段
    related_chunks = vector_store.search_similar(query_embedding, top_n=8)

    # 3、无匹配内容时返回友好提示
    if not related_chunks:
        raise HTTPException(status_code=400, detail="知识库中未找到相关内容，请先上传文档后再提问")

    # 4、拼接检索到的片段作为参考上下文
    context_parts = []
    sources = []
    for idx, chunk in enumerate(related_chunks, 1):
        context_parts.append(f"【参考资料{idx}】\n{chunk['content']}")
        sources.append({
            "document_id": chunk["metadata"].get("document_id"),
            "chunk_index": chunk["metadata"].get("chunk_index"),
            "content_preview": chunk["content"][:100]
        })
    doc_content = "\n\n".join(context_parts)

    # 5、复用原有的 Prompt 构建函数，无需改动模板
    messages = build_rag_qa_prompt(doc_content, req.question)

    # 6、SSE 流式生成器： 逐字推送内容 + 最后推送来源
    # 6、SSE 流式生成器：逐字推送内容 + 最后推送来源
    def generate():
        # 逐字推送回答内容
        for token in llm_client.stream_chat_with_messages(messages):
            content_data = json.dumps({'type': 'content', 'data': token}, ensure_ascii=False)
            yield f"data: {content_data}\n\n"

        # 回答结束后，推送完整引用来源
        sources_data = json.dumps({'type': 'sources', 'data': sources}, ensure_ascii=False)
        yield f"data: {sources_data}\n\n"

        # 推送结束标记
        yield "data: [DONE]\n\n"


    # 7、返回 SSE 流式响应
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )