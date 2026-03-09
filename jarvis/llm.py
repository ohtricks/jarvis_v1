import os
import time
from functools import lru_cache
from openai import OpenAI, APIConnectionError, APITimeoutError, APIStatusError
from .telemetry import log_event, add_token_usage, debug_append, debug_set

DEBUG = os.getenv("JARVIS_DEBUG", "0") == "1"

# Timeout padrão por chamada LLM (segundos). Evita que o agente trave indefinidamente.
_LLM_TIMEOUT = float(os.getenv("JARVIS_LLM_TIMEOUT", "60"))
# Número máximo de retries em caso de erro transitório.
_LLM_MAX_RETRIES = int(os.getenv("JARVIS_LLM_RETRIES", "2"))


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    """Cliente OpenAI cacheado — criado uma vez e reutilizado em todas as chamadas."""
    base_url = os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL") or "http://localhost:4000"
    api_key = os.getenv("OPENAI_API_KEY") or "sk-local"
    return OpenAI(base_url=base_url, api_key=api_key, timeout=_LLM_TIMEOUT)


def ask_llm(
    messages: list[dict],
    model: str,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    role: str = "llm",
) -> str:

    # Claude thinking (model group reasoning) exige temperature = 1
    if model == "reasoning":
        temperature = 1.0

    client = _client()

    kwargs = {}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    t0 = time.time()
    for attempt in range(_LLM_MAX_RETRIES + 1):
        try:
            res = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                **kwargs
            )
            break  # sucesso
        except (APIConnectionError, APITimeoutError) as e:
            if attempt < _LLM_MAX_RETRIES:
                wait = 2 ** attempt  # backoff: 1s, 2s
                if DEBUG:
                    debug_set("llm_retry", {"attempt": attempt + 1, "wait_s": wait, "error": str(e)})
                time.sleep(wait)
            else:
                raise RuntimeError(
                    f"LLM indisponível após {_LLM_MAX_RETRIES + 1} tentativas: {e}"
                ) from e
        except APIStatusError as e:
            # Erros do servidor (rate limit 429, 500, etc.) — sem retry automático
            raise RuntimeError(f"Erro da API LLM (HTTP {e.status_code}): {e.message}") from e

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