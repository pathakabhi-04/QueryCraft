"""One interface to both models:  generate(prompt, model) -> LLMResponse(text, latency, ...)

model is "gemini" (Google AI Studio) or "llama" (Groq or local Ollama, chosen
by LLAMA_BACKEND in .env). Exact model names come from .env.

Features needed for fair, cheap evaluation:
  * temperature / max tokens from .env (0 for all evaluation runs)
  * retry with exponential backoff on rate-limit and server errors
  * a fixed delay between real API calls (free-tier limits)
  * an on-disk cache keyed by (backend, model name, settings, prompt, run index)
    so reruns are free. The run index is part of the key, so run 1, 2 and 3 of
    a consistency experiment are genuinely separate API calls.

List the model names your keys can use:
    python -m querycraft.llm --list-models
"""

import argparse
import hashlib
import json
import time
from dataclasses import asdict, dataclass

from querycraft.config import CACHE_DIR, get_settings

MODELS = ("gemini", "llama")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

_last_call = 0.0
_clients = {}


@dataclass
class LLMResponse:
    text: str
    latency: float          # seconds for the original (uncached) call
    model: str              # "gemini" / "llama"
    model_name: str         # exact provider model id, e.g. "gemini-3.5-flash"
    backend: str            # "gemini" / "groq" / "ollama"
    cached: bool = False


class LLMError(RuntimeError):
    pass


def model_info(model: str) -> tuple[str, str]:
    """(backend, exact model name) for "gemini" or "llama"."""
    s = get_settings()
    if model == "gemini":
        return "gemini", s.gemini_model
    if model == "llama":
        return s.llama_backend, s.llama_model
    raise ValueError(f"Unknown model {model!r}; use one of {MODELS}")


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]


# ---------------------------------------------------------------- backends

def _gemini_client():
    if "gemini" not in _clients:
        from google import genai
        key = get_settings().gemini_api_key
        if not key:
            raise LLMError("GEMINI_API_KEY is not set in .env")
        _clients["gemini"] = genai.Client(api_key=key)
    return _clients["gemini"]


def _openai_client(backend: str):
    if backend not in _clients:
        from openai import OpenAI
        s = get_settings()
        if backend == "groq":
            if not s.groq_api_key:
                raise LLMError("GROQ_API_KEY is not set in .env")
            _clients[backend] = OpenAI(api_key=s.groq_api_key, base_url=GROQ_BASE_URL)
        elif backend == "ollama":
            _clients[backend] = OpenAI(api_key="ollama", base_url=s.ollama_base_url)
        else:
            raise LLMError(f"LLAMA_BACKEND must be 'groq' or 'ollama', got {backend!r}")
    return _clients[backend]


def _call_gemini(prompt: str, model_name: str, temperature: float, max_tokens: int) -> str:
    from google.genai import types
    resp = _gemini_client().models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=temperature, max_output_tokens=max_tokens),
    )
    return resp.text or ""


def _call_openai_compatible(backend: str, prompt: str, model_name: str,
                            temperature: float, max_tokens: int) -> str:
    resp = _openai_client(backend).chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


def _is_retryable(err: Exception) -> bool:
    code = getattr(err, "code", None) or getattr(err, "status_code", None)
    if isinstance(code, int) and (code == 429 or code >= 500):
        return True
    name = type(err).__name__
    return name in {"RateLimitError", "APIConnectionError", "APITimeoutError",
                    "InternalServerError", "ServerError", "ConnectionError", "TimeoutError"}


# ---------------------------------------------------------------- public API

def generate(prompt: str, model: str, use_cache: bool = True, run: int = 0) -> LLMResponse:
    global _last_call
    s = get_settings()
    backend, model_name = model_info(model)
    if not model_name:
        raise LLMError(f"No model name configured for {model!r} (set it in .env)")

    key_src = json.dumps([backend, model_name, s.temperature, s.max_output_tokens, run, prompt])
    cache_file = CACHE_DIR / f"{hashlib.sha256(key_src.encode()).hexdigest()}.json"
    if use_cache and cache_file.exists():
        data = json.loads(cache_file.read_text())
        return LLMResponse(**{**data, "cached": True})

    for attempt in range(s.max_api_retries + 1):
        wait = s.call_delay_seconds - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        start = time.monotonic()
        try:
            if backend == "gemini":
                text = _call_gemini(prompt, model_name, s.temperature, s.max_output_tokens)
            else:
                text = _call_openai_compatible(backend, prompt, model_name,
                                               s.temperature, s.max_output_tokens)
            latency = time.monotonic() - start
            _last_call = time.monotonic()
            break
        except Exception as e:  # noqa: BLE001 - provider SDKs raise many types
            _last_call = time.monotonic()
            if attempt < s.max_api_retries and _is_retryable(e):
                backoff = min(60, 2 ** attempt * 2)
                print(f"  [{model}] {type(e).__name__}; retrying in {backoff}s "
                      f"({attempt + 1}/{s.max_api_retries})")
                time.sleep(backoff)
                continue
            raise LLMError(f"{model} call failed: {type(e).__name__}: {e}") from e

    resp = LLMResponse(text=text, latency=latency, model=model,
                       model_name=model_name, backend=backend)
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data = asdict(resp)
        data.pop("cached")
        cache_file.write_text(json.dumps(data))
    return resp


def list_models() -> None:
    s = get_settings()
    if s.gemini_api_key:
        print("Gemini models (generateContent):")
        for m in _gemini_client().models.list():
            if "generateContent" in (getattr(m, "supported_actions", None) or []):
                print("  ", m.name.removeprefix("models/"))
    else:
        print("Gemini: GEMINI_API_KEY not set")
    try:
        print(f"Llama backend '{s.llama_backend}' models:")
        for m in _openai_client(s.llama_backend).models.list():
            print("  ", m.id)
    except Exception as e:  # noqa: BLE001
        print(f"  could not list: {e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="QueryCraft LLM helper")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--model", choices=MODELS, default="llama")
    ap.add_argument("--prompt", default="Reply with the single word: ready")
    args = ap.parse_args()
    if args.list_models:
        list_models()
    else:
        r = generate(args.prompt, args.model, use_cache=False)
        print(f"{r.model_name} ({r.backend}) {r.latency:.2f}s:\n{r.text}")
