# Created by Metrum AI for AMD

import json
import re
import time

import httpx
from app.config import settings
from app.providers.base import LLMProvider, LLMResult


def _repair_json(text: str) -> str:
    """Fix common LLM JSON errors: unclosed braces, trailing commas,
    unclosed objects inside arrays."""
    # Remove trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # Fix unclosed objects before array close: ..."value"\n  ]
    # becomes ..."value"}\n  ]
    text = re.sub(
        r'("[^"]*")\s*\n(\s*\])',
        lambda m: m.group(1) + "}\n" + m.group(2)
        if _needs_object_close(text, m.start())
        else m.group(0),
        text,
    )

    # Final pass: count remaining unmatched openers
    stack = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch in ("}", "]"):
            if stack and stack[-1] == ch:
                stack.pop()

    if stack:
        text = text.rstrip()
        for closer in reversed(stack):
            text += closer

    return text


def _needs_object_close(text: str, pos: int) -> bool:
    """Check if position is inside an unclosed { within an array."""
    depth = 0
    in_str = False
    esc = False
    for i in range(pos):
        ch = text[i]
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
    return depth > 0


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response that may contain thinking
    blocks, markdown fences, or malformed JSON."""
    import logging

    log = logging.getLogger(__name__)

    # Strip Qwen3 <think>...</think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    candidates = []

    # Direct parse
    candidates.append(text)

    # Markdown code fence
    fence_match = re.search(
        r"```(?:json)?\s*\n?(.*?)```",
        text,
        re.DOTALL,
    )
    if fence_match:
        candidates.append(fence_match.group(1).strip())

    # First { ... } block (greedy)
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        candidates.append(brace_match.group(0))

    for candidate in candidates:
        # Try raw first
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        # Try with repair
        try:
            repaired = _repair_json(candidate)
            result = json.loads(repaired)
            log.debug("JSON repaired successfully")
            return result
        except json.JSONDecodeError:
            continue

    log.warning(
        "Failed to parse JSON from LLM response (%d chars)",
        len(text),
    )
    return {"raw_text": text}


class APILLMProvider(LLMProvider):
    """Chat-completions provider for any /v1/chat/completions endpoint."""

    def __init__(self) -> None:
        self._base_url = settings.llm_base_url.rstrip("/")
        self._api_key = settings.llm_api_key
        self._model = settings.llm_model

    def _extra_headers(self) -> dict:
        """Override in subclasses to inject additional HTTP headers."""
        return {}

    def _underlying_model(self) -> str:
        """The actual LLM model name, used for prompt adjustments like /no_think.
        Subclasses may override when the model sent in the payload differs
        from the real model running inference (e.g. OpenClaw gateway)."""
        return self._model

    def _supports_response_format(self) -> bool:
        """Whether the upstream supports OpenAI-style response_format."""
        return False

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict | None = None,
    ) -> LLMResult:
        sys_content = system_prompt
        if "qwen3" in self._underlying_model().lower():
            sys_content += "\n\n/no_think"

        payload: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": sys_content},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
            "max_tokens": 2048,
        }
        if response_format is not None and self._supports_response_format():
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            **self._extra_headers(),
        }

        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()

        latency_ms = int((time.monotonic() - t0) * 1000)
        raw = resp.json()

        content = raw["choices"][0]["message"]["content"]
        usage = raw.get("usage", {})

        data = _extract_json(content)

        return LLMResult(
            data=data,
            raw_request=payload,
            raw_response=raw,
            model=raw.get("model", self._model),
            tokens_used=usage.get("total_tokens"),
            latency_ms=latency_ms,
        )
