import os
import time
from openai import OpenAI
from .telemetry import log_event, add_token_usage, debug_append

DEBUG = os.getenv("JARVIS_DEBUG", "0") == "1"

def _client() -> OpenAI:
    # LiteLLM proxy costuma ser OPENAI_API_BASE + OPENAI_API_KEY
    base_url = os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL") or "http://localhost:4000"
    api_key = os.getenv("OPENAI_API_KEY") or "sk-local"
    return OpenAI(base_url=base_url, api_key=api_key)

def ask_llm(
    messages: list[dict],
    model: str,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    role: str = "llm",
) -> str:

    # 🔥 FIX CRÍTICO
    # Claude thinking (model group reasoning) exige temperature = 1
    if model == "reasoning":
        temperature = 1.0

    client = _client()

    kwargs = {}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    t0 = time.time()
    res = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        **kwargs
    )
    elapsed_ms = int((time.time() - t0) * 1000)

    text = (res.choices[0].message.content or "").strip()

    # tokens
    usage = getattr(res, "usage", None)
    if usage:
        prompt = getattr(usage, "prompt_tokens", 0) or 0
        completion = getattr(usage, "completion_tokens", 0) or 0
        total = getattr(usage, "total_tokens", 0) or 0
        add_token_usage(model, prompt, completion, total)

        if DEBUG:
            print(
                f"DEBUG USAGE({model}): "
                f"prompt={prompt} completion={completion} total={total} ms={elapsed_ms}"
            )
            log_event(
                "token_usage",
                {
                    "model": model,
                    "prompt": prompt,
                    "completion": completion,
                    "total": total,
                },
            )
            debug_append("llm_calls", {
                "role": role,
                "model": model,
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "total_tokens": total,
                "ms": elapsed_ms,
            })

    return text