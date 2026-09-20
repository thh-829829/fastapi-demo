from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_admin
from app.core.response import success
from app.db.database import get_db
from app.models.user import User
from app.services.admin_service import list_documents_admin, list_users_admin
from app.services.qa_log_service import list_qa_logs_admin

router = APIRouter(prefix="/admin", tags=["管理员模块"])


@router.get("/debug/whoami", summary="测试：查看当前登录用户（需登录）")
def whoami(current_user: User = Depends(get_current_user)):
    return success(data={"id": current_user.id, "username": current_user.username, "role": current_user.role})


@router.get("/debug/admin-only", summary="测试：仅管理员可访问")
def admin_only(current_user: User = Depends(require_admin)):
    return success(data={"message": "欢迎管理员", "user": current_user.username})


@router.get("/qa-logs", summary="分页查询问答日志")
def get_qa_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    user_id: int = Query(None, ge=1, description="按用户ID筛选"),
    keyword: str = Query(None, description="问题关键词模糊搜索"),
    start_time: str = Query(None, description="开始时间，格式YYYY-MM-DD HH:mm:ss"),
    end_time: str = Query(None, description="结束时间，格式YYYY-MM-DD HH:mm:ss"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    管理员分页查询全量问答日志
    - 支持按用户、关键词、时间范围筛选
    - 仅管理员可访问
    """
    total, logs = list_qa_logs_admin(
        db=db,
        page=page,
        page_size=page_size,
        user_id=user_id,
        keyword=keyword,
        start_time=start_time,
        end_time=end_time
    )
    return success(data={
        "total": total,
        "list": logs
    })


@router.get("/users", summary="分页查询用户列表")
def list_users(
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(20, ge=1, le=100, description="每页条数"),
        keyword: str = Query(None, description="用户名/邮箱关键词搜索"),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    """
    管理员分页查询用户列表
    - 邮箱脱敏处理，不返回密码字段
    - 支持用户名/邮箱关键词模糊搜索
    """
    total, user_list = list_users_admin(
        db=db,
        page=page,
        page_size=page_size,
        keyword=keyword
    )
    return success(data={
        "total": total,
        "list": user_list
    })


@router.get("/documents", summary="分页查询全局文档列表")
def list_documents(
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(20, ge=1, le=100, description="每页条数"),
        user_id: int = Query(None, ge=1, description="按用户ID筛选"),
        keyword: str = Query(None, description="文件名关键词搜索"),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin)
):
    """
    管理员分页查询全局文档元数据
    - 仅返回元数据，不返回文档全文
    - 支持按用户、文件名关键词筛选
    """
    total, doc_list = list_documents_admin(
        db=db,
        page=page,
        page_size=page_size,
        user_id=user_id,
        keyword=keyword
    )
    return success(data={
        "total": total,
        "list": doc_list
    })

