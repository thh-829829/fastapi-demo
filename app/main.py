from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router

from app.core.exception import http_exception_handler, validation_exception_handler,global_exception_handler
from app.core.exception import runtime_exception_handler
from app.core.logger import setup_logger
from app.core.config import get_settings


class NoCacheStaticFiles(StaticFiles):
    """HTML 页面禁用浏览器缓存，确保移动端能及时加载最新布局。"""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if path.endswith(".html"):
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, max-age=0"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


# 项目启动立即初始化日志系统
setup_logger()

settings = get_settings()

# 创建应用实例，标题改为新项目名
app = FastAPI(title=settings.app_name, version=settings.app_version)


# 挂载静态文件目录
# 将本地 static 文件夹挂载到 /static 路径下。这样用户访问 http://域名/static/图片.jpg 就能直接获取静态文件。
app.mount("/static", NoCacheStaticFiles(directory="static"), name="static")

# 统一注册 /api/v1 下的业务路由
app.include_router(api_router)

# 注册全局异常处理器
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RuntimeError, runtime_exception_handler)
app.add_exception_handler(Exception,global_exception_handler)
