from fastapi import APIRouter
from app.api.v1.user import router as user_router
from app.api.v1.goal import router as goal_router
from app.api.v1.task import router as task_router
from app.api.v1.file import router as file_router


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(user_router)
api_router.include_router(goal_router)
api_router.include_router(task_router)
api_router.include_router(file_router)