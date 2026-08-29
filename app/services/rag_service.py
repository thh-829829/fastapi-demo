import logging
import json
from typing import Generator, Dict, Any, List

from app.utils.llm_client import llm_client
from app.utils.prompt_templates import build_rag_qa_prompt
from app.utils.vector_store import vector_store
from app.utils.redis_client import redis_client

logger = logging.getLogger("rag-service")


def normal_rag_qa(question: str, top_n: int = 8) -> Dict[str, Any]:
    """
    普通RAG问答：检索相关文档 + 调用大模型生成回答
    :param question: 用户问题文本
    :param top_n: 向量检索返回的相关文档块数量
    :return: 问答结果字典，包含问题、回答、引用来源列表
    """
    # 0、缓存前置判断：相同问题直接命中返回
    cache_key = f"rag:qa:{question}"
    cache_value = redis_client.get(cache_key)
    if cache_value:
        logger.info(f"[RAG问答] 缓存命中，问题：{question}")
        return json.loads(cache_value)

    # 1、将用户问题向量化（与入库使用同一模型，保证向量空间一致）
    query_embedding = llm_client.get_embeddings([question])[0]

    # 2、从向量库检索 TopN 最相关的文档片段
    related_chunks = vector_store.search_similar(query_embedding, top_n=top_n)

    # 3、无匹配内容时抛出业务异常
    if not related_chunks:
        logger.warning("[RAG问答] 知识库未检索到相关内容")
        raise RuntimeError("知识库中未找到相关内容，请先上传文档后再提问")

    # 4、拼接检索到的片段作为参考上下文，组装引用来源
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

    # 5、复用原有 Prompt 模板构建对话消息
    messages = build_rag_qa_prompt(doc_content, question)

    # 6、调用大模型生成回答
    try:
        logger.info("[RAG问答] 开始调用大模型生成回答")
        answer = llm_client.chat_with_messages(messages, temperature=0.3)
        logger.info("[RAG问答] 大模型回答生成完成")
    except RuntimeError:
        # 已包装的业务异常直接透传
        raise
    except Exception as e:
        logger.error(f"[RAG问答] 大模型调用失败：{str(e)}", exc_info=True)
        raise RuntimeError("大模型调用失败，请稍后重试") from e

    # 7、组装结果并写入缓存，设置30分钟过期
    result = {
        "question": question,
        "answer": answer,
        "sources": sources
    }
    try:
        redis_client.set(cache_key, json.dumps(result, ensure_ascii=False), expire_seconds=1800)
        logger.info("[RAG问答] 结果已写入缓存，过期时间30分钟")
    except Exception as e:
        logger.warning(f"[RAG问答] 缓存写入失败，不影响主流程：{str(e)}")

    return result


def stream_rag_qa(question: str, top_n: int = 8) -> Generator[str, None, None]:
    """
    流式RAG问答：检索相关文档 + SSE逐字输出 + 末尾推送引用来源
    :param question: 用户问题文本
    :param top_n: 向量检索返回的相关文档块数量
    :return: SSE标准格式的字符串生成器，可直接放入StreamingResponse
    """
    # 1、将用户问题向量化（与入库使用同一模型，保证向量空间一致）
    query_embedding = llm_client.get_embeddings([question])[0]

    # 2、从向量库检索 TopN 最相关的文档片段
    related_chunks = vector_store.search_similar(query_embedding, top_n=top_n)

    # 3、无匹配内容时抛出业务异常
    if not related_chunks:
        logger.warning("[RAG流式问答] 知识库未检索到相关内容")
        raise RuntimeError("知识库中未找到相关内容，请先上传文档后再提问")

    # 4、拼接检索到的片段作为参考上下文，组装引用来源
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

    # 5、复用原有 Prompt 模板构建对话消息
    messages = build_rag_qa_prompt(doc_content, question)

    # 6、SSE 流式生成器：逐字推送内容 + 最后推送来源 + 结束标记
    def generate():
        try:
            # 逐字返回回答内容
            for token in llm_client.stream_chat_with_messages(messages):
                content_data = json.dumps({"type": "content", "data": token}, ensure_ascii=False)
                yield f"data: {content_data}\n\n"

            # 回答结束，推送引用来源
            sources_data = json.dumps({"type": "sources", "data": sources}, ensure_ascii=False)
            yield f"data: {sources_data}\n\n"

            # 推送结束标记
            yield "data: [DONE]\n\n"
            logger.info("[RAG流式问答] 流式生成完成")
        except RuntimeError as e:
            # 业务异常：以SSE标准错误事件返回
            error_data = json.dumps({"type": "error", "code": 400, "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
            logger.error(f"[RAG流式问答] 业务异常：{str(e)}")
        except Exception as e:
            # 未知异常：统一友好提示，不暴露底层错误
            logger.error(f"[RAG流式问答] 流式生成失败：{str(e)}", exc_info=True)
            error_data = json.dumps({"type": "error", "code": 500, "message": "流式生成失败，请稍后重试"}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return generate()
