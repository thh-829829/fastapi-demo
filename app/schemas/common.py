from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class ResponseModel(BaseModel, Generic[T]):
    """统一响应模型"""
    code: int = 200
    message: str = "操作成功"
    data: Optional[T] = None

class PageResult(BaseModel, Generic[T]):
    """分页数据结果"""
    total: int
    list: List[T]



