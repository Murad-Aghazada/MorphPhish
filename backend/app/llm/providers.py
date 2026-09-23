"""LLM providers for scenario generation.

All providers share the prompt-engineering layer in `prompts.py`:
  * MockLLMProvider  — offline, deterministic template rendering (default);
  * OpenAIProvider   — GPT via the Responses API with structured JSON output;
  * AnthropicProvider — Claude via the Messages API.

Selected by settings.llm_provider (mock | openai | anthropic).
"""
from abc import ABC, abstractmethod
import json, re, time
import httpx
from app.core.config import settings
from . import prompts

_TRANSIENT = {429, 500, 502, 503, 504}


def _post_json(url, *, params=None, headers=None, json=None, timeout=40, retries=3):
    """POST returning parsed JSON, retrying transient (429/5xx) responses with backoff."""
    last = None
    for attempt in range(retries):
        with httpx.Client(timeout=timeout) as c:
            r = c.post(url, params=params, headers=headers, json=json)
        if r.status_code in _TRANSIENT and attempt < retries - 1:
            last = r
            time.sleep(1.5 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    last.raise_for_status()


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, payload: dict) -> dict: ...


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):  # strip ```json ... ``` fences
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    return json.loads(text)


def _validate_keys(data: dict) -> dict:
    missing = [k for k in prompts.SCENARIO_SCHEMA["required"] if k not in data]
    if missing:
        raise RuntimeError(f"LLM response missing keys: {', '.join(missing)}")
    return data


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
        return _validate_keys(_extract_json(text))


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
        return _validate_keys(_extract_json(text))


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
        return _validate_keys(_extract_json(text))


_PROVIDERS = {"mock": MockLLMProvider, "openai": OpenAIProvider, "anthropic": AnthropicProvider,
              "gemini": GeminiProvider, "google": GeminiProvider, "aistudio": GeminiProvider}


def get_llm_provider() -> LLMProvider:
    return _PROVIDERS.get(settings.llm_provider.lower(), MockLLMProvider)()
