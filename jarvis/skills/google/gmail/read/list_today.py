from ....base import Skill
from .._common import not_authed_msg, get_alias, format_meta_list, normalize_category, build_query
from .....integrations.google import gmail_api as _api


class GoogleGmailListTodaySkill(Skill):
    name = "google_gmail_list_today"

    def run(self, args: dict) -> str:
        alias = get_alias(args)
        if not _api.is_authed(alias):
            return not_authed_msg(alias)

        category, err = normalize_category(args.get("category"))
        if err:
            return err

        max_r = int(args.get("max") or args.get("max_results") or 10)
        base = "newer_than:12h" if args.get("period") == "morning" else "newer_than:1d"
        query = build_query(base, None, category, inbox_only=True)

        try:
            ids = _api.list_message_ids(alias, query, max_r)
            if not ids:
                return "Nenhum email encontrado na caixa de entrada de hoje."
            metas = [_api.get_message_meta(alias, i) for i in ids]
            return format_meta_list(metas, alias)
        except Exception as e:
            return f"Erro ao buscar emails: {e}"
