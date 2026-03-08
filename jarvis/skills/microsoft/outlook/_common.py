"""Helpers compartilhados pelas Microsoft Outlook skills."""
from ....integrations.microsoft import outlook_api as _api
from ....integrations.microsoft.outlook_query import (
    build_filter,
    received_after_days,
    received_after_hours,
)


def not_authed_msg(alias: str) -> str:
    return (
        f"Conta Outlook '{alias}' não conectada. "
        f"Para conectar: auth outlook {alias}"
    )


def get_alias(args: dict) -> str:
    return _api.normalize_alias(args.get("account") or args.get("alias"))


def format_meta_list(metas: list[dict], alias: str) -> str:
    if not metas:
        return "Nenhum email encontrado."
    lines = [f"📬 {len(metas)} email(s) — conta Outlook: {alias}\n"]
    for i, m in enumerate(metas, 1):
        status = "" if m.get("isRead", True) else "🔵 "
        lines.append(
            f"{i}. {status}{m['subject']}\n"
            f"   De: {m['from']}\n"
            f"   {m['date']}\n"
            f"   ID: {m['id']}"
        )
    return "\n".join(lines)
