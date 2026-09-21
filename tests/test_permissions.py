"""权限、角色和跨用户数据隔离测试。"""

from datetime import datetime

from app.models.document import Document
from app.models.goal import Goal
from app.models.qa_log import QALog


def test_missing_token_returns_401(client):
    response = client.get("/api/v1/goals")
    assert response.status_code == 401


def test_invalid_token_returns_401(client):
    response = client.get(
        "/api/v1/goals",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


def test_normal_user_cannot_query_admin_users(client, seeded_users, auth_headers):
    response = client.get(
        "/api/v1/admin/users",
        headers=auth_headers(seeded_users["user_a"]),
    )
    assert response.status_code == 403


def test_normal_user_cannot_query_admin_documents(client, seeded_users, auth_headers):
    response = client.get(
        "/api/v1/admin/documents",
        headers=auth_headers(seeded_users["user_a"]),
    )
    assert response.status_code == 403


def test_normal_user_cannot_query_admin_logs(client, seeded_users, auth_headers):
    response = client.get(
        "/api/v1/admin/qa-logs",
        headers=auth_headers(seeded_users["user_a"]),
    )
    assert response.status_code == 403


def test_admin_can_query_users_with_masked_email(
    client,
    seeded_users,
    auth_headers,
):
    response = client.get(
        "/api/v1/admin/users",
        headers=auth_headers(seeded_users["admin"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["total"] >= 3
    assert all("password" not in item for item in body["data"]["list"])
    assert any("***" in item["email"] for item in body["data"]["list"])


def test_admin_can_query_document_metadata_without_content(
    client,
    seeded_users,
    auth_headers,
    db_session_factory,
):
    db = db_session_factory()
    db.add(
        Document(
            user_id=seeded_users["user_a"]["id"],
            filename="alice-only.docx",
            file_type="docx",
            content="这段正文不应出现在管理员列表中",
            file_size=42,
        )
    )
    db.commit()
    db.close()

    response = client.get(
        "/api/v1/admin/documents",
        headers=auth_headers(seeded_users["admin"]),
    )
    assert response.status_code == 200
    records = response.json()["data"]["list"]
    assert records
    assert all("content" not in item for item in records)


def test_admin_can_query_qa_logs(client, seeded_users, auth_headers, db_session_factory):
    db = db_session_factory()
    db.add(
        QALog(
            user_id=seeded_users["user_a"]["id"],
            question="如何学习 FastAPI",
            answer_summary="先掌握路由和依赖注入",
            latency_ms=120,
            hit_knowledge=True,
            status="success",
            create_time=datetime.now(),
        )
    )
    db.commit()
    db.close()

    response = client.get(
        "/api/v1/admin/qa-logs",
        headers=auth_headers(seeded_users["admin"]),
    )
    assert response.status_code == 200
    assert response.json()["data"]["total"] >= 1


def test_user_can_query_own_goal(client, seeded_users, auth_headers):
    headers = auth_headers(seeded_users["user_a"])
    created = client.post(
        "/api/v1/goals",
        json={"title": "学习 FastAPI"},
        headers=headers,
    )
    assert created.status_code == 200

    response = client.get("/api/v1/goals", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "学习 FastAPI"


def test_user_cannot_get_another_users_goal(
    client,
    seeded_users,
    auth_headers,
    db_session_factory,
):
    db = db_session_factory()
    goal = Goal(
        user_id=seeded_users["user_a"]["id"],
        title="Alice 的私有目标",
        status="未开始",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    goal_id = goal.id
    db.close()

    response = client.get(
        f"/api/v1/goals/{goal_id}",
        headers=auth_headers(seeded_users["user_b"]),
    )
    assert response.status_code == 404


def test_user_goal_list_does_not_include_another_users_data(
    client,
    seeded_users,
    auth_headers,
    db_session_factory,
):
    db = db_session_factory()
    db.add(
        Goal(
            user_id=seeded_users["user_a"]["id"],
            title="Alice 的目标",
            status="未开始",
        )
    )
    db.commit()
    db.close()

    response = client.get(
        "/api/v1/goals",
        headers=auth_headers(seeded_users["user_b"]),
    )
    assert response.status_code == 200
    assert response.json() == []


def test_user_cannot_update_another_users_goal(
    client,
    seeded_users,
    auth_headers,
    db_session_factory,
):
    db = db_session_factory()
    goal = Goal(
        user_id=seeded_users["user_a"]["id"],
        title="Alice 的私有目标",
        status="未开始",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    goal_id = goal.id
    db.close()

    response = client.put(
        f"/api/v1/goals/{goal_id}",
        json={"title": "越权修改"},
        headers=auth_headers(seeded_users["user_b"]),
    )
    assert response.status_code == 404


def test_user_cannot_delete_another_users_goal(
    client,
    seeded_users,
    auth_headers,
    db_session_factory,
):
    db = db_session_factory()
    goal = Goal(
        user_id=seeded_users["user_a"]["id"],
        title="Alice 的私有目标",
        status="未开始",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    goal_id = goal.id
    db.close()

    response = client.delete(
        f"/api/v1/goals/{goal_id}",
        headers=auth_headers(seeded_users["user_b"]),
    )
    assert response.status_code == 404


def test_user_cannot_create_task_under_another_users_goal(
    client,
    seeded_users,
    auth_headers,
    db_session_factory,
):
    db = db_session_factory()
    goal = Goal(
        user_id=seeded_users["user_a"]["id"],
        title="Alice 的私有目标",
        status="未开始",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    goal_id = goal.id
    db.close()

    response = client.post(
        "/api/v1/tasks",
        json={"content": "越权任务", "goal_id": goal_id},
        headers=auth_headers(seeded_users["user_b"]),
    )
    assert response.status_code == 404


def test_user_cannot_delete_another_users_document(
    client,
    seeded_users,
    auth_headers,
    db_session_factory,
):
    db = db_session_factory()
    document = Document(
        user_id=seeded_users["user_a"]["id"],
        filename="alice-private.docx",
        file_type="docx",
        content="私有正文",
        file_size=20,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    document_id = document.id
    db.close()

    response = client.delete(
        f"/api/v1/files/{document_id}",
        headers=auth_headers(seeded_users["user_b"]),
    )
    assert response.status_code == 404


def test_register_and_current_user_do_not_return_password(
    client,
    auth_headers,
):
    register_response = client.post(
        "/api/v1/register",
        json={
            "username": "charlie",
            "password": "CharliePass123!",
            "email": "charlie@example.com",
        },
    )
    assert register_response.status_code == 200
    register_data = register_response.json()["data"]
    assert "password" not in register_data

    user = {
        "id": register_data["id"],
        "role": register_data["role"],
    }
    me_response = client.get("/api/v1/users/me", headers=auth_headers(user))
    assert me_response.status_code == 200
    assert "password" not in me_response.json()["data"]
