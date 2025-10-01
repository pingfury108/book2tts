import logging
import os
from typing import Any, Dict, Optional

import litellm
from litellm import completion


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


# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


class LLMService:
    """Service class for handling LLM operations using litellm."""

    def __init__(
        self,
        ocr_provider: Optional[str] = None,
        text_provider: Optional[str] = None,
        ocr_model_name: Optional[str] = None,
        text_model_name: Optional[str] = None,
    ):
        """
        Initialize the LLM service with separate providers for OCR and text processing.

        Args:
            ocr_provider: The LLM provider name for OCR (default from env or "volcengine")
            text_provider: The LLM provider name for text processing (default from env or "volcengine")
            ocr_model_name: The specific model name for the OCR provider
            text_model_name: The specific model name for the text provider
        """
        # OCR provider setup
        self.ocr_provider = ocr_provider or os.environ.get("OCR_PROVIDER", "volcengine")
        self.ocr_model_name = ocr_model_name or os.environ.get(
            f"{self.ocr_provider.upper()}_OCR_MODEL", "<DEFAULT_OCR_MODEL>"
        )
        self.ocr_api_key = os.environ.get(f"{self.ocr_provider.upper()}_API_KEY")

        if not self.ocr_api_key:
            raise ValueError(
                f"{self.ocr_provider.upper()}_API_KEY environment variable not set"
            )

        # Text provider setup
        self.text_provider = text_provider or os.environ.get(
            "TEXT_PROVIDER", "volcengine"
        )
        self.text_model_name = text_model_name or os.environ.get(
            f"{self.text_provider.upper()}_TEXT_MODEL", "<DEFAULT_TEXT_MODEL>"
        )
        self.text_api_key = os.environ.get(f"{self.text_provider.upper()}_API_KEY")

        if not self.text_api_key:
            raise ValueError(
                f"{self.text_provider.upper()}_API_KEY environment variable not set"
            )

    def get_model_name(self, for_ocr: bool = True) -> str:
        """
        Get the full model name with provider and model.

        Args:
            for_ocr: Whether to get the OCR model name (True) or text model name (False)

        Returns:
            Full model name with provider and model
        """
        if for_ocr:
            return f"{self.ocr_provider}/{self.ocr_model_name}"
        else:
            return f"{self.text_provider}/{self.text_model_name}"

    def _collect_usage_info(self, response: Any) -> Optional[Dict[str, Any]]:
        usage = None
        if hasattr(response, "usage"):
            usage = response.usage
        elif isinstance(response, dict):
            usage = response.get("usage")

        if usage is None:
            return None

        if isinstance(usage, dict):
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            total_tokens = usage.get("total_tokens")
        else:
            prompt_tokens = getattr(usage, "prompt_tokens", None)
            completion_tokens = getattr(usage, "completion_tokens", None)
            total_tokens = getattr(usage, "total_tokens", None)

        if all(token is None for token in (prompt_tokens, completion_tokens, total_tokens)):
            return None

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

    def _log_token_usage(self, response: Any, context: str, fallback_model: str) -> None:
        """记录每次 LLM 调用的 token 使用情况。"""
        try:
            usage_info = self._collect_usage_info(response)

            model_name = None
            if hasattr(response, "model"):
                model_name = response.model
            elif isinstance(response, dict):
                model_name = response.get("model")

            prompt_tokens = usage_info.get("prompt_tokens") if usage_info else None
            completion_tokens = usage_info.get("completion_tokens") if usage_info else None
            total_tokens = usage_info.get("total_tokens") if usage_info else None

            logger.info(
                "LLM %s call tokens prompt=%s completion=%s total=%s model=%s",
                context,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                model_name or fallback_model,
            )
        except Exception:
            logger.debug("Failed to log LLM token usage", exc_info=True)

    def perform_ocr(self, image_data: str, temperature: float = 0.2) -> Dict[str, Any]:
        """
        Perform OCR on an image using the configured LLM.

        Args:
            image_data: Base64 encoded image data
            temperature: The temperature parameter for the LLM (default: 0.2)

        Returns:
            Dictionary containing the OCR result or error
        """
        try:
            model_name = self.get_model_name(for_ocr=True)
            response = completion(
                model=model_name,
                messages=[
                    {"role": "system", "content": ""},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": image_data},
                            },
                        ],
                    },
                ],
                temperature=temperature,
            )

            self._log_token_usage(
                response=response,
                context="OCR",
                fallback_model=model_name,
            )

            usage_info = self._collect_usage_info(response)

            if response and response.choices and len(response.choices) > 0:
                return {
                    "success": True,
                    "result": response.choices[0].message.content,
                    "usage": usage_info,
                    "model": getattr(response, "model", model_name),
                }
            else:
                return {"success": False, "error": "Failed to get OCR result from LLM"}

        except Exception as e:
            logger.error("LLM OCR call failed: %s", e, exc_info=True)
            return {"success": False, "error": str(e)}

    def process_text(
        self, system_prompt: str, user_content: str, temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Process text using the configured text LLM with given system and user prompts.

        Args:
            system_prompt: The system prompt/instructions
            user_content: The user's prompt content
            temperature: The temperature parameter for the LLM (default: 0.7)

        Returns:
            Dictionary containing the LLM response or error
        """
        try:
            model_name = self.get_model_name(for_ocr=False)
            response = completion(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature,
            )

            self._log_token_usage(
                response=response,
                context="TEXT",
                fallback_model=model_name,
            )

            usage_info = self._collect_usage_info(response)

            if response and response.choices and len(response.choices) > 0:
                return {
                    "success": True,
                    "result": response.choices[0].message.content,
                    "usage": usage_info,
                    "model": getattr(response, "model", model_name),
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to get response from text LLM",
                }

        except Exception as e:
            logger.error("LLM TEXT call failed: %s", e, exc_info=True)
            return {"success": False, "error": str(e)}
