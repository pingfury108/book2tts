"""LLM 文本处理服务（OpenAI 兼容接口，直连 openai SDK）。

通过环境变量配置任意 OpenAI 兼容供应商：
    TEXT_PROVIDER     供应商名，用于拼接环境变量前缀，例如 deepseek
    <PROVIDER>_API_KEY          该供应商的 API Key
    <PROVIDER>_BASE_URL         OpenAI 兼容端点（默认 https://api.deepseek.com/v1）
    <PROVIDER>_TEXT_MODEL       模型名
"""

import logging
import os
from typing import Any, Dict, Optional

from openai import OpenAI

logger = logging.getLogger("book2tts.llm")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

DEFAULT_BASE_URL = "https://api.deepseek.com/v1"


class LLMService:
    """基于 OpenAI 兼容接口的 LLM 服务（文本处理）。"""

    def __init__(
        self,
        text_provider: Optional[str] = None,
        text_model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.text_provider = text_provider or os.environ.get(
            "TEXT_PROVIDER", "deepseek"
        )
        prefix = self.text_provider.upper()

        self.text_model_name = (
            text_model_name
            or os.environ.get(f"{prefix}_TEXT_MODEL")
            or os.environ.get("TEXT_MODEL")
        )
        self.base_url = (
            base_url
            or os.environ.get(f"{prefix}_BASE_URL")
            or os.environ.get("OPENAI_BASE_URL")
            or DEFAULT_BASE_URL
        )
        self.api_key = (
            api_key
            or os.environ.get(f"{prefix}_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
        )

        if not self.api_key:
            raise ValueError(f"{prefix}_API_KEY environment variable not set")
        if not self.text_model_name:
            raise ValueError(f"{prefix}_TEXT_MODEL environment variable not set")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def get_model_name(self) -> str:
        return self.text_model_name

    def _log_token_usage(self, response: Any, context: str) -> Optional[Dict[str, Any]]:
        usage = getattr(response, "usage", None)
        if usage is None:
            return None

        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)
        model_name = getattr(response, "model", None) or self.text_model_name

        logger.info(
            "LLM %s call tokens prompt=%s completion=%s total=%s model=%s",
            context,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            model_name,
        )
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

    def process_text(
        self, system_prompt: str, user_content: str, temperature: float = 0.7
    ) -> Dict[str, Any]:
        """用配置的 OpenAI 兼容模型处理文本。"""
        try:
            response = self.client.chat.completions.create(
                model=self.text_model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature,
            )

            usage_info = self._log_token_usage(response, "TEXT")

            if response and response.choices:
                return {
                    "success": True,
                    "result": response.choices[0].message.content,
                    "usage": usage_info,
                    "model": getattr(response, "model", self.text_model_name),
                }
            return {"success": False, "error": "Failed to get response from text LLM"}

        except Exception as e:
            logger.error("LLM TEXT call failed: %s", e, exc_info=True)
            return {"success": False, "error": str(e)}
