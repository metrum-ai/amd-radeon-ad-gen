# Created by Metrum AI for AMD

"""Phase 1 LLM: OpenClaw with parse/structure validation, then direct Ollama.

When ``APP_LLM_PROVIDER_MODE=openclaw``, we try up to 3 times per section. If
the response is not valid JSON with the required shape, we call the local
Ollama provider once (no response_format) as a last resort.
"""

import logging
from collections.abc import Callable

from app.config import settings
from app.providers.base import LLMResult
from app.providers.factory import get_llm_provider, get_local_llm_provider
from app.workers.tasks.utils import run_async


def _llm_effective_mode() -> str:
    return settings.llm_provider_mode or settings.provider_mode


log = logging.getLogger(__name__)

OPENCLAW_MAX_ATTEMPTS = 3


def _is_bad_data(data: object) -> bool:
    if not isinstance(data, dict):
        return True
    if "raw_text" in data:
        return True
    return False


def validate_strategy_result(result: LLMResult) -> bool:
    if _is_bad_data(result.data):
        return False
    d = result.data
    if not str(d.get("campaign_direction") or "").strip():
        return False
    if len(d.get("audience_segments") or []) < 3:
        return False
    if len(d.get("messaging_angles") or []) < 3:
        return False
    tr = d.get("track_recommendations")
    if not isinstance(tr, dict) or not tr:
        return False
    return True


def validate_copy_result(result: LLMResult) -> bool:
    if _is_bad_data(result.data):
        return False
    variants = result.data.get("copy_variants") or []
    got: set[str] = set()
    for v in variants:
        if not isinstance(v, dict):
            return False
        if not (
            str(v.get("headline", "")).strip()
            and str(v.get("body", "")).strip()
            and str(v.get("cta", "")).strip()
        ):
            return False
        fw = v.get("framework")
        if isinstance(fw, str):
            got.add(fw)
    return required_frameworks_ok(got) and len(variants) >= 3


def required_frameworks_ok(frameworks: set) -> bool:
    return {"AIDA", "PAS", "BAB"}.issubset(frameworks)


def validate_scene_result(result: LLMResult) -> bool:
    if _is_bad_data(result.data):
        return False
    scenes = result.data.get("scene_prompts") or []
    if len(scenes) < 3:
        return False
    for s in scenes:
        if not isinstance(s, dict):
            return False
        if s.get("scene_type") not in ("primary", "lifestyle", "mood"):
            return False
        if not str(s.get("image_prompt") or "").strip():
            return False
    return True


def validate_audio_result(result: LLMResult) -> bool:
    if _is_bad_data(result.data):
        return False
    scripts = result.data.get("audio_scripts") or []
    if len(scripts) < 2:
        return False
    for s in scripts:
        if not isinstance(s, dict):
            return False
        if not str(s.get("script") or "").strip():
            return False
        if not str(s.get("tone") or "").strip():
            return False
    return True


def _stamp_fallback_model(res: LLMResult) -> LLMResult:
    m = settings.llm_model or "qwen3:8b"
    res.model = f"Ollama (direct fallback) / {m}"
    return res


def run_openclaw_then_direct_llm(
    system_prompt: str,
    user_prompt: str,
    response_format: dict,
    validate: Callable[[LLMResult], bool],
) -> LLMResult:
    """
    - If not in openclaw mode, single call with configured provider (no loop).
    - If openclaw: up to OPENCLAW_MAX_ATTEMPTS to OpenClaw, then one direct
      Ollama call without response_format.
    """
    if _llm_effective_mode() != "openclaw":
        p = get_llm_provider()
        return run_async(p.chat(system_prompt, user_prompt, response_format))

    oc = get_llm_provider()
    last_exc: BaseException | None = None
    for attempt in range(1, OPENCLAW_MAX_ATTEMPTS + 1):
        try:
            res = run_async(
                oc.chat(system_prompt, user_prompt, response_format)
            )
            if validate(res):
                return res
            log.warning(
                "OpenClaw returned invalid structure (attempt %d/%d)",
                attempt,
                OPENCLAW_MAX_ATTEMPTS,
            )
        except Exception as exc:
            last_exc = exc
            log.warning(
                "OpenClaw call failed (attempt %d/%d): %s",
                attempt,
                OPENCLAW_MAX_ATTEMPTS,
                exc,
            )

    local = get_local_llm_provider()
    log.error(
        "OpenClaw failed %d times; using direct Ollama fallback for this section",
        OPENCLAW_MAX_ATTEMPTS,
    )
    try:
        res = run_async(local.chat(system_prompt, user_prompt, None))
    except Exception:
        if last_exc:
            raise last_exc from None
        raise
    if not validate(res):
        if last_exc:
            raise last_exc
        raise ValueError(
            "Direct Ollama fallback also returned invalid structure"
        )
    return _stamp_fallback_model(res)
