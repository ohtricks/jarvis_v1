from .open_app import OpenAppSkill
from .open_url import OpenUrlSkill
from .run_shell import RunShellSkill
from .git.git_status import GitStatusSkill
from .git.git_add_all import GitAddAllSkill
from .git.git_commit import GitCommitSkill
from .git.git_push import GitPushSkill
from .git.git_diff_review import GitDiffReviewSkill
from .git.git_diff_validate import GitDiffValidateSkill
from .git.git_generate_patch import GitGeneratePatchSkill
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
from .microsoft.outlook.read.list_today import MicrosoftOutlookListTodaySkill
from .microsoft.outlook.read.list_unread import MicrosoftOutlookListUnreadSkill
from .microsoft.outlook.read.search import MicrosoftOutlookSearchSkill
from .microsoft.outlook.read.get_message import MicrosoftOutlookGetMessageSkill
from .microsoft.outlook.read.get_latest import MicrosoftOutlookGetLatestSkill
from .microsoft.outlook.threads.summarize_today import MicrosoftOutlookSummarizeTodaySkill
from .microsoft.outlook.threads.summarize_unread import MicrosoftOutlookSummarizeUnreadSkill
from .microsoft.outlook.threads.summarize_thread import MicrosoftOutlookSummarizeThreadSkill
from .microsoft.outlook.write.send_email import MicrosoftOutlookSendEmailSkill
from .microsoft.outlook.write.reply import MicrosoftOutlookReplySkill
from .microsoft.outlook.labels.mark_read import MicrosoftOutlookMarkReadSkill
from .microsoft.outlook.labels.archive import MicrosoftOutlookArchiveSkill
from .capabilities import Capability, format_capabilities_for_prompt


def build_skills(execute: bool = False):
    """Retorna dict action->skill_obj. Contrato imutável — executor.py depende disso."""
    return {
        "open_app":   OpenAppSkill(execute=execute),
        "open_url":   OpenUrlSkill(execute=execute),
        "run_shell":  RunShellSkill(execute=execute),
        "git_status":           GitStatusSkill(),
        "git_diff_review":      GitDiffReviewSkill(),
        "git_diff_validate":    GitDiffValidateSkill(),
        "git_generate_patch":   GitGeneratePatchSkill(execute=execute),
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
        # Microsoft Outlook — read
        "microsoft_outlook_list_today":       MicrosoftOutlookListTodaySkill(),
        "microsoft_outlook_list_unread":      MicrosoftOutlookListUnreadSkill(),
        "microsoft_outlook_search":           MicrosoftOutlookSearchSkill(),
        "microsoft_outlook_get_message":      MicrosoftOutlookGetMessageSkill(),
        "microsoft_outlook_get_latest":       MicrosoftOutlookGetLatestSkill(),
        # Microsoft Outlook — threads/summarize
        "microsoft_outlook_summarize_today":  MicrosoftOutlookSummarizeTodaySkill(),
        "microsoft_outlook_summarize_unread": MicrosoftOutlookSummarizeUnreadSkill(),
        "microsoft_outlook_summarize_thread": MicrosoftOutlookSummarizeThreadSkill(),
        # Microsoft Outlook — write (risky)
        "microsoft_outlook_send_email":       MicrosoftOutlookSendEmailSkill(execute=execute),
        "microsoft_outlook_reply":            MicrosoftOutlookReplySkill(execute=execute),
        # Microsoft Outlook — labels (risky)
        "microsoft_outlook_mark_read":        MicrosoftOutlookMarkReadSkill(execute=execute),
        "microsoft_outlook_archive":          MicrosoftOutlookArchiveSkill(execute=execute),
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
        name="git_diff_review",
        namespace="git",
        title="Revisar Git Diff",
        description="Analisa o diff atual do repositório: arquivos alterados, resumo de adições/remoções, insights de risco e ações sugeridas. Retorna payload estruturado para modal de revisão na UI.",
        args_schema={"cwd": "string?"},
        examples=[
            "mostre o git diff do projeto",
            "analise o diff atual",
            "revise as alterações",
            "o que mudou no código?",
        ],
        risk="safe",
    ),
    Capability(
        name="git_diff_validate",
        namespace="git",
        title="Validar Git Diff (LLM)",
        description="Envia o diff atual para análise com IA: detecta bugs, problemas de segurança, código morto e sugere melhorias. Ideal após git_diff_review para aprofundar a análise.",
        args_schema={"cwd": "string?"},
        examples=[
            "valide o diff atual",
            "analise o diff com IA",
            "tem algum bug no diff?",
            "revisar com LLM",
        ],
        risk="safe",
    ),
    Capability(
        name="git_generate_patch",
        namespace="git",
        title="Gerar Patch do Diff",
        description="Exporta o diff atual como arquivo .patch em ~/.jarvis/patch_<timestamp>.patch.",
        args_schema={"cwd": "string?"},
        examples=[
            "gerar patch do diff",
            "exportar diff como patch",
            "salvar alterações como patch",
        ],
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
    # ── Microsoft Outlook ─────────────────────────────────────────────────────
    Capability(
        name="microsoft_outlook_list_today",
        namespace="microsoft.outlook",
        title="Listar emails de hoje do Outlook",
        description="Lista emails recentes da caixa do Outlook (últimas 24h).",
        args_schema={"account": "string?", "max": "integer?", "period": "string?"},
        examples=["emails de hoje do outlook", "meus emails outlook de hoje", "outlook hoje"],
        risk="safe",
    ),
    Capability(
        name="microsoft_outlook_list_unread",
        namespace="microsoft.outlook",
        title="Listar emails não lidos do Outlook",
        description="Lista emails não lidos da caixa do Outlook.",
        args_schema={"account": "string?", "max": "integer?"},
        examples=["emails não lidos do outlook", "não lidos outlook", "outlook não lidos"],
        risk="safe",
    ),
    Capability(
        name="microsoft_outlook_search",
        namespace="microsoft.outlook",
        title="Buscar emails no Outlook",
        description="Busca emails no Outlook com texto livre (assunto, remetente, corpo).",
        args_schema={"account": "string?", "query": "string", "max": "integer?"},
        examples=["buscar email outlook sobre reunião", "pesquisar outlook fatura", "outlook busca"],
        risk="safe",
    ),
    Capability(
        name="microsoft_outlook_get_message",
        namespace="microsoft.outlook",
        title="Ler email do Outlook por ID",
        description="Lê o conteúdo completo de um email do Outlook pelo ID.",
        args_schema={"account": "string?", "message_id": "string"},
        examples=["ler email outlook <id>", "ver conteúdo do email outlook"],
        risk="safe",
    ),
    Capability(
        name="microsoft_outlook_get_latest",
        namespace="microsoft.outlook",
        title="Último email do Outlook",
        description="Lê o email mais recente da caixa do Outlook.",
        args_schema={"account": "string?"},
        examples=["último email outlook", "email mais recente outlook", "outlook último email"],
        risk="safe",
    ),
    Capability(
        name="microsoft_outlook_summarize_today",
        namespace="microsoft.outlook",
        title="Resumir emails de hoje do Outlook",
        description="Gera um resumo dos emails de hoje do Outlook usando IA.",
        args_schema={"account": "string?", "max": "integer?"},
        examples=["resuma emails do outlook de hoje", "resumo outlook hoje"],
        risk="safe",
    ),
    Capability(
        name="microsoft_outlook_summarize_unread",
        namespace="microsoft.outlook",
        title="Resumir emails não lidos do Outlook",
        description="Gera um resumo dos emails não lidos do Outlook usando IA.",
        args_schema={"account": "string?", "max": "integer?"},
        examples=["resuma não lidos do outlook", "resumo outlook não lidos"],
        risk="safe",
    ),
    Capability(
        name="microsoft_outlook_summarize_thread",
        namespace="microsoft.outlook",
        title="Resumir conversa do Outlook",
        description="Gera um resumo de uma conversa (thread) do Outlook.",
        args_schema={"account": "string?", "conversation_id": "string"},
        examples=["resuma essa conversa outlook", "resumo thread outlook"],
        risk="safe",
    ),
    Capability(
        name="microsoft_outlook_send_email",
        namespace="microsoft.outlook",
        title="Enviar email pelo Outlook",
        description="Envia um email via Outlook. Requer confirmação (risky).",
        args_schema={"account": "string?", "to": "string", "subject": "string?", "body": "string", "cc": "string?", "bcc": "string?"},
        examples=["envie email pelo outlook para X", "mande email outlook para fulano@empresa.com"],
        risk="risky",
    ),
    Capability(
        name="microsoft_outlook_reply",
        namespace="microsoft.outlook",
        title="Responder email do Outlook",
        description="Responde a um email do Outlook pelo ID. Requer confirmação (risky).",
        args_schema={"account": "string?", "message_id": "string", "body": "string", "reply_all": "boolean?"},
        examples=["responda o email outlook <id>", "reply outlook"],
        risk="risky",
    ),
    Capability(
        name="microsoft_outlook_mark_read",
        namespace="microsoft.outlook",
        title="Marcar como lido no Outlook",
        description="Marca um email do Outlook como lido. Requer confirmação (risky).",
        args_schema={"account": "string?", "message_id": "string"},
        examples=["marque como lido outlook", "mark as read outlook"],
        risk="risky",
    ),
    Capability(
        name="microsoft_outlook_archive",
        namespace="microsoft.outlook",
        title="Arquivar email do Outlook",
        description="Move o email do Outlook para a pasta Archive. Requer confirmação (risky).",
        args_schema={"account": "string?", "message_id": "string"},
        examples=["arquive o email outlook", "archive outlook"],
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
