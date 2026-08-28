import logging
import sys

# 日志输出格式：时间 - 日志级别 - 文件名 - 日志内容
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(filename)s - %(message)s"
# 时间格式：年-月-日 时:分:秒
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logger():
    """
    初始化全局日志配置
    项目启动时调用一次即可，所有模块复用该配置
    """

    # 获取根日志器
    root_logger = logging.getLogger()

    # 避免热重载时重复添加处理器，导致日志重复打印
    if root_logger.handlers:
        return

    # 根日志级别设为INFO，所有自定义模块默认继承
    root_logger.setLevel(logging.INFO)

    # 控制台输出处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # 应用统一日志格式
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)

    # 降低第三方库的日志级别，避免无关信息刷屏
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

def get_logger(name: str = "rag-app") -> logging.Logger:
    """
    获取日志实例，各模块调用时传入自己的模块名即可
    :param name: 模块名称，用于区分日志来源
    """
    return logging.getLogger(name)

# 初始化日志配置
setup_logger()