from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
# 导入用户模块的路由对象
from app.api.v1.user import router as user_router
from app.api.v1.goal import router as goal_router
from app.api.v1.file import router as file_router
from app.api.v1.task import router as task_router
from app.api.rag import router as rag_router
from app.core.exception import http_exception_handler, validation_exception_handler,global_exception_handler


# 创建应用实例，标题改为新项目名
app = FastAPI(title="AI Agent智能学习助手")

# 注册用户路由：统一加 /api/v1 前缀
app.include_router(user_router, prefix="/api/v1")

# 注册goal路由
app.include_router(goal_router, prefix="/api/v1")

# 注册file路由到主应用
app.include_router(file_router, prefix="/api/v1")

# 注册task路由
app.include_router(task_router, prefix="/api/v1")

# 注册问答路由
app.include_router(rag_router, prefix="/app/v1")

# 注册全局异常处理器
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception,global_exception_handler)