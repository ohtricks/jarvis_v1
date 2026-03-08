"""
Outlook query builder — helpers para construção de filtros OData para Microsoft Graph API.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def build_filter(
    received_after: datetime | None = None,
    is_unread: bool = False,
    folder: str = "inbox",
    user_query: str | None = None,
) -> tuple[str, dict]:
    """
    Constrói o filtro OData e os parâmetros para listar mensagens no Graph API.

    Args:
        received_after: filtra mensagens mais recentes que essa data
        is_unread:      se True, filtra apenas não lidas (isRead eq false)
        folder:         nome da pasta: "inbox", "archive", etc.
        user_query:     busca textual livre (subject, from, body)

    Retorna (filter_str, extra_params) onde:
        filter_str   → valor do $filter OData
        extra_params → params adicionais (ex: $search para busca textual)
    """
    parts: list[str] = []
    extra_params: dict = {}

    if received_after:
        iso = received_after.strftime("%Y-%m-%dT%H:%M:%SZ")
        parts.append(f"receivedDateTime ge {iso}")

    if is_unread:
        parts.append("isRead eq false")

    # Busca textual livre usa $search (KQL), não $filter
    if user_query:
        extra_params["$search"] = f'"{user_query}"'

    filter_str = " and ".join(parts)
    return filter_str, extra_params


def received_after_hours(hours: int) -> datetime:
    """Retorna datetime UTC de 'agora menos N horas'."""
    return _now_utc() - timedelta(hours=hours)


def received_after_days(days: int) -> datetime:
    """Retorna datetime UTC de 'agora menos N dias'."""
    return _now_utc() - timedelta(days=days)
