# Created by Metrum AI for AMD

"""OpenClaw LLM provider -- routes chat completions through the OpenClaw
gateway, which forwards to the configured local Ollama instance."""

from app.config import settings
from app.providers.llm.api_provider import APILLMProvider


class OpenClawLLMProvider(APILLMProvider):
    """Sends chat-completion requests to the OpenClaw gateway's
    OpenAI-compatible /v1/chat/completions endpoint.

    OpenClaw sits between this provider and Ollama, so the request path
    becomes:  Backend -> OpenClaw Gateway -> Ollama -> response.

    All JSON extraction / repair logic in APILLMProvider applies unchanged
    because the response format is the same OpenAI-compatible structure.
    """

    def __init__(self) -> None:
        super().__init__()
        self._base_url = settings.openclaw_gateway_url.rstrip("/")
        self._api_key = settings.openclaw_api_key or "not-needed"
        # OpenClaw treats the OpenAI "model" field as an agent target.
        # Be explicit so we avoid config/default routing surprises.
        self._model = f"openclaw/{settings.openclaw_agent_id or 'main'}"
        self._agent_id = settings.openclaw_agent_id
        self._real_model = settings.llm_model or "qwen3:8b"

    def _extra_headers(self) -> dict:
        # Force the backend model and isolate sessions so OpenClaw behaves
        # as a thin chat gateway instead of a stateful agent.
        #
        # - x-openclaw-model: override the backend model used by the agent
        # - x-openclaw-agent-id: compatibility override (kept)
        # - x-openclaw-session-key: prevents cross-request “agent memory”
        import uuid

        return {
            "x-openclaw-agent-id": self._agent_id,
            "x-openclaw-model": f"ollama/{self._real_model}",
            "x-openclaw-session-key": f"adgen:{uuid.uuid4()}",
        }

    def _underlying_model(self) -> str:
        return self._real_model

    def _supports_response_format(self) -> bool:
        return True

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict | None = None,
    ):
        # Retries, validation, and direct Ollama fallback for bad JSON/structure
        # are handled in ``app.services.phase1_llm`` for Phase 1 tasks.
        result = await super().chat(
            system_prompt, user_prompt, response_format
        )
        result.model = f"OpenClaw / {self._real_model}"
        return result
