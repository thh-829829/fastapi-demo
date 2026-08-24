import os
import requests
from dotenv import load_dotenv
from openai import OpenAI, APIError, APIConnectionError, AuthenticationError

# 加载环境变量
load_dotenv()


class LLMClient:
    """DeepSeek大模型客户封装"""

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
                raise ValueError("DEEPSEEK_API_KEY 未配置，请在.env文件中设置")
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        return self._client


    def chat(self, user_prompt: str, temperature: float = 0.7) -> str:
        """
        单次对话调用
        :param user_prompt: 用户输入的提示词
        :param temperature: 温度参数，0-2，越低越严谨
        :return: 大模型返回的回答文本
        """
        client = self._get_client()
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=temperature
            )
            return response.choices[0].message.content.strip()

        except AuthenticationError:
            raise RuntimeError("API Key认证失败，请检查DeepSeek密钥是否正确")
        except APIConnectionError:
            raise RuntimeError("网络连接失败，无法访问DeepSeek接口")
        except APIError as e:
            raise RuntimeError(f"大模型调用出错：{str(e)}")

    def chat_with_messages(self, messages: list, temperature: float = 0.7) -> str:
        """
        支持传入完整消息列表的对话调用
        :param messages:符合OpenAI格式的消息列表，如[{"role":"system","content":"..."},{""role":"user","content":"..."}]
        :param temperature: 温度参数
        :return: 大模型返回的回答文本
        """
        client = self._get_client()
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()

        except AuthenticationError:
            raise RuntimeError("API Key认证失败，请检查DeepSeek密钥是否正确")
        except APIConnectionError:
            raise RuntimeError("网络连接失败，无法访问DeepSeek接口")
        except APIError as e:
            raise RuntimeError(f"大模型调用出错：{str(e)}")

    def get_embeddings(self, texts: list[str], model: str = "BAAI/bge-large-zh-v1.5") -> list[list[float]]:
        """
        调用 DeepSeek Embedding接口，批量生成中文文本向量
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

        response =requests.post(url, headers=headers, json=payload)
        # 接口异常时主动抛出错误，便于排查
        response.raise_for_status()
        data = response.json()

        # 按index 排序，保证返回顺序与输入文本严格一致
        sorted_data = sorted(data["data"], key=lambda item: item["index"])
        # 提取纯向量数组
        return [item["embedding"] for item in sorted_data]

# 全局单例，直接导入使用
llm_client = LLMClient()
