"""兼容导入入口：统一复用 security.py 中的鉴权实现。"""

from app.core.security import get_current_user, require_admin

__all__ = ["get_current_user", "require_admin"]
