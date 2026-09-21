"""正式测试的公共夹具。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.database import Base, get_db
from app.main import app
from app.models.document import Document  # noqa: F401
from app.models.goal import Goal  # noqa: F401
from app.models.qa_log import QALog  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.user import User


@pytest.fixture()
def db_session_factory():
    """为每个测试创建独立的 SQLite 内存数据库，并覆盖应用的数据库依赖。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield testing_session_local
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session_factory):
    """返回禁用服务端异常直抛的测试客户端，便于断言统一错误响应。"""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture()
def seeded_users(db_session_factory):
    """创建两个普通用户和一个管理员，供权限与数据隔离测试复用。"""
    db = db_session_factory()
    user_specs = [
        ("alice", "AlicePass123!", "alice@example.com", "user"),
        ("bob", "BobPass123!", "bob@example.com", "user"),
        ("admin", "AdminPass123!", "admin@example.com", "admin"),
    ]
    users = []
    for username, password, email, role in user_specs:
        user = User(
            username=username,
            password=hash_password(password),
            email=email,
            role=role,
        )
        db.add(user)
        users.append(user)

    db.commit()
    for user in users:
        db.refresh(user)

    result = {
        "user_a": {
            "id": users[0].id,
            "username": users[0].username,
            "password": user_specs[0][1],
            "role": users[0].role,
        },
        "user_b": {
            "id": users[1].id,
            "username": users[1].username,
            "password": user_specs[1][1],
            "role": users[1].role,
        },
        "admin": {
            "id": users[2].id,
            "username": users[2].username,
            "password": user_specs[2][1],
            "role": users[2].role,
        },
    }
    db.close()
    return result


@pytest.fixture()
def auth_headers():
    """根据测试用户生成真实 JWT 请求头。"""
    def _build(user: dict) -> dict:
        token = create_access_token(
            data={"sub": str(user["id"]), "role": user["role"]}
        )
        return {"Authorization": f"Bearer {token}"}

    return _build
