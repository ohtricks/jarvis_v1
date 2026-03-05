"""Helpers compartilhados pelas Google Gmail skills."""
from ....integrations.google import gmail_api as _api


def not_authed_msg(alias: str) -> str:
    return (
        f"Conta Gmail '{alias}' não conectada. "
        f"Para conectar: auth gmail {alias}"
    )


def get_alias(args: dict) -> str:
    return _api.normalize_alias(args.get("account") or args.get("alias"))


def format_meta_list(metas: list[dict], alias: str) -> str:
    if not metas:
        return "Nenhum email encontrado."
    lines = [f"📬 {len(metas)} email(s) — conta: {alias}\n"]
    for i, m in enumerate(metas, 1):
        lines.append(
            f"{i}. {m['subject']}\n"
            f"   De: {m['from']}\n"
            f"   {m['date']}\n"
            f"   ID: {m['id']}"
        )
    return "\n".join(lines)
