import logging
import redis
from typing import Optional

logger = logging.getLogger("redis-client")

class RedisClient:
    """
    Redis 客户端封装，单例模式
    提供字符串类型的读写、删除、过期设置基础操作
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 6379, db: int = 0):
        """
        初始化Redis连接
        :param host: Redis服务地址
        :param port: Redis服务端口
        :param db: 数据库编号
        """
        try:
            self.client = redis.Redis(
                host=host, port=port, db=db,
                decode_responses=True, # 自动解码为字符串，不用手动转 bytes
                socket_connect_timeout=3
            )
            # 测试链连接
            self.client.ping()
            logger.info("[Redis初始化] 连接成功")
        except Exception as e:
            logger.error(f"[Redis初始化] 连接失败：{str(e)}", exc_info=True)
            raise RuntimeError("Redis连接失败，请检查服务是否启动") from e

    def set(self, key: str, value: str, expire_seconds: Optional[int] = None) -> bool:
        """
        设置键值对，可选过期时间
        :param key: 缓存键
        :param value: 缓存值（字符串）
        :param expire_seconds: 过期时间，单位秒，None表示永久
        :return: 是否设置成功
        """
        try:
            self.client.set(key, value, ex=expire_seconds)
            return True
        except Exception as e:
            logger.error(f"[Redis写入] 失败，key={key}: {str(e)}")
            return False

    def get(self, key: str) -> Optional[str]:
        """
        根据键获取值
        :param key: 缓存键
        :return: 缓存值，不存在返回None
        """
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"[Redis读取] 失败，key={key}: {str(e)}")
            return None

    def delete(self, key: str) -> bool:
        """
        删除指定键
        :param key: 缓存键
        :return: 是否删除成功
        """
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"[Redis删除] 失败，key={key}: {str(e)}")
            return False

# 全局单例，供业务层直接调用
redis_client = RedisClient()






