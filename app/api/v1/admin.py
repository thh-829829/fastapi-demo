from fastapi import APIRouter, Depends
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.core.response import success

router = APIRouter(prefix="/admin", tags=["管理员模块"])


@router.get("/debug/whoami", summary="测试：查看当前登录用户（需登录）")
def whoami(current_user: User = Depends(get_current_user)):
    return success(data={"id": current_user.id, "username": current_user.username, "role": current_user.role})


@router.get("/debug/admin-only", summary="测试：仅管理员可访问")
def admin_only(current_user: User = Depends(require_admin)):
    return success(data={"message": "欢迎管理员", "user": current_user.username})





