import os
import litellm
from litellm import completion
from typing import Dict, List, Any, Optional


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
            response = completion(
                model=self.get_model_name(for_ocr=True),
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

            if response and response.choices and len(response.choices) > 0:
                return {"success": True, "result": response.choices[0].message.content}
            else:
                return {"success": False, "error": "Failed to get OCR result from LLM"}

        except Exception as e:
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
            response = completion(
                model=self.get_model_name(for_ocr=False),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature,
            )

            if response and response.choices and len(response.choices) > 0:
                return {"success": True, "result": response.choices[0].message.content}
            else:
                return {
                    "success": False,
                    "error": "Failed to get response from text LLM",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}
