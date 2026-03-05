"""
gmail_api.py — shim de compatibilidade.

Redireciona imports para o novo módulo integrations.google.gmail_api.
Mantido para não quebrar importações antigas (wizard, skills legados).
"""

from .integrations.google.gmail_api import (
    normalize_alias,
    get_paths,
    is_authed,
    is_authed as is_authenticated,
    _find_client_secret,
    build_service,
    gmail_auth_interactive,
    _get_credentials,
    list_message_ids,
    get_message_meta,
    get_message_full,
    get_thread,
    list_labels,
    modify_message_labels,
    get_attachment,
    send_message,
    reply_message,
    NEW_CREDS_DIR,
    OLD_CREDS_DIR,
    SCOPES,
)

from pathlib import Path

# Path legado — mantido para o wizard antigo
CREDS_DIR = OLD_CREDS_DIR


def _alias_dir(alias: str) -> Path:
    """Retorna o diretório do alias no path legado."""
    return CREDS_DIR / (alias or "default")


def get_client_secret_path(alias: str) -> Path:
    return get_paths(alias)["client_secret_path"]


def get_token_path(alias: str) -> Path:
    return get_paths(alias)["token_path"]


def list_recent_emails(alias: str = "default", max_results: int = 10) -> list[dict]:
    """Compatibilidade: usa get_message_meta via list_message_ids."""
    ids = list_message_ids(alias, "in:inbox", max_results)
    return [get_message_meta(alias, i) for i in ids]
