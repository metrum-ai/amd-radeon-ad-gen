# Created by Metrum AI for AMD

"""Local LLM provider -- uses Ollama (local /v1/chat/completions endpoint)."""

import asyncio
import logging

import httpx
from app.config import settings
from app.providers.llm.api_provider import APILLMProvider


class LocalLLMProvider(APILLMProvider):
    """Ollama exposes a /v1/chat/completions endpoint, so we reuse the
    same HTTP client logic with the local URL and model name."""

    def __init__(self) -> None:
        super().__init__()
        self._base_url = settings.local_llm_url
        self._api_key = "not-needed"  # pragma: allowlist secret
        self._model = settings.llm_model or "qwen3:8b"
        self._resolved_model_name: str | None = None

    def _resolve_model_name(self) -> str:
        """Query Ollama /api/show once to get the real model family,
        parameter size, and quantization instead of the alias."""
        if self._resolved_model_name is not None:
            return self._resolved_model_name

        ollama_base = self._base_url.replace("/v1", "")
        try:
            resp = httpx.post(
                f"{ollama_base}/api/show",
                json={"name": self._model},
                timeout=5,
            )
            if resp.status_code == 200:
                details = resp.json().get("details", {})
                family = details.get("family", "")
                param_size = details.get("parameter_size", "")
                quant = details.get("quantization_level", "")

                if family:
                    parts = [family.capitalize()]
                    if param_size:
                        parts.append(param_size)
                    if quant:
                        parts.append(quant)
                    self._resolved_model_name = " ".join(parts)
                    return self._resolved_model_name
        except Exception as exc:
            logging.getLogger(__name__).debug(
                "Ollama /api/show lookup failed, using alias: %s", exc
            )

        self._resolved_model_name = self._model
        return self._model

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict | None = None,
    ):
        result = await super().chat(
            system_prompt, user_prompt, response_format
        )
        result.model = await asyncio.to_thread(self._resolve_model_name)
        return result
