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
    • gmail/email: qualquer ação de email (ler, listar, buscar, resumir, enviar, responder, arquivar) → executor+brain.
    • exemplos: "abra o gmail e me fale os assuntos dos emails de hoje", "leia meus emails", "resuma os não lidos".
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
{"action":"google_gmail_list_today","account":"default"}
{"action":"google_gmail_list_today","account":"default","category":"primary"}
{"action":"google_gmail_list_unread","account":"default","category":"promotions"}
{"action":"google_gmail_search","account":"default","query":"from:alguem","category":"updates"}
{"action":"google_gmail_get_latest","account":"default","category":"social"}
{"action":"google_gmail_get_message","account":"default","message_id":"<id>"}
{"action":"google_gmail_summarize_today","account":"default","category":"primary"}
{"action":"google_gmail_summarize_unread","account":"default","category":"forums"}
{"action":"google_gmail_send_email","account":"default","to":"x@y.com","subject":"Oi","body":"..."}
{"action":"google_gmail_reply","account":"default","message_id":"<id>","body":"..."}
{"action":"google_gmail_mark_read","account":"default","message_id":"<id>"}
{"action":"google_gmail_archive","account":"default","message_id":"<id>"}
ou se for só conversa:
{"action":"chat","response":"..."}

Categorias Gmail (abas):
- "principal", "importantes" → category="primary"
- "promoções", "promocoes", "promoção" → category="promotions"
- "social" → category="social"
- "atualizações", "atualizacoes", "notificações" → category="updates"
- "fóruns", "foruns" → category="forums"
Quando detectar "aba X" ou menção de categoria, preencher args.category com o valor correto.
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
- google_gmail_list_today {account?, max?, period?, category?}
- google_gmail_list_unread {account?, max?, category?}
- google_gmail_search {account?, query?, max?, category?}
- google_gmail_get_latest {account?, query?, category?}
- google_gmail_get_message {account?, message_id}
- google_gmail_summarize_today {account?, max?, category?}
- google_gmail_summarize_unread {account?, max?, category?}
- google_gmail_summarize_thread {account?, thread_id}
- google_gmail_send_email {account?, to, subject?, body}
- google_gmail_reply {account?, message_id, body}
- google_gmail_mark_read {account?, message_id}
- google_gmail_archive {account?, message_id}
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

Gmail:
- "emails de hoje / inbox / leia meus emails / últimos emails" → {"action":"google_gmail_list_today","account":"default"}
- "emails não lidos / não li" → {"action":"google_gmail_list_unread","account":"default"}
- "buscar email / pesquisar <termo>" → {"action":"google_gmail_search","account":"default","query":"<termo>"}
- "último email / email mais recente" → {"action":"google_gmail_get_latest","account":"default"}
- "ler email <id> / ver email <id>" → {"action":"google_gmail_get_message","account":"default","message_id":"<id>"}
- "resuma emails de hoje / resumo do inbox" → {"action":"google_gmail_summarize_today","account":"default"}
- "resuma não lidos / resumo dos não lidos" → {"action":"google_gmail_summarize_unread","account":"default"}
- "resuma thread <id>" → {"action":"google_gmail_summarize_thread","account":"default","thread_id":"<id>"}
- "envie email para X assunto Y" → {"action":"google_gmail_send_email","account":"default","to":"X","subject":"Y","body":"..."}
- "responda email <id>" → {"action":"google_gmail_reply","account":"default","message_id":"<id>","body":"..."}
- "marque como lido <id>" → {"action":"google_gmail_mark_read","account":"default","message_id":"<id>"}
- "arquive <id>" → {"action":"google_gmail_archive","account":"default","message_id":"<id>"}
- "da empresa" → account="empresa" | "pessoal" → account="pessoal"

Categorias Gmail (abas) — preencher category= quando mencionadas:
- "principal", "importantes", "aba principal" → category="primary"
- "promoções", "promocoes", "promoção", "aba promoções" → category="promotions"
- "social", "aba social" → category="social"
- "atualizações", "atualizacoes", "notificações", "aba atualizações" → category="updates"
- "fóruns", "foruns", "aba fóruns" → category="forums"
Exemplos: "emails de hoje da aba principal" → list_today + category="primary"
          "resuma promoções de hoje" → summarize_today + category="promotions"
          "não lidos da aba social" → list_unread + category="social"

Regras:
- No máximo 4 passos no plan.
- Não invente skills além das listadas.
- Use URLs completas com https://.
- Se o pedido exigir skill inexistente (ex: calendário, Google Drive), use chat explicando a limitação.
"""

def clean_json(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.replace("```json", "").replace("```", "").strip()
    return t

def safe_load(text: str) -> dict:
    return json.loads(clean_json(text))