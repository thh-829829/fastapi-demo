import os
import requests
import logging
from dotenv import load_dotenv
from openai import OpenAI, APIError, APIConnectionError, AuthenticationError

logger = logging.getLogger("llm-client")
# 加载环境变量
load_dotenv()


class LLMClient:
    """DeepSeek大模型客户端封装"""

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com"
        # 硅基流动 Embedding 配置
        self.embedding_api_key = os.getenv("SILICONFLOW_API_KEY")
        self.embedding_base_url = os.getenv("SILICONFLOW_BASE_URL")
        self.model = "deepseek-chat"
        self._client = None

    def _get_client(self) -> OpenAI:
        """懒加载初始化客户端"""
        if self._client is None:
            if not self.api_key:
                logger.error("DEEPSEEK_API_KEY 未配置，请在.env文件中设置")
                raise RuntimeError("DEEPSEEK_API_KEY 未配置，请在.env文件中设置")
            logger.info("初始化DeepSeek大模型客户端")
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        return self._client

    def chat(self, user_prompt: str, temperature: float | int = 0.7) -> str:
        """
        单次对话调用
        :param user_prompt: 用户输入的提示词
        :param temperature: 温度参数，0‑2，越低越严谨
        :return: 大模型返回的回答文本
        """
        client = self._get_client()
        try:
            logger.info(f"[LLM chat] 发起单轮调用，temperature={temperature}, prompt长度：{len(user_prompt)}")
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=temperature
            )
            answer = response.choices[0].message.content.strip()
            logger.info(f"[LLM chat] 调用成功，返回回答长度：{len(answer)}")
            return answer

        except AuthenticationError:
            logger.error("[LLM chat] API Key认证失败，请检查DeepSeek密钥是否正确")
            raise RuntimeError("API Key认证失败，请检查DeepSeek密钥是否正确")
        except APIConnectionError:
            logger.error("[LLM chat] 网络连接失败，无法访问DeepSeek接口")
            raise RuntimeError("网络连接失败，无法访问DeepSeek接口")
        except APIError as e:
            logger.error(f"[LLM chat]大模型调用出错: {str(e)}", exc_info=True)
            raise RuntimeError(f"大模型调用出错：{str(e)}")

    def chat_with_messages(self, messages: list, temperature: float | int = 0.7) -> str:
        """
        支持传入完整消息列表的对话调用
        :param messages: 符合OpenAI格式的消息列表，如[{"role":"system","content":"..."},{"role":"user","content":"..."}]
        :param temperature: 温度参数
        :return: 大模型返回的回答文本
        """
        client = self._get_client()
        try:
            logger.info(f"[LLM chat_with_messages]发起多轮调用，消息条数：{len(messages)}, temperature={temperature}")
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            answer = response.choices[0].message.content.strip()
            logger.info(f"[LLM chat_with_messages]调用成功，返回回答长度：{len(answer)}")
            return answer

        except AuthenticationError:
            logger.error("[LLM chat_with_messages] API Key认证失败，请检查DeepSeek密钥是否正确")
            raise RuntimeError("API Key认证失败，请检查DeepSeek密钥是否正确")
        except APIConnectionError:
            logger.error("[LLM chat_with_messages] 网络连接失败，无法访问DeepSeek接口")
            raise RuntimeError("网络连接失败，无法访问DeepSeek接口")
        except APIError as e:
            logger.error(f"[LLM chat_with_messages]大模型调用出错: {str(e)}", exc_info=True)
            raise RuntimeError(f"大模型调用出错：{str(e)}")

    def stream_chat_with_messages(self, messages: list, temperature: float | int = 0.3):
        """
        流式调用大模型，逐字返回文本片段
        :param messages: 符合OpenAI格式的消息列表
        :param temperature: 温度参数
        :return: 生成器，逐字yield文本内容
        """
        client = self._get_client()
        try:
            logger.info(f"[LLM stream] 发起流式调用，消息条数：{len(messages)}, temperature={temperature}")
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True  # 开启流式响应
            )

            for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
            logger.info("[LLM stream] 流式调用完成")

        except AuthenticationError:
            logger.error("[LLM stream] API Key认证失败，请检查DeepSeek密钥是否正确")
            raise RuntimeError("API Key认证失败，请检查DeepSeek密钥是否正确")
        except APIConnectionError:
            logger.error("[LLM stream] 网络连接失败，无法访问DeepSeek接口")
            raise RuntimeError("网络连接失败，无法访问DeepSeek接口")
        except APIError as e:
            logger.error(f"[LLM stream] 大模型流式调用出错: {str(e)}", exc_info=True)
            raise RuntimeError(f"大模型调用出错：{str(e)}")


    def chat_with_tools(self, messages: list, tools: list, temperature: float | int = 0.7):
        """
        支持工具调用的对话
        :param messages: 消息列表
        :param tools: 工具定义列表，符合OpenAI Function Calling格式
        :param temperature: 温度参数
        :return: 模型响应消息对象，包含内容或 tool_calls
        """
        client = self._get_client()
        try:
            logger.info(f"[LLM chat_with_tools] 发起工具调用，消息条数：{len(messages)}，工具数量：{len(tools)}")
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=temperature
            )
            logger.info("[LLM chat_with_tools] 调用成功")
            return response.choices[0].message
        except AuthenticationError:
            logger.error("[LLM chat_with_tools] API Key认证失败，请检查DeepSeek密钥是否正确")
            raise RuntimeError("API Key认证失败，请检查DeepSeek密钥是否正确")
        except APIConnectionError:
            logger.error("[LLM chat_with_tools] 网络连接失败，无法访问DeepSeek接口")
            raise RuntimeError("网络连接失败，无法访问DeepSeek接口")
        except APIError as e:
            logger.error(f"[LLM chat_with_tools]大模型调用出错：{str(e)}", exc_info=True)
            raise RuntimeError(f"大模型调用出错：{str(e)}")


    def get_embeddings(self, texts: list[str], model: str = "BAAI/bge-large-zh-v1.5") -> list[list[float | int]]:
        """
        调用 Embedding接口，批量生成中文文本向量
        :param texts: 待向量化的文本列表，支持批量传入
        :param model: Embedding模型名称，默认使用 BGE 中文大模型
        :return: 向量列表，顺序与输入文本一一对应
        """
        url = f"{self.embedding_base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.embedding_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "input": texts
        }
        try:
            logger.info(f"[Embedding]发起向量化，文本数量：{len(texts)}，model={model}")
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            # 按index 排序，保证返回顺序与输入文本严格一致
            sorted_data = sorted(data["data"], key=lambda item: item["index"])
            result = [item["embedding"] for item in sorted_data]
            logger.info(f"[Embedding]向量化成功，生成向量数量：{len(result)}")
            return result
        except Exception as e:
            logger.error(f"[Embedding]向量化接口调用失败：{str(e)}", exc_info=True)
            raise RuntimeError(f"文本向量化失败：{str(e)}") from e


# 全局单例，直接导入使用
llm_client = LLMClient()
