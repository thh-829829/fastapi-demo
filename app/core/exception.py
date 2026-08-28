from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.response import error

import logging

logger = logging.getLogger("global-exception")


async def http_exception_handler(request: Request, exc: HTTPException):
    """处理代码主动抛出的HTTP异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "data": None
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求参数校验异常"""
    # 提取第一个错误信息返回
    err_msg = exc.errors()[0].get("msg", "参数校验失败")
    logger.warning(f"参数校验失败: {err_msg}")
    return JSONResponse(
        status_code=422,
        content=error(code=422, message=err_msg)
    )


async def global_exception_handler(request: Request, exc: Exception):
    """全局兜底异常处理器，捕获所有未处理的错误"""
    logger.error(f"未捕获的系统异常: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "服务器内部错误，请稍后重试",
            "data": None
        }
    )


async def runtime_exception_handler(request: Request, exc: RuntimeError):
    """全局捕获业务运行时异常，统一返回标准错误格式"""
    logger.error(f"[业务异常] {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={
            "code": 400,
            "message": str(exc),
            "data": None
        }
    )




