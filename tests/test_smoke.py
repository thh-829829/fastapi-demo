"""9 月 20 日四条主链路冒烟测试。"""

from app.api.v1 import file as file_api
from app.services import agent_service as agent_service_module
from app.services import rag_service


def test_smoke_login_chain(client, seeded_users):
    """登录链路：登录、获取 Token、读取当前用户。"""
    response = client.post(
        "/api/v1/login",
        data={
            "username": seeded_users["user_a"]["username"],
            "password": seeded_users["user_a"]["password"],
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    profile = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile.status_code == 200
    assert profile.json()["data"]["username"] == seeded_users["user_a"]["username"]


def test_smoke_upload_chain(
    client,
    seeded_users,
    auth_headers,
    monkeypatch,
):
    """上传链路：文件解析、向量化、ChromaDB 写入。"""
    monkeypatch.setattr(
        file_api,
        "parse_document",
        lambda file_bytes, filename: ("docx", "冒烟测试文档内容"),
    )
    monkeypatch.setattr(
        file_api.llm_client,
        "get_embeddings",
        lambda texts: [[0.1, 0.2, 0.3] for _ in texts],
    )
    monkeypatch.setattr(
        file_api.vector_store,
        "add_documents_with_embeddings",
        lambda **kwargs: None,
    )

    response = client.post(
        "/api/v1/files/upload",
        headers=auth_headers(seeded_users["user_a"]),
        files={
            "file": (
                "smoke_test.docx",
                b"fake-docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 200


def test_smoke_rag_chain(
    client,
    seeded_users,
    auth_headers,
    monkeypatch,
):
    """问答链路：向量检索、模型回答、来源返回。"""
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
                "content": "FastAPI 使用 Depends 完成依赖注入。",
                "metadata": {"document_id": 1, "chunk_index": 0},
                "distance": 0.1,
            }
        ],
    )
    monkeypatch.setattr(
        rag_service.llm_client,
        "chat_with_messages",
        lambda messages, temperature=0.3: "FastAPI 使用 Depends 完成依赖注入。[1]",
    )
    monkeypatch.setattr(rag_service, "create_qa_log", lambda **kwargs: True)

    response = client.post(
        "/api/v1/rag/ask",
        headers=auth_headers(seeded_users["user_a"]),
        json={"question": "FastAPI 如何实现依赖注入？"},
    )
    assert response.status_code == 200
    assert "answer" in response.json()["data"]


def test_smoke_agent_chain(
    client,
    seeded_users,
    auth_headers,
    monkeypatch,
):
    """Agent 链路：鉴权、会话调用和回复返回。"""
    def fake_chat(user_id, session_id, message):
        assert user_id == seeded_users["user_a"]["id"]
        return "sess_smoke", "当前暂无任务", "progress_query"

    monkeypatch.setattr(agent_service_module.agent_service, "chat", fake_chat)
    response = client.post(
        "/api/v1/agent/chat",
        headers=auth_headers(seeded_users["user_a"]),
        json={"message": "帮我查看一下我的任务列表"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["reply"] == "当前暂无任务"
