from ....base import Skill
from .._common import not_authed_msg, get_alias, format_meta_list, normalize_category, build_query
from .....integrations.google import gmail_api as _api


class GoogleGmailSearchSkill(Skill):
    name = "google_gmail_search"

    def run(self, args: dict) -> str:
        alias = get_alias(args)
        if not _api.is_authed(alias):
            return not_authed_msg(alias)

        user_query = (args.get("query") or "").strip()
        category, err = normalize_category(args.get("category"))
        if err:
            return err

        if not user_query and not category:
            return "Campo 'query' é obrigatório para busca."

        max_r = int(args.get("max") or args.get("max_results") or 10)
        query = build_query("", user_query or None, category, inbox_only=False)

        try:
            ids = _api.list_message_ids(alias, query, max_r)
            if not ids:
                return f"Nenhum email encontrado para: {query}"
            metas = [_api.get_message_meta(alias, i) for i in ids]
            return format_meta_list(metas, alias)
        except Exception as e:
            return f"Erro na busca de emails: {e}"
