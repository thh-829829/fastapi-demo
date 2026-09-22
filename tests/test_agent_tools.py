"""Agent 正式工具的数据隔离与核心能力测试。"""

from datetime import datetime

from app.models.goal import Goal
from app.models.task import Task
from app.services import agent_service as agent_module


def _override_agent_db(monkeypatch, db_session_factory):
    def fake_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(agent_module, "get_db", fake_get_db)


def test_agent_task_and_goal_queries_are_user_scoped(
    seeded_users,
    db_session_factory,
    monkeypatch,
):
    db = db_session_factory()
    user_a_goal = Goal(
        user_id=seeded_users["user_a"]["id"],
        title="Alice 目标",
        status="未开始",
    )
    user_b_goal = Goal(
        user_id=seeded_users["user_b"]["id"],
        title="Bob 目标",
        status="未开始",
    )
    db.add_all([user_a_goal, user_b_goal])
    db.commit()
    db.refresh(user_a_goal)
    db.refresh(user_b_goal)

    user_a_task = Task(
        user_id=seeded_users["user_a"]["id"],
        goal_id=user_a_goal.id,
        content="Alice 任务",
        priority="高",
        deadline=datetime(2026, 9, 22, 20, 0, 0),
    )
    user_b_task = Task(
        user_id=seeded_users["user_b"]["id"],
        goal_id=user_b_goal.id,
        content="Bob 任务",
        priority="中",
    )
    db.add_all([user_a_task, user_b_task])
    db.commit()
    db.refresh(user_a_task)
    db.refresh(user_b_task)
    user_b_task_id = user_b_task.id
    db.close()

    _override_agent_db(monkeypatch, db_session_factory)
    service = agent_module.agent_service
    user_a_id = seeded_users["user_a"]["id"]

    task_result = service._execute_tool("list_tasks", {}, user_a_id)
    assert "Alice 任务" in task_result
    assert "Bob 任务" not in task_result
    assert "2026-09-22 20:00:00" in task_result

    goal_result = service._execute_tool("list_goals", {}, user_a_id)
    assert "Alice 目标" in goal_result
    assert "Bob 目标" not in goal_result

    update_result = service._execute_tool(
        "update_task_status",
        {"task_id": user_b_task_id, "is_completed": True},
        user_a_id,
    )
    assert "未更新" in update_result

    db = db_session_factory()
    bob_task = db.query(Task).filter(Task.id == user_b_task_id).first()
    assert bob_task.is_completed is False
    db.close()


def test_agent_can_create_goal_and_own_task(
    seeded_users,
    db_session_factory,
    monkeypatch,
):
    _override_agent_db(monkeypatch, db_session_factory)
    service = agent_module.agent_service
    user_a_id = seeded_users["user_a"]["id"]

    goal_result = service._execute_tool(
        "create_goal",
        {
            "title": "一周 FastAPI 提升计划",
            "description": "覆盖依赖注入、测试和部署",
            "start_date": "2026-09-21",
            "end_date": "2026-09-27",
        },
        user_a_id,
    )
    assert "目标创建成功" in goal_result

    db = db_session_factory()
    goal = db.query(Goal).filter(Goal.user_id == user_a_id).first()
    assert goal is not None
    goal_id = goal.id
    db.close()

    task_result = service._execute_tool(
        "create_task",
        {
            "content": "完成依赖注入练习",
            "goal_id": goal_id,
            "priority": "高",
            "deadline": "2026-09-22 20:00:00",
        },
        user_a_id,
    )
    assert "任务创建成功" in task_result

    db = db_session_factory()
    task = db.query(Task).filter(Task.user_id == user_a_id).first()
    assert task is not None
    assert task.goal_id == goal_id
    db.close()


def test_agent_cannot_create_task_under_another_users_goal(
    seeded_users,
    db_session_factory,
    monkeypatch,
):
    db = db_session_factory()
    bob_goal = Goal(
        user_id=seeded_users["user_b"]["id"],
        title="Bob 私有目标",
        status="未开始",
    )
    db.add(bob_goal)
    db.commit()
    db.refresh(bob_goal)
    bob_goal_id = bob_goal.id
    db.close()

    _override_agent_db(monkeypatch, db_session_factory)
    result = agent_module.agent_service._execute_tool(
        "create_task",
        {"content": "越权任务", "goal_id": bob_goal_id},
        seeded_users["user_a"]["id"],
    )
    assert "执行失败" in result or "所属目标不存在" in result

    db = db_session_factory()
    assert db.query(Task).count() == 0
    db.close()


def test_agent_knowledge_tool_uses_current_user(
    seeded_users,
    db_session_factory,
    monkeypatch,
):
    _override_agent_db(monkeypatch, db_session_factory)
    captured = {}

    def fake_rag_qa(question, user_id, top_n=5):
        captured.update(
            {
                "question": question,
                "user_id": user_id,
                "top_n": top_n,
            }
        )
        return {
            "answer": "FastAPI 使用 Depends 完成依赖注入。",
            "sources": [{"document_id": 12, "chunk_index": 0}],
        }

    monkeypatch.setattr(
        agent_module.rag_service,
        "normal_rag_qa",
        fake_rag_qa,
    )

    user_a_id = seeded_users["user_a"]["id"]
    result = agent_module.agent_service._execute_tool(
        "search_knowledge_base",
        {"question": "FastAPI 怎么实现依赖注入？"},
        user_a_id,
    )
    assert "Depends" in result
    assert captured == {
        "question": "FastAPI 怎么实现依赖注入？",
        "user_id": user_a_id,
        "top_n": 5,
    }
