from ....base import Skill
from .._common import not_authed_msg, get_alias, format_meta_list
from .....integrations.microsoft import outlook_api as _api
from .....integrations.microsoft.outlook_query import build_filter


class MicrosoftOutlookSearchSkill(Skill):
    name = "microsoft_outlook_search"

    def run(self, args: dict) -> str:
        alias = get_alias(args)
        if not _api.is_authed(alias):
            return not_authed_msg(alias)

        user_query = (args.get("query") or "").strip()
        if not user_query:
            return "Campo 'query' é obrigatório para busca."

        max_r = int(args.get("max") or args.get("max_results") or 10)
        filter_str, extra = build_filter(user_query=user_query)

        try:
            # Busca textual usa $search, não $filter
            import urllib.request
            import urllib.parse
            import json as _json
            from .....integrations.microsoft.outlook_api import _get_token, _GRAPH_BASE

            token = _get_token(alias)
            params: dict = {
                "$top": max_r,
                "$select": "id,subject,from,toRecipients,receivedDateTime,bodyPreview,conversationId,isRead",
                "$orderby": "receivedDateTime desc",
            }
            if extra.get("$search"):
                params["$search"] = extra["$search"]

            url = f"{_GRAPH_BASE}/me/messages?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req) as resp:
                data = _json.loads(resp.read().decode("utf-8"))

            ids = [m["id"] for m in data.get("value", [])]
            if not ids:
                return f"Nenhum email encontrado para: {user_query}"
            metas = [_api.get_message_meta(alias, i) for i in ids]
            return format_meta_list(metas, alias)
        except Exception as e:
            return f"Erro na busca de emails: {e}"
