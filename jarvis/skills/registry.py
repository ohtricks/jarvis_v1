from .open_app import OpenAppSkill
from .open_url import OpenUrlSkill
from .run_shell import RunShellSkill
from .git.git_status import GitStatusSkill
from .git.git_add_all import GitAddAllSkill
from .git.git_commit import GitCommitSkill
from .git.git_push import GitPushSkill
from .google.gmail.read.list_today import GoogleGmailListTodaySkill
from .google.gmail.read.list_unread import GoogleGmailListUnreadSkill
from .google.gmail.read.search import GoogleGmailSearchSkill
from .google.gmail.read.get_message import GoogleGmailGetMessageSkill
from .google.gmail.read.get_latest import GoogleGmailGetLatestSkill
from .google.gmail.threads.summarize_today import GoogleGmailSummarizeTodaySkill
from .google.gmail.threads.summarize_unread import GoogleGmailSummarizeUnreadSkill
from .google.gmail.threads.summarize_thread import GoogleGmailSummarizeThreadSkill
from .google.gmail.write.send_email import GoogleGmailSendEmailSkill
from .google.gmail.write.reply import GoogleGmailReplySkill
from .google.gmail.labels.mark_read import GoogleGmailMarkReadSkill
from .google.gmail.labels.archive import GoogleGmailArchiveSkill
from .capabilities import Capability, format_capabilities_for_prompt


def build_skills(execute: bool = False):
    """Retorna dict action->skill_obj. Contrato imutável — executor.py depende disso."""
    return {
        "open_app":   OpenAppSkill(execute=execute),
        "open_url":   OpenUrlSkill(execute=execute),
        "run_shell":  RunShellSkill(execute=execute),
        "git_status":       GitStatusSkill(),
        "git_add_all":      GitAddAllSkill(execute=execute),
        "git_commit":       GitCommitSkill(execute=execute),
        "git_push":         GitPushSkill(execute=execute),
        # Google Gmail — read
        "google_gmail_list_today":       GoogleGmailListTodaySkill(),
        "google_gmail_list_unread":      GoogleGmailListUnreadSkill(),
        "google_gmail_search":           GoogleGmailSearchSkill(),
        "google_gmail_get_message":      GoogleGmailGetMessageSkill(),
        "google_gmail_get_latest":       GoogleGmailGetLatestSkill(),
        # Google Gmail — threads/summarize
        "google_gmail_summarize_today":  GoogleGmailSummarizeTodaySkill(),
        "google_gmail_summarize_unread": GoogleGmailSummarizeUnreadSkill(),
        "google_gmail_summarize_thread": GoogleGmailSummarizeThreadSkill(),
        # Google Gmail — write (risky)
        "google_gmail_send_email":       GoogleGmailSendEmailSkill(execute=execute),
        "google_gmail_reply":            GoogleGmailReplySkill(execute=execute),
        # Google Gmail — labels (risky)
        "google_gmail_mark_read":        GoogleGmailMarkReadSkill(execute=execute),
        "google_gmail_archive":          GoogleGmailArchiveSkill(execute=execute),
    }


# ── Catálogo de capabilities ──────────────────────────────────────────────────
# Adicione aqui ao criar novas skills. Os action names DEVEM bater com as chaves
# de build_skills() (ou "chat" para a resposta direta do executor_llm).

_CATALOG: list[Capability] = [
    Capability(
        name="open_app",
        namespace="system",
        title="Abrir aplicativo",
        description="Abre um aplicativo no macOS pelo nome.",
        args_schema={"app": "string"},
        examples=["abra o chrome", "abra o vscode", "abra o slack"],
        risk="safe",
    ),
    Capability(
        name="open_url",
        namespace="browser",
        title="Abrir URL no navegador",
        description="Abre uma URL no navegador padrão ou especificado.",
        args_schema={"url": "string", "browser": "string?"},
        examples=["abra https://gmail.com", "abra o youtube no chrome"],
        risk="safe",
    ),
    Capability(
        name="run_shell",
        namespace="dev",
        title="Executar comando no terminal",
        description="Executa um comando shell (allowlist de prefixos seguros).",
        args_schema={"command": "string", "cwd": "string?"},
        examples=["git status", "npm install", "ls -la"],
        risk="risky",
    ),
    Capability(
        name="chat",
        namespace="meta",
        title="Resposta direta",
        description="Retorna texto diretamente sem executar ação (limitação ou conversa).",
        args_schema={"response": "string"},
        examples=["o que é Python?", "explique git rebase"],
        risk="safe",
    ),
    Capability(
        name="git_status",
        namespace="git",
        title="Git Status",
        description="Mostra o status do repositório git no diretório atual.",
        args_schema={"cwd": "string?"},
        examples=["ver status do git", "git status", "o que mudou?"],
        risk="safe",
    ),
    Capability(
        name="git_add_all",
        namespace="git",
        title="Git Add All",
        description="Adiciona todos os arquivos modificados ao stage (git add -A).",
        args_schema={"cwd": "string?"},
        examples=["adicionar tudo", "stage tudo", "git add all"],
        risk="risky",
    ),
    Capability(
        name="git_commit",
        namespace="git",
        title="Git Commit",
        description="Cria um commit com a mensagem fornecida.",
        args_schema={"message": "string", "cwd": "string?"},
        examples=["commite com mensagem fix bug", "git commit -m 'feat: nova feature'"],
        risk="risky",
    ),
    Capability(
        name="git_push",
        namespace="git",
        title="Git Push",
        description="Envia commits para o repositório remoto.",
        args_schema={"remote": "string?", "branch": "string?", "cwd": "string?"},
        examples=["sobe as mudanças", "push", "git push origin main"],
        risk="risky",
    ),
    # ── Google Gmail ──────────────────────────────────────────────────────────
    Capability(
        name="google_gmail_list_today",
        namespace="google.gmail",
        title="Listar emails de hoje",
        description="Lista emails recentes da caixa de entrada (últimas 24h). Suporta filtro por aba (category).",
        args_schema={"account": "string?", "max": "integer?", "period": "string?", "category": "string?"},
        examples=["emails de hoje", "emails de hoje da aba principal", "promoções de hoje"],
        risk="safe",
    ),
    Capability(
        name="google_gmail_list_unread",
        namespace="google.gmail",
        title="Listar emails não lidos",
        description="Lista emails não lidos da caixa de entrada. Suporta filtro por aba (category).",
        args_schema={"account": "string?", "max": "integer?", "category": "string?"},
        examples=["emails não lidos", "não lidos da aba social", "promoções não lidas"],
        risk="safe",
    ),
    Capability(
        name="google_gmail_search",
        namespace="google.gmail",
        title="Buscar emails",
        description="Busca emails com query Gmail (from:, subject:, etc.). Suporta filtro por aba (category).",
        args_schema={"account": "string?", "query": "string?", "max": "integer?", "category": "string?"},
        examples=["buscar email de fulano", "pesquisar fatura na aba atualizações"],
        risk="safe",
    ),
    Capability(
        name="google_gmail_get_message",
        namespace="google.gmail",
        title="Ler email por ID",
        description="Lê o conteúdo completo de um email pelo ID.",
        args_schema={"account": "string?", "message_id": "string"},
        examples=["ler email <id>", "ver conteúdo do email"],
        risk="safe",
    ),
    Capability(
        name="google_gmail_get_latest",
        namespace="google.gmail",
        title="Último email recebido",
        description="Lê o email mais recente da caixa de entrada. Suporta filtro por aba (category).",
        args_schema={"account": "string?", "query": "string?", "category": "string?"},
        examples=["último email", "último email da aba social", "email mais recente das promoções"],
        risk="safe",
    ),
    Capability(
        name="google_gmail_summarize_today",
        namespace="google.gmail",
        title="Resumir emails de hoje",
        description="Gera um resumo dos emails de hoje usando IA. Suporta filtro por aba (category).",
        args_schema={"account": "string?", "max": "integer?", "category": "string?"},
        examples=["resuma meus emails de hoje", "resuma promoções de hoje", "resumo do inbox principal"],
        risk="safe",
    ),
    Capability(
        name="google_gmail_summarize_unread",
        namespace="google.gmail",
        title="Resumir emails não lidos",
        description="Gera um resumo dos emails não lidos usando IA. Suporta filtro por aba (category).",
        args_schema={"account": "string?", "max": "integer?", "category": "string?"},
        examples=["resuma os não lidos", "resuma não lidos de promoções", "resumo social não lido"],
        risk="safe",
    ),
    Capability(
        name="google_gmail_summarize_thread",
        namespace="google.gmail",
        title="Resumir thread de email",
        description="Gera um resumo de uma conversa (thread) de email.",
        args_schema={"account": "string?", "thread_id": "string"},
        examples=["resuma esse thread", "resumo da conversa de email"],
        risk="safe",
    ),
    Capability(
        name="google_gmail_send_email",
        namespace="google.gmail",
        title="Enviar email",
        description="Envia um email. Requer confirmação (risky).",
        args_schema={"account": "string?", "to": "string", "subject": "string?", "body": "string", "cc": "string?", "bcc": "string?"},
        examples=["envie email para X", "mande email para fulano@empresa.com"],
        risk="risky",
    ),
    Capability(
        name="google_gmail_reply",
        namespace="google.gmail",
        title="Responder email",
        description="Responde a um email pelo ID. Requer confirmação (risky).",
        args_schema={"account": "string?", "message_id": "string", "body": "string", "reply_all": "boolean?"},
        examples=["responda o email <id>", "reply para o último email"],
        risk="risky",
    ),
    Capability(
        name="google_gmail_mark_read",
        namespace="google.gmail",
        title="Marcar como lido",
        description="Remove label UNREAD de um email. Requer confirmação (risky).",
        args_schema={"account": "string?", "message_id": "string"},
        examples=["marque como lido", "mark as read"],
        risk="risky",
    ),
    Capability(
        name="google_gmail_archive",
        namespace="google.gmail",
        title="Arquivar email",
        description="Remove o email da caixa de entrada (archiva). Requer confirmação (risky).",
        args_schema={"account": "string?", "message_id": "string"},
        examples=["arquive o email", "archive este email"],
        risk="risky",
    ),
]


def get_capabilities() -> list[Capability]:
    """Retorna lista completa de capabilities registradas."""
    return list(_CATALOG)


def get_capabilities_text() -> str:
    """Texto compacto pronto para inserir em system prompts."""
    return format_capabilities_for_prompt(_CATALOG)


def find_capability(action: str) -> Capability | None:
    """Busca uma capability pelo action name. Retorna None se não encontrar."""
    for cap in _CATALOG:
        if cap.name == action:
            return cap
    return None
