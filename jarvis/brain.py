from openai import OpenAI
import os

client = OpenAI(
    api_key="anything",
    base_url="http://localhost:4000/v1",
)

DEBUG = os.getenv("JARVIS_DEBUG", "0") == "1"

def ask_llm(messages, model="brain", temperature=0.2):
    # ✅ Anthropic extended thinking exige temperature=1
    if model == "reasoning":
        temperature = 1

    res = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )

    # opcional: ver tokens
    if DEBUG and getattr(res, "usage", None):
        u = res.usage
        print(
            f"DEBUG USAGE({model}): prompt={u.prompt_tokens} "
            f"completion={u.completion_tokens} total={u.total_tokens}"
        )

    return res.choices[0].message.content