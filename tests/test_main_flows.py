"""注册、登录、上传、问答和 Agent 四条主链路冒烟测试。"""

from app.api.v1 import file as file_api
from app.main import app
from app.services import agent_service as agent_service_module
from app.services import rag_service


def test_register_login_and_profile_flow(client):
    register_response = client.post(
        "/api/v1/register",
        json={
            "username": "flow_user",
            "password": "FlowPass123!",
            "email": "flow@example.com",
        },
    )
    assert register_response.status_code == 200
    registered = register_response.json()["data"]
    assert registered["username"] == "flow_user"
    assert registered["role"] == "user"
    assert "password" not in registered

    login_response = client.post(
        "/api/v1/login",
        data={"username": "flow_user", "password": "FlowPass123!"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    profile_response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["data"]["username"] == "flow_user"


def test_goal_and_task_flow(client, seeded_users, auth_headers):
    headers = auth_headers(seeded_users["user_a"])
    goal_response = client.post(
        "/api/v1/goals",
        json={"title": "完成企业级 MVP"},
        headers=headers,
    )
    assert goal_response.status_code == 200
    goal_id = goal_response.json()["id"]

    task_response = client.post(
        "/api/v1/tasks",
        json={"content": "补齐自动化测试", "goal_id": goal_id, "priority": "高"},
        headers=headers,
    )
    assert task_response.status_code == 200
    task_id = task_response.json()["id"]

    update_response = client.put(
        f"/api/v1/tasks/{task_id}",
        json={"is_completed": True},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_completed"] is True


def test_document_upload_and_delete_flow(
    client,
    seeded_users,
    auth_headers,
    monkeypatch,
):
    headers = auth_headers(seeded_users["user_a"])
    captured_metadata = []
    deleted_filters = []

    monkeypatch.setattr(
        file_api,
        "parse_document",
        lambda file_bytes, filename: ("docx", "FastAPI 依赖注入与权限控制"),
    )
    monkeypatch.setattr(
        file_api.llm_client,
        "get_embeddings",
        lambda texts: [[0.1, 0.2, 0.3] for _ in texts],
    )

    def fake_add_documents_with_embeddings(**kwargs):
        captured_metadata.extend(kwargs["metadatas"])

    def fake_delete_by_metadata(filter_dict):
        deleted_filters.append(filter_dict)

    monkeypatch.setattr(
        file_api.vector_store,
        "add_documents_with_embeddings",
        fake_add_documents_with_embeddings,
    )
    monkeypatch.setattr(
        file_api.vector_store,
        "delete_by_metadata",
        fake_delete_by_metadata,
    )

    upload_response = client.post(
        "/api/v1/files/upload",
        files={"file": ("study.docx", b"fake-docx", "application/octet-stream")},
        headers=headers,
    )
    assert upload_response.status_code == 200
    document_id = upload_response.json()["id"]
    assert captured_metadata
    assert all(
        item["user_id"] == seeded_users["user_a"]["id"]
        for item in captured_metadata
    )
    assert all(item["document_id"] == document_id for item in captured_metadata)

    list_response = client.get("/api/v1/files", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    delete_response = client.delete(
        f"/api/v1/files/{document_id}",
        headers=headers,
    )
    assert delete_response.status_code == 200
    assert deleted_filters == [
        {"document_id": document_id, "user_id": seeded_users["user_a"]["id"]}
    ]


def test_rag_qa_flow(client, seeded_users, auth_headers, monkeypatch):
    headers = auth_headers(seeded_users["user_a"])
    logged_events = []

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
                "metadata": {
                    "document_id": 10,
                    "user_id": seeded_users["user_a"]["id"],
                    "chunk_index": 0,
                },
                "distance": 0.1,
            }
        ],
    )
    monkeypatch.setattr(
        rag_service.llm_client,
        "chat_with_messages",
        lambda messages, temperature=0.3: "FastAPI 通过 Depends 实现依赖注入。[1]",
    )
    monkeypatch.setattr(
        rag_service,
        "create_qa_log",
        lambda **kwargs: logged_events.append(kwargs) or True,
    )

    response = client.post(
        "/api/v1/rag/ask",
        json={"question": "FastAPI 如何实现依赖注入？"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "Depends" in data["answer"]
    assert data["sources"][0]["document_id"] == 10
    assert logged_events
    assert logged_events[0]["user_id"] == seeded_users["user_a"]["id"]


def test_agent_chat_flow(client, seeded_users, auth_headers, monkeypatch):
    headers = auth_headers(seeded_users["user_a"])
    captured = {}

    def fake_chat(user_id, session_id, message):
        captured.update(
            {
                "user_id": user_id,
                "session_id": session_id,
                "message": message,
            }
        )
        return "sess_test_123", "已识别的学习计划", "plan_generate"

    monkeypatch.setattr(agent_service_module.agent_service, "chat", fake_chat)

    response = client.post(
        "/api/v1/agent/chat",
        json={
            "user_id": 999,
            "session_id": "sess_test_123",
            "message": "帮我制定一周学习计划",
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["session_id"] == "sess_test_123"
    assert captured["user_id"] == seeded_users["user_a"]["id"]
    assert captured["session_id"] == "sess_test_123"
