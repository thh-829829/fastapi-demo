from app.schemas.common import ResponseModel
from typing import Any

def success(data=None, message: str = "操作成功"):
    """成功响应快捷方法，直接返回字典,兼容ORM"""
    return {
        "code": 200,
        "message": message,
        "data" : data
    }

def error(code: int = 400, message: str = "操作失败"):
    """错误响应快捷方法"""
    return{
        "code": code,
        "message": message,
        "data": None
    }

