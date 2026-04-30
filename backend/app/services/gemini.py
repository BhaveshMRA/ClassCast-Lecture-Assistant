"""
OpenRouter client wrapper (OpenAI-compatible API).

OpenRouter provides access to many models (Gemini, Claude, Llama, etc.)
through a single OpenAI-compatible endpoint.

Two model handles:
- flash: fast, cheap/free; used for concept extraction and summaries
- pro:   higher quality; used for visual HTML generation
"""

import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class GeminiService:
    """
    Name kept as GeminiService so no other file needs changing.
    Internally calls OpenRouter instead of Google's SDK.
    """
    _client = None

    @classmethod
    def _ensure_configured(cls):
        if not settings.openrouter_api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY not set. Add it to your .env file. "
                "Get one at https://openrouter.ai/keys"
            )
        if cls._client is None:
            from openai import AsyncOpenAI

            cls._client = AsyncOpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=settings.openrouter_api_key,
            )
            logger.info(
                f"OpenRouter configured: "
                f"flash={settings.openrouter_flash_model}, "
                f"pro={settings.openrouter_pro_model}"
            )

    @classmethod
    def _model_name(cls, model: str) -> str:
        """Resolve 'flash' / 'pro' aliases to full OpenRouter model IDs."""
        if model == "flash":
            return settings.openrouter_flash_model
        if model == "pro":
            return settings.openrouter_pro_model
        return model  # allow passing a full model ID directly

    @classmethod
    async def generate(
        cls,
        model: str,
        prompt: str,
        json_mode: bool = False,
        max_output_tokens: int = 2048,
    ) -> str:
        """Generate text. `model` is 'flash' or 'pro'."""
        cls._ensure_configured()
        model_id = cls._model_name(model)

        kwargs = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_output_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await cls._client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.exception(f"OpenRouter error ({model_id}): {e}")
            raise

    @classmethod
    async def generate_json(cls, model: str, prompt: str) -> dict:
        """Generate and parse JSON. Returns {} on parse failure."""
        text = await cls.generate(model, prompt, json_mode=True)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed: {e}; raw response: {text[:300]}")
            return {}
