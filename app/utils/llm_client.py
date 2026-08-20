import os
from dotenv import load_dotenv
from openai import OpenAI, APIError, APIConnectionError, AuthenticationError

# 加载环境变量
load_dotenv()


class LLMClient:
    """DeepSeek大模型客户封装"""

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com"
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


# 全局单例，直接导入使用
llm_client = LLMClient()
