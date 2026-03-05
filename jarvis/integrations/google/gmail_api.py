"""
Google Gmail API — autenticação OAuth e operações completas.

SEGURANÇA:
- Credentials e tokens são salvos apenas em ~/.jarvis/credentials/google/gmail/<alias>/
- Fallback automático para path antigo (~/.jarvis/credentials/gmail/<alias>/)
- Nenhum token ou credential é enviado para LLM ou gravado em telemetry.
- As funções deste módulo nunca chamam add_turn(), telemetry ou logger.
"""

from __future__ import annotations

import base64
import email as _email_lib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

NEW_CREDS_DIR = Path.home() / ".jarvis" / "credentials" / "google" / "gmail"
OLD_CREDS_DIR = Path.home() / ".jarvis" / "credentials" / "gmail"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


# ── Paths ─────────────────────────────────────────────────────────────────────

def normalize_alias(alias) -> str:
    return (str(alias or "default").strip().lower()) or "default"


def _find_client_secret(alias: str, new_dir: Path, old_dir: Path) -> Path:
    """Busca client_secret.json com fallback progressivo."""
    for p in [
        new_dir / "client_secret.json",
        old_dir / "client_secret.json",
        NEW_CREDS_DIR / "client_secret.json",
        OLD_CREDS_DIR / "client_secret.json",
    ]:
        if p.exists():
            return p
    return new_dir / "client_secret.json"


def get_paths(alias: str = "default") -> dict:
    """
    Retorna dict com base_dir, token_path, client_secret_path.
    Preferência: novo path; se token só existe no velho, migra silenciosamente.
    """
    alias = normalize_alias(alias)
    new_dir = NEW_CREDS_DIR / alias
    old_dir = OLD_CREDS_DIR / alias

    if (new_dir / "token.json").exists():
        base = new_dir
    elif (old_dir / "token.json").exists():
        base = old_dir
    else:
        base = new_dir

    return {
        "base_dir": base,
        "token_path": base / "token.json",
        "client_secret_path": _find_client_secret(alias, new_dir, old_dir),
    }


def is_authed(alias: str = "default") -> bool:
    """Verifica se existe token salvo para o alias."""
    return get_paths(alias)["token_path"].exists()


# backward-compat alias
is_authenticated = is_authed


# ── Auth ──────────────────────────────────────────────────────────────────────

def _get_credentials(alias: str):
    """Carrega e refresca credenciais salvas. Uso interno."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    token_path = get_paths(alias)["token_path"]
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def build_service(alias: str = "default"):
    """Carrega credenciais e retorna o service object do Gmail."""
    from googleapiclient.discovery import build
    creds = _get_credentials(alias)
    return build("gmail", "v1", credentials=creds)


def gmail_auth_interactive(alias: str, client_secret_path: Path) -> tuple[bool, str]:
    """
    Executa o fluxo OAuth localmente (abre o browser do usuário).
    Salva token no novo path (NEW_CREDS_DIR).
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

        token_path = NEW_CREDS_DIR / normalize_alias(alias) / "token.json"
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

        return True, f"✅ Gmail conectado com sucesso (alias: {alias})"
    except Exception as e:
        return False, f"Erro durante autenticação OAuth: {e}"


# ── Read ──────────────────────────────────────────────────────────────────────

def list_message_ids(
    alias: str,
    query: str,
    max_results: int = 10,
) -> list[str]:
    """Retorna lista de message IDs que batem com a query."""
    svc = build_service(alias)
    result = (
        svc.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    return [m["id"] for m in result.get("messages", [])]


def get_message_meta(alias: str, message_id: str) -> dict:
    """
    Retorna metadata básica de uma mensagem.
    {id, from, subject, date, snippet, threadId, labelIds}
    """
    svc = build_service(alias)
    msg = (
        svc.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=["Subject", "From", "Date", "To"],
        )
        .execute()
    )
    headers = {
        h["name"]: h["value"]
        for h in msg.get("payload", {}).get("headers", [])
    }
    return {
        "id": message_id,
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", "(sem assunto)"),
        "date": headers.get("Date", ""),
        "snippet": msg.get("snippet", ""),
        "threadId": msg.get("threadId", ""),
        "labelIds": msg.get("labelIds", []),
    }


def _decode_body_part(part: dict) -> str:
    """Decodifica base64url de uma parte do email."""
    data = (part.get("body") or {}).get("data", "")
    if not data:
        return ""
    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")


def get_message_full(alias: str, message_id: str) -> dict:
    """
    Retorna metadata + body_text (decode base64 parts/text).
    {id, from, to, subject, date, snippet, threadId, labelIds, body_text}
    """
    svc = build_service(alias)
    msg = (
        svc.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )
    payload = msg.get("payload") or {}
    headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

    # Extrai body text recursivamente
    body_text = ""
    parts = payload.get("parts") or []
    if parts:
        for part in parts:
            if part.get("mimeType") == "text/plain":
                body_text = _decode_body_part(part)
                break
        if not body_text:
            for part in parts:
                if part.get("mimeType") == "text/html":
                    body_text = _decode_body_part(part)
                    break
    else:
        body_text = _decode_body_part(payload)

    return {
        "id": message_id,
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", "(sem assunto)"),
        "date": headers.get("Date", ""),
        "snippet": msg.get("snippet", ""),
        "threadId": msg.get("threadId", ""),
        "labelIds": msg.get("labelIds", []),
        "body_text": body_text,
    }


def get_thread(alias: str, thread_id: str, max_messages: int = 20) -> list[dict]:
    """Retorna lista de metadados de mensagens de um thread."""
    svc = build_service(alias)
    thread = (
        svc.users()
        .threads()
        .get(userId="me", id=thread_id, format="metadata",
             metadataHeaders=["Subject", "From", "Date", "To"])
        .execute()
    )
    messages = thread.get("messages", [])[:max_messages]
    result = []
    for msg in messages:
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        result.append({
            "id": msg["id"],
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", "(sem assunto)"),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
            "threadId": thread_id,
            "labelIds": msg.get("labelIds", []),
        })
    return result


def list_labels(alias: str) -> list[dict]:
    """Retorna [{id, name}] com todos os labels da conta."""
    svc = build_service(alias)
    result = svc.users().labels().list(userId="me").execute()
    return [{"id": l["id"], "name": l["name"]} for l in result.get("labels", [])]


# ── Modify ────────────────────────────────────────────────────────────────────

def modify_message_labels(
    alias: str,
    message_id: str,
    add: list[str] | None = None,
    remove: list[str] | None = None,
) -> bool:
    """Adiciona/remove labels de uma mensagem. Retorna True se ok."""
    svc = build_service(alias)
    body: dict = {}
    if add:
        body["addLabelIds"] = add
    if remove:
        body["removeLabelIds"] = remove
    svc.users().messages().modify(userId="me", id=message_id, body=body).execute()
    return True


def get_attachment(alias: str, message_id: str, attachment_id: str) -> bytes:
    """Baixa e decodifica um attachment. Retorna bytes."""
    svc = build_service(alias)
    att = (
        svc.users()
        .messages()
        .attachments()
        .get(userId="me", messageId=message_id, id=attachment_id)
        .execute()
    )
    data = att.get("data", "")
    return base64.urlsafe_b64decode(data + "==")


# ── Write ─────────────────────────────────────────────────────────────────────

def send_message(
    alias: str,
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
) -> dict:
    """
    Envia email. Retorna {id, threadId}.
    """
    msg = MIMEMultipart()
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    msg.attach(MIMEText(body, "plain", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    svc = build_service(alias)
    result = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"id": result.get("id", ""), "threadId": result.get("threadId", "")}


def reply_message(
    alias: str,
    message_id: str,
    body: str,
    reply_all: bool = False,
) -> dict:
    """
    Reply a uma mensagem, mantendo threadId e headers In-Reply-To/References.
    Retorna {id, threadId}.
    """
    original = get_message_full(alias, message_id)
    svc = build_service(alias)

    msg = MIMEMultipart()
    msg["To"] = original.get("from", "")
    if reply_all:
        cc_parts = [original.get("to", "")]
        cc_parts = [p for p in cc_parts if p]
        if cc_parts:
            msg["Cc"] = ", ".join(cc_parts)
    msg["Subject"] = "Re: " + original.get("subject", "")
    msg["In-Reply-To"] = message_id
    msg["References"] = message_id
    msg.attach(MIMEText(body, "plain", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    result = svc.users().messages().send(
        userId="me",
        body={"raw": raw, "threadId": original.get("threadId", "")},
    ).execute()
    return {"id": result.get("id", ""), "threadId": result.get("threadId", "")}
