from fastapi import APIRouter, Depends, Query
from app.core.security import get_current_user, require_admin
from app.core.response import success
from app.models.user import User
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
    current_user: User = Depends(require_admin)
):
    """
    管理员分页查询全量问答日志
    - 支持按用户、关键词、时间范围筛选
    - 仅管理员可访问
    """
    total, logs = list_qa_logs_admin(
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


