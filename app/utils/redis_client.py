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
        初始化Redis连接参数。

        这里不在导入阶段主动连接Redis，避免单元测试或仅使用非缓存接口时
        因为Redis未启动而阻塞应用导入。第一次真正操作Redis时再建立连接。
        :param host: Redis服务地址
        :param port: Redis服务端口
        :param db: 数据库编号
        """
        self.host = host
        self.port = port
        self.db = db
        self._client = None

    @property
    def client(self):
        """兼容原有调用方式，按需返回已连接的Redis客户端。"""
        return self._get_client()

    def _get_client(self):
        """懒加载Redis客户端，首次使用时验证连接是否可用。"""
        if self._client is None:
            try:
                client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    decode_responses=True,
                    socket_connect_timeout=3
                )
                client.ping()
                self._client = client
                logger.info("[Redis初始化] 连接成功")
            except Exception as e:
                logger.error(f"[Redis初始化] 连接失败：{str(e)}", exc_info=True)
                raise RuntimeError("Redis连接失败，请检查服务是否启动") from e
        return self._client

    def set(self, key: str, value: str, expire_seconds: Optional[int] = None) -> bool:
        """
        设置键值对，可选过期时间
        :param key: 缓存键
        :param value: 缓存值（字符串）
        :param expire_seconds: 过期时间，单位秒，None表示永久
        :return: 是否设置成功
        """
        try:
            self._get_client().set(key, value, ex=expire_seconds)
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
            return self._get_client().get(key)
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
            self._get_client().delete(key)
            return True
        except Exception as e:
            logger.error(f"[Redis删除] 失败，key={key}: {str(e)}")
            return False

    def list_append(self, key: str, value: str, expire_seconds: Optional[int] = None) -> int:
        """
        向列表尾部追加一个元素，可选设置过期时间
        :param key: 列表键
        :param value: 要追加的字符串值
        :param expire_seconds: 过期时间，单位秒，None表示不设置
        :return: 追加后列表的长度，失败返回-1
        """
        try:
            client = self._get_client()
            length = client.rpush(key, value)
            if expire_seconds is not None:
                client.expire(key, expire_seconds)
            return length
        except Exception as e:
            logger.error(f"[Redis列表追加] 失败，key={key}: {str(e)}")
            return -1

    def list_get_all(self, key: str) -> list:
        """
        获取列表所有元素（按顺序从左到右）
        :param key: 列表键
        :return: 元素列表，不存在返回空列表
        """
        try:
            result = self._get_client().lrange(key, 0, -1)
            return result if result else []
        except Exception as e:
            logger.error(f"[Redis列表读取] 失败，key={key}: {str(e)}")
            return []

    def list_len(self, key: str) -> int:
        """
        获取列表长度
        :param key: 列表键
        :return: 列表长度，失败返回0
        """
        try:
            return self._get_client().llen(key)
        except Exception as e:
            logger.error(f"[Redis列表长度] 失败，key={key}: {str(e)}")
            return 0

    def expire(self, key: str, seconds: int) -> bool:
        """
        设置键的过期时间
        :param key: 键名
        :param seconds: 过期秒数
        :return: 是否设置成功
        """
        try:
            return self._get_client().expire(key, seconds)
        except Exception as e:
            logger.error(f"[Redis设置过期] 失败，key={key}: {str(e)}")
            return False


    def exists(self, key: str) -> bool:
        """检查key是否存在"""
        return self._get_client().exists(key) > 0

    def hset(self, key: str, field: str, value: str) -> int:
        """设置哈希字段值"""
        return self._get_client().hset(key, field, value)

    def hgetall(self, key: str) -> dict:
        """获取哈希所有字段"""
        result = self._get_client().hgetall(key)
        return result if result else {}

    def zadd(self, key: str, mapping: dict) -> int:
        """添加有序集合成员，mapping={member: score}"""
        return self._get_client().zadd(key, mapping)

    def zrem(self, key: str, value: str) -> int:
        """移除有序集合成员"""
        return self._get_client().zrem(key, value)

    def zrevrange(self, key: str, start: int, end: int) -> list:
        """倒序获取有序集合成员（按score从大到小）"""
        result = self._get_client().zrevrange(key, start, end)
        return result if result else []



# 全局单例，供业务层直接调用
redis_client = RedisClient()






