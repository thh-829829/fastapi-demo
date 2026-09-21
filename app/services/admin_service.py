from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.user import User


def mask_email(email: Optional[str]) -> str:
    """邮箱脱敏：保留前两位和域名，其余使用星号替代"""
    if not email or "@" not in email:
        return "***"

    name_part, domain = email.split("@", 1)
    mask_name = f"{name_part[:2]}***" if len(name_part) > 2 else "***"
    return f"{mask_name}@{domain}"


def list_users_admin(
        db: Session,
        page: int,
        page_size: int,
        keyword: Optional[str] = None
) -> tuple[int, list[dict]]:
    """管理员分页查询用户列表，只返回脱敏后的公开字段"""
    query = db.query(User)

    if keyword:
        query = query.filter(
            or_(
                User.username.like(f"%{keyword}%"),
                User.email.like(f"%{keyword}%")
            )
        )

    total = query.count()
    offset = (page - 1) * page_size
    users = query.order_by(User.id.desc()).offset(offset).limit(page_size).all()

    user_list = [
        {
            "id": user.id,
            "username": user.username,
            "email": mask_email(user.email),
            "role": user.role,
            "create_time": user.create_time
        }
        for user in users
    ]
    return total, user_list


def list_documents_admin(
        db: Session,
        page: int,
        page_size: int,
        user_id: Optional[int] = None,
        keyword: Optional[str] = None
) -> tuple[int, list[dict]]:
    """管理员分页查询全局文档元数据，不返回文档全文"""
    query = db.query(Document)

    if user_id:
        query = query.filter(Document.user_id == user_id)
    if keyword:
        query = query.filter(Document.filename.like(f"%{keyword}%"))

    total = query.count()
    offset = (page - 1) * page_size
    documents = query.order_by(Document.id.desc()).offset(offset).limit(page_size).all()

    document_list = [
        {
            "id": document.id,
            "filename": document.filename,
            "file_type": document.file_type,
            "file_size": document.file_size,
            "user_id": document.user_id,
            "create_time": document.create_time
        }
        for document in documents
    ]
    return total, document_list
