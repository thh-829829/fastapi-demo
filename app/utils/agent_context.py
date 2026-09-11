import json
import time
import logging
from typing import List, Dict, Any, Optional
from app.utils.redis_client import redis_client

logger = logging.getLogger("agent-context")

# 默认会话过期时间：30分钟无交互自动清理
DEFAULT_CONTEXT_TTL = 1800
# Redis Key前缀
CONTEXT_KEY_PREFIX = "agent:context:"


class AgentContextManager:
    """
    Agent对话上下文管理器
    基于Redis List实现，支持多轮对话记忆、自动过期、会话隔离
    消息格式完全兼容DeepSeek/OpenAI标准，取出后可直接传入大模型
    """

    def __init__(self, session_id: str, ttl: int = DEFAULT_CONTEXT_TTL):
        """
        初始化上下文管理器
        :param session_id: 会话唯一ID，不同会话完全隔离
        :param ttl: 会话过期时间（秒），每次追加消息自动续期
        """
        self.session_id = session_id
        self.ttl = ttl
        self.redis_key = f"{CONTEXT_KEY_PREFIX}{session_id}"

    def init_session(self, system_prompt: str) -> bool:
        """
        初始化新会话，写入系统提示词
        如果会话已存在，会先清空再初始化
        :param system_prompt: 系统提示词
        :return: 是否成功
        """
        # 先清空已有会话
        self.clear()
        system_msg = {"role": "system", "content": system_prompt}
        return self._append_message(system_msg)

    def add_user_message(self, content: str, user_id: int = 1) -> bool:
        """
        追加用户消息
        :param content: 用户输入文本
        :param user_id: 用户ID，用于会话索引
        :return: 是否成功
        """
        msg = {"role": "user", "content": content}
        self._update_session_meta(user_id=user_id)
        return self._append_message(msg)

    def add_assistant_message(self, content: Optional[str] = None, tool_calls: Optional[List[Dict]] = None, user_id: int = 1) -> bool:
        """
        追加助手消息（支持普通回答和工具调用两种）
        :param content: 文本回答内容，无则传None
        :param tool_calls: 工具调用列表，无则传None
        :param user_id: 用户ID
        :return: 是否成功
        """
        msg = {"role": "assistant", "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self._update_session_meta(user_id=user_id)
        return self._append_message(msg)

    def add_tool_message(self, tool_call_id: str, name: str, content: str) -> bool:
        """
        追加工具执行结果消息
        :param tool_call_id: 工具调用ID，与助手返回的tool_calls.id对应
        :param name: 工具名称
        :param content: 工具执行结果字符串
        :return: 是否成功
        """
        msg = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content
        }
        return self._append_message(msg)

    def get_messages(self) -> List[Dict[str, Any]]:
        """
        获取完整对话消息列表，按时间顺序排列
        返回结果可直接传入 llm_client.chat_with_tools()
        :return: 消息列表
        """
        raw_list = redis_client.list_get_all(self.redis_key)
        messages = []
        for raw in raw_list:
            try:
                messages.append(json.loads(raw))
            except Exception as e:
                logger.warning(f"[上下文解析] 消息解析失败，跳过: {str(e)}")
                continue
        return messages

    def clear(self) -> bool:
        """
        清空当前会话消息
        :return: 是否成功
        """
        return redis_client.delete(self.redis_key)

    def message_count(self) -> int:
        """
        获取当前会话消息条数
        :return: 消息条数
        """
        return redis_client.list_len(self.redis_key)

    def _append_message(self, msg: Dict[str, Any]) -> bool:
        """
        内部方法：序列化消息并追加到列表，同时刷新TTL
        :param msg: 消息字典
        :return: 是否成功
        """
        try:
            msg_str = json.dumps(msg, ensure_ascii=False)
            length = redis_client.list_append(self.redis_key, msg_str, expire_seconds=self.ttl)
            return length > 0
        except Exception as e:
            logger.error(f"[上下文追加] 失败，session={self.session_id}: {str(e)}")
            return False

    # ========== 新增：会话管理能力 ==========
    def list_user_sessions(self, user_id: int) -> List[Dict]:
        """
        查询指定用户的所有会话列表，按最后活跃时间倒序
        """
        key = f"user:{user_id}:sessions"
        session_ids = redis_client.zrevrange(key, 0, -1)
        sessions = []
        for sid in session_ids:
            info_key = f"session:{sid}:info"
            info = redis_client.hgetall(info_key)
            if info:
                sessions.append({
                    "session_id": sid,
                    "created_at": info.get("created_at", ""),
                    "last_active_at": info.get("last_active_at", ""),
                    "message_count": int(info.get("message_count", 0))
                })
        return sessions

    def delete_session(self, user_id: int) -> bool:
        """
        删除当前会话，同时清理消息、元数据与用户索引
        """
        # 1. 删除对话消息
        redis_client.delete(self.redis_key)
        # 2. 删除会话元信息
        info_key = f"session:{self.session_id}:info"
        redis_client.delete(info_key)
        # 3. 从用户会话索引中移除
        user_key = f"user:{user_id}:sessions"
        redis_client.zrem(user_key, self.session_id)
        return True

    def get_full_history(self) -> List[Dict]:
        """
        获取当前会话的完整消息历史
        """
        return self.get_messages()

    def _update_session_meta(self, user_id: int):
        """
        更新会话元数据（创建时间、最后活跃时间、消息数）
        每次追加消息后调用
        """
        info_key = f"session:{self.session_id}:info"
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        # 不存在则初始化创建时间，并加入用户索引
        if not redis_client.exists(info_key):
            redis_client.hset(info_key, "created_at", now)
            redis_client.zadd(f"user:{user_id}:sessions", {self.session_id: time.time()})

        # 更新最后活跃时间与消息数
        redis_client.hset(info_key, "last_active_at", now)
        redis_client.hset(info_key, "message_count", self.message_count())
