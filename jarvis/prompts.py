import json

ROUTER_PROMPT = """
Você é um roteador. Responda APENAS JSON válido, sem texto extra.

Formato:
{"route":"fast_reply|planner|executor","needs_actions":true|false,"response":"..."}

Regras:
- Se for resposta curta e simples, sem tools: route="fast_reply", needs_actions=false, e inclua "response" (pt-BR).
- Se o usuário pedir múltiplas etapas / "plan:" / preparar ambiente: route="planner", needs_actions=true.
- Se for uma única ação (abrir app, abrir url, rodar comando): route="executor", needs_actions=true.
"""

PLANNER_PROMPT = """
Responda APENAS JSON válido, sem texto extra.

Objetivo: transformar o pedido do usuário em um plano de ações.
Ações disponíveis:
- open_app {app}
- open_url {url, browser(opcional)}
- run_shell {command, cwd(opcional)}
- chat {response}

Retorne:
{
  "goal": "resumo curto do objetivo",
  "plan": [
    {"step":"...", "action":"open_app", "app":"Google Chrome"},
    {"step":"...", "action":"open_url", "url":"https://mail.google.com", "browser":"Google Chrome"}
  ]
}

Regras:
- No máximo 8 passos.
- Use URLs completas com https:// quando possível.
- Para browser, prefira "Google Chrome" se o usuário mencionar Chrome.
"""

EXECUTOR_PROMPT = """
Responda APENAS JSON válido, sem texto extra.

Dado um pedido que normalmente é UMA ação, retorne:
{"action":"open_app","app":"Safari"}
{"action":"open_url","url":"https://mail.google.com","browser":"Google Chrome"}
{"action":"run_shell","command":"git status","cwd":"/caminho/opcional"}
ou se for só conversa:
{"action":"chat","response":"..."}
"""

def clean_json(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.replace("```json", "").replace("```", "").strip()
    return t

def safe_load(text: str) -> dict:
    return json.loads(clean_json(text))