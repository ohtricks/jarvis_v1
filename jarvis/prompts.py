import json

ROUTER_PROMPT = """
Você é um roteador. Responda APENAS JSON válido, sem texto extra.

Formato:
{"route":"fast_reply|planner|executor","needs_actions":true|false,"executor_model":"fast|brain","response":"..."}

Regras:
- fast_reply: perguntas, explicações, conversa sem executar ações. needs_actions=false, inclua "response" em pt-BR.
- executor + executor_model="fast":
    • abrir apps/urls, rodar comandos diretos.
    • pode ter 2-3 ações simples conectadas por "e"/"depois" (open_app, open_url, run_shell simples).
    • git workflow (status/add/commit/push) sem análise de código → executor+fast.
    • exemplos: "abra o chrome", "abra o chrome e o youtube", "rode git status e depois git diff", "commite com mensagem X", "commite e suba".
- executor + executor_model="brain":
    • envolve objetivo semântico/contextual: "me fale", "resuma", "liste", "extraia", "compare", "o que chegou".
    • exemplos: "abra o gmail e me fale os assuntos dos emails de hoje".
- planner:
    • revisão/análise de código, refatoração, arquitetura, implementação, "faça um plano", "pesquise", "implemente X".
    • tarefas de decomposição real com muitos passos ou decisões encadeadas.
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
{"action":"run_shell","command":"ls -la","cwd":"/caminho/opcional"}
{"action":"git_status"}
{"action":"git_add_all"}
{"action":"git_commit","message":"fix shell_policy"}
{"action":"git_push","remote":"origin","branch":"main"}
ou se for só conversa:
{"action":"chat","response":"..."}
"""

ACTION_COMPILER_PROMPT = """
Responda APENAS JSON válido, sem texto extra.

Ações disponíveis:
- open_app {app}
- open_url {url, browser?}
- run_shell {command, cwd?}
- git_status {cwd?}
- git_add_all {cwd?}
- git_commit {message, cwd?}
- git_push {remote?, branch?}
- chat {response}

Retorne UMA das formas:

A) Ação única:
{"action":"open_app","app":"Google Chrome"}

B) Plano com 2-4 passos (quando houver múltiplas ações diretas):
{"goal":"abrir chrome e youtube","plan":[
  {"step":"Abrir Chrome","action":"open_app","app":"Google Chrome"},
  {"step":"Abrir YouTube","action":"open_url","url":"https://youtube.com"}
]}

C) Chat (quando não conseguir mapear em ações ou skill inexistente):
{"action":"chat","response":"Não consigo fazer isso ainda. Tente 'plan:' para um plano detalhado."}

Git workflow:
- "ver status / git status" → {"action":"git_status"}
- "adicionar tudo / stage tudo / git add" → {"action":"git_add_all"}
- "commitar / commit com mensagem X" → {"action":"git_commit","message":"X"}
- "subir / push" → {"action":"git_push"}
- "commit e push" → plan 3 passos: git_add_all → git_commit → git_push
- "commite tudo e sobe / commit tudo e push" → plan 4 passos: git_status → git_add_all → git_commit → git_push
- Se mensagem do commit não estiver clara: {"action":"chat","response":"Qual mensagem do commit?"}

Regras:
- No máximo 4 passos no plan.
- Não invente skills além das listadas.
- Use URLs completas com https://.
- Se o pedido exigir skill inexistente (ex: ler emails, acessar calendário), use chat explicando a limitação.
"""

def clean_json(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.replace("```json", "").replace("```", "").strip()
    return t

def safe_load(text: str) -> dict:
    return json.loads(clean_json(text))