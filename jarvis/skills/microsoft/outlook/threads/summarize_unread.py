from ....base import Skill
from .._common import not_authed_msg, get_alias
from .....integrations.microsoft import outlook_api as _api
from .....integrations.microsoft.outlook_query import build_filter
from .....llm import ask_llm


class MicrosoftOutlookSummarizeUnreadSkill(Skill):
    name = "microsoft_outlook_summarize_unread"

    def run(self, args: dict) -> str:
        alias = get_alias(args)
        if not _api.is_authed(alias):
            return not_authed_msg(alias)

        max_r = int(args.get("max") or args.get("max_results") or 15)
        filter_str, _extra = build_filter(is_unread=True)

        try:
            ids = _api.list_message_ids(alias, filter_str, top=max_r)
            if not ids:
                return "Nenhum email não lido encontrado."
            snippets = []
            for mid in ids:
                m = _api.get_message_meta(alias, mid)
                snippets.append(
                    f"- De: {m['from']}\n"
                    f"  Assunto: {m['subject']}\n"
                    f"  Preview: {m['snippet'][:100]}"
                )
            prompt = (
                "Resuma estes emails não lidos do Outlook de forma curta e direta em português brasileiro.\n"
                "Destaque os mais importantes ou urgentes:\n\n"
                + "\n".join(snippets)
            )
            msgs = [{"role": "user", "content": prompt}]
            return ask_llm(msgs, model="fast", role="outlook_summarize_unread")
        except Exception as e:
            return f"Erro ao resumir emails não lidos: {e}"
