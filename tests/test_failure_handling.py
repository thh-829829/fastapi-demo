"""异常场景与失败降级测试。"""

from app.api.v1 import file as file_api
from app.services import qa_log_service, rag_service


def test_empty_question_returns_422(client, seeded_users, auth_headers):
    response = client.post(
        "/api/v1/rag/ask",
        json={"question": ""},
        headers=auth_headers(seeded_users["user_a"]),
    )
    assert response.status_code == 422


def test_qa_log_write_failure_returns_false(monkeypatch):
    def failing_session_factory():
        raise RuntimeError("模拟日志数据库不可用")

    monkeypatch.setattr(qa_log_service, "SessionLocal", failing_session_factory)
    result = qa_log_service.create_qa_log(
        user_id=1,
        question="测试问题",
        answer_summary="测试回答",
        latency_ms=10,
        hit_knowledge=False,
    )
    assert result is False


def test_rag_answer_is_not_blocked_by_log_failure(monkeypatch):
    def failing_session_factory():
        raise RuntimeError("模拟日志数据库不可用")

    monkeypatch.setattr(qa_log_service, "SessionLocal", failing_session_factory)
    monkeypatch.setattr(rag_service, "create_qa_log", qa_log_service.create_qa_log)
    monkeypatch.setattr(rag_service.redis_client, "get", lambda key: None)
    monkeypatch.setattr(
        rag_service.redis_client,
        "set",
        lambda key, value, expire_seconds=None: True,
    )
    monkeypatch.setattr(
        rag_service.llm_client,
        "get_embeddings",
        lambda texts: [[0.1, 0.2, 0.3] for _ in texts],
    )
    monkeypatch.setattr(
        rag_service.vector_store,
        "search_similar",
        lambda query_vector, top_n, filter: [
            {
                "content": "日志失败不能中断问答。",
                "metadata": {
                    "document_id": 1,
                    "chunk_index": 0,
                },
                "distance": 0.1,
            }
        ],
    )
    monkeypatch.setattr(
        rag_service.llm_client,
        "chat_with_messages",
        lambda messages, temperature=0.3: "问答仍然成功返回。",
    )

    result = rag_service.normal_rag_qa(
        question="日志失败会怎样？",
        user_id=1,
    )
    assert result["answer"] == "问答仍然成功返回。"


def test_upload_failure_rolls_back_document_record(
    client,
    seeded_users,
    auth_headers,
    db_session_factory,
    monkeypatch,
):
    monkeypatch.setattr(
        file_api,
        "parse_document",
        lambda file_bytes, filename: ("docx", "需要向量化的正文"),
    )
    monkeypatch.setattr(
        file_api.llm_client,
        "get_embeddings",
        lambda texts: [[0.1, 0.2, 0.3] for _ in texts],
    )

    def fail_vector_write(**kwargs):
        raise RuntimeError("模拟向量库写入失败")

    monkeypatch.setattr(
        file_api.vector_store,
        "add_documents_with_embeddings",
        fail_vector_write,
    )
    monkeypatch.setattr(
        file_api.vector_store,
        "delete_by_metadata",
        lambda filter_dict: None,
    )

    response = client.post(
        "/api/v1/files/upload",
        files={"file": ("rollback.docx", b"fake-docx", "application/octet-stream")},
        headers=auth_headers(seeded_users["user_a"]),
    )
    assert response.status_code == 500

    db = db_session_factory()
    from app.models.document import Document

    assert db.query(Document).count() == 0
    db.close()
