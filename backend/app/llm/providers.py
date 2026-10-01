"""LLM providers for scenario generation.

All providers share the prompt-engineering layer in `prompts.py`:
  * MockLLMProvider  — offline, deterministic template rendering (default);
  * OpenAIProvider   — GPT via the Responses API with structured JSON output;
  * AnthropicProvider — Claude via the Messages API.

Selected by settings.llm_provider (mock | openai | anthropic).
"""
from abc import ABC, abstractmethod
import json, logging, re, time
import httpx
from app.core.config import settings
from . import prompts

log = logging.getLogger("app.llm")
_TRANSIENT = {429, 500, 502, 503, 504}


def _post_json(url, *, params=None, headers=None, json=None, timeout=60, retries=3):
    """POST returning parsed JSON, retrying transient failures (429/5xx and
    read timeouts, e.g. serverless cold starts) with backoff."""
    last = None
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=timeout) as c:
                r = c.post(url, params=params, headers=headers, json=json)
        except httpx.TimeoutException as e:
            last = e
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
        if r.status_code in _TRANSIENT and attempt < retries - 1:
            last = r
            time.sleep(1.5 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    if isinstance(last, httpx.Response):
        last.raise_for_status()
    raise last


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, payload: dict) -> dict: ...


def _extract_json(text: str) -> dict:
    """Best-effort parse of a model's text into a dict. Returns {} instead of
    raising so a malformed content response degrades to the template baseline
    (see _coerce_scenario) rather than surfacing as a 500/503."""
    text = (text or "").strip()
    if text.startswith("```"):  # strip ```json ... ``` fences
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)  # salvage the first {...} block
        if not m:
            return {}
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}


# Scenario fields that must be non-empty strings.
_STR_FIELDS = ("subject", "email_body", "pretext", "landing_page_message", "training_objective", "difficulty")


def _coerce_scenario(raw: dict, payload: dict) -> dict:
    """Merge a real LLM response onto the deterministic template so the result
    is ALWAYS schema-valid. Any field the model omitted or returned with the
    wrong type falls back to the template, which prevents a flaky model response
    (missing keys, a list where an object was expected, prose instead of JSON)
    from surfacing as an opaque 500/503. Safety-critical landing text is still
    re-enforced downstream by generate_scenario regardless of what we keep here."""
    base = prompts.render_scenario(payload)
    if not isinstance(raw, dict):
        raw = {}
    # Unwrap a single-key envelope like {"scenario": {...}}.
    if raw and not any(k in raw for k in base) and len(raw) == 1:
        inner = next(iter(raw.values()))
        if isinstance(inner, dict):
            raw = inner
    out = dict(base)
    kept = []
    for k in _STR_FIELDS:
        v = raw.get(k)
        if isinstance(v, str) and v.strip():
            out[k] = v.strip()
            kept.append(k)
    if out.get("difficulty") not in prompts.DIFFICULTIES:
        out["difficulty"] = base["difficulty"]
    ri = raw.get("risk_indicators")
    if isinstance(ri, str):
        inds = [ri.strip()] if ri.strip() else []
    elif isinstance(ri, dict):
        inds = [str(x).strip() for x in ri.values() if str(x).strip()]
    elif isinstance(ri, list):
        inds = [str(x).strip() for x in ri if str(x).strip()]
    else:
        inds = []
    if inds:
        out["risk_indicators"] = inds
        kept.append("risk_indicators")
    if len(kept) < 3:
        log.warning("LLM response was sparse/malformed; filled most fields from template (kept: %s)", kept or "none")
    return out


class MockLLMProvider(LLMProvider):
    def generate(self, payload):
        return prompts.render_scenario(payload)


class OpenAIProvider(LLMProvider):
    def generate(self, payload):
        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is not configured")
        system, user = prompts.build_prompt(payload)
        body = {
            "model": settings.llm_model,
            "max_output_tokens": settings.llm_max_tokens,
            "input": [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
            "text": {"format": {"type": "json_schema", "name": "scenario", "strict": True, "schema": prompts.SCENARIO_SCHEMA}},
        }
        try:
            data = _post_json(settings.openai_base_url.rstrip("/") + "/responses",
                              headers={"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}, json=body)
        except httpx.HTTPError as e:
            raise RuntimeError(f"OpenAI request failed: {e}")
        text = "".join(x.get("text", "") for item in data.get("output", []) for x in item.get("content", []) if x.get("type") == "output_text")
        return _coerce_scenario(_extract_json(text), payload)


class AnthropicProvider(LLMProvider):
    def generate(self, payload):
        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is not configured")
        system, user = prompts.build_prompt(payload)
        body = {
            "model": settings.llm_model,
            "max_tokens": settings.llm_max_tokens,
            "system": system + " Respond with the JSON object only, no prose or code fences.",
            "messages": [{"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
        }
        try:
            data = _post_json(settings.anthropic_base_url.rstrip("/") + "/v1/messages",
                              headers={"x-api-key": settings.llm_api_key, "anthropic-version": settings.anthropic_version, "Content-Type": "application/json"}, json=body)
        except httpx.HTTPError as e:
            raise RuntimeError(f"Anthropic request failed: {e}")
        text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
        return _coerce_scenario(_extract_json(text), payload)


class GeminiProvider(LLMProvider):
    """Google AI Studio / Gemini via the Generative Language API (generateContent).

    Works with a free AI Studio key. The key is passed as a query parameter and
    JSON output is forced with responseMimeType. Set LLM_MODEL to a Gemini model
    such as gemini-2.0-flash or gemini-1.5-flash.
    """
    def generate(self, payload):
        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is not configured")
        system, user = prompts.build_prompt(payload)
        body = {
            "system_instruction": {"parts": [{"text": system + " Respond with the JSON object only."}]},
            "contents": [{"role": "user", "parts": [{"text": json.dumps(user, ensure_ascii=False)}]}],
            "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": settings.llm_max_tokens, "temperature": 0.7},
        }
        url = settings.gemini_base_url.rstrip("/") + f"/v1beta/models/{settings.llm_model}:generateContent"
        try:
            data = _post_json(url, params={"key": settings.llm_api_key}, headers={"Content-Type": "application/json"}, json=body)
        except httpx.HTTPError as e:
            raise RuntimeError(f"Gemini request failed: {e}")
        text = "".join(p.get("text", "") for cand in data.get("candidates", []) for p in cand.get("content", {}).get("parts", []))
        return _coerce_scenario(_extract_json(text), payload)


class NvidiaProvider(LLMProvider):
    """NVIDIA NIM (integrate.api.nvidia.com) via the OpenAI-compatible Chat
    Completions API. The same provider works for other OpenAI-compatible chat
    endpoints by overriding NVIDIA_BASE_URL. Set LLM_MODEL to a catalog model
    such as meta/llama-3.1-8b-instruct. Non-streaming JSON output."""
    def generate(self, payload):
        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is not configured")
        system, user = prompts.build_prompt(payload)
        body = {
            "model": settings.llm_model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
            "max_tokens": settings.llm_max_tokens,
            "temperature": 0.7,
            "stream": False,
            "response_format": {"type": "json_object"},
        }
        try:
            data = _post_json(settings.nvidia_base_url.rstrip("/") + "/chat/completions",
                              headers={"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}, json=body, timeout=120)
        except httpx.HTTPError as e:
            raise RuntimeError(f"NVIDIA request failed: {e}")
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        return _coerce_scenario(_extract_json(text), payload)


_PROVIDERS = {"mock": MockLLMProvider, "openai": OpenAIProvider, "anthropic": AnthropicProvider,
              "gemini": GeminiProvider, "google": GeminiProvider, "aistudio": GeminiProvider,
              "nvidia": NvidiaProvider, "nim": NvidiaProvider}


def get_llm_provider() -> LLMProvider:
    return _PROVIDERS.get(settings.llm_provider.lower(), MockLLMProvider)()
