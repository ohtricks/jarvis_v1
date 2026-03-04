"""
Gmail API — autenticação OAuth e operações básicas.

SEGURANÇA:
- Credentials e tokens são salvos apenas em ~/.jarvis/credentials/gmail/<alias>/
- Nenhum token ou credential é enviado para LLM ou gravado em telemetry.
- As funções deste módulo nunca chamam add_turn(), telemetry ou logger.
"""

from pathlib import Path

CREDS_DIR = Path.home() / ".jarvis" / "credentials" / "gmail"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


def _alias_dir(alias: str) -> Path:
    return CREDS_DIR / (alias or "default")


def get_client_secret_path(alias: str) -> Path:
    """
    Busca client_secret.json com prioridade:
      1. ~/.jarvis/credentials/gmail/<alias>/client_secret.json
      2. ~/.jarvis/credentials/gmail/client_secret.json (global)
    """
    specific = _alias_dir(alias) / "client_secret.json"
    if specific.exists():
        return specific
    return CREDS_DIR / "client_secret.json"


def get_token_path(alias: str) -> Path:
    return _alias_dir(alias) / "token.json"


def is_authenticated(alias: str = "default") -> bool:
    """Verifica se existe token salvo para o alias."""
    return get_token_path(alias).exists()


def gmail_auth_interactive(alias: str, client_secret_path: Path) -> tuple[bool, str]:
    """
    Executa o fluxo OAuth localmente (abre o browser do usuário).

    NUNCA loga o token nem o conteúdo das credenciais.
    Retorna (success: bool, mensagem: str).
    """
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        return False, (
            "Dependências ausentes. Instale com:\n"
            "  pip install google-auth-oauthlib google-api-python-client"
        )

    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
        creds = flow.run_local_server(port=0)

        token_path = get_token_path(alias)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        # Salva token em arquivo local — fora do pipeline de telemetry/memory
        token_path.write_text(creds.to_json(), encoding="utf-8")

        return True, f"✅ Gmail conectado com sucesso (alias: {alias})"
    except Exception as e:
        return False, f"Erro durante autenticação OAuth: {e}"


def _get_credentials(alias: str):
    """Carrega e refresca credenciais salvas. Uso interno."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    token_path = get_token_path(alias)
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def list_recent_emails(alias: str = "default", max_results: int = 10) -> list[dict]:
    """
    Busca os N emails mais recentes da caixa de entrada.
    Requer autenticação prévia (is_authenticated == True).
    """
    from googleapiclient.discovery import build

    creds = _get_credentials(alias)
    service = build("gmail", "v1", credentials=creds)

    result = (
        service.users()
        .messages()
        .list(userId="me", labelIds=["INBOX"], maxResults=max_results)
        .execute()
    )
    messages = result.get("messages", [])

    out: list[dict] = []
    for m in messages:
        msg = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=m["id"],
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
            )
            .execute()
        )
        headers = {
            h["name"]: h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }
        out.append(
            {
                "id": m["id"],
                "subject": headers.get("Subject", "(sem assunto)"),
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
            }
        )
    return out
