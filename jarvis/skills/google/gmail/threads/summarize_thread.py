from ....base import Skill
from .._common import not_authed_msg, get_alias
from .....integrations.google import gmail_api as _api
from .....llm import ask_llm


class GoogleGmailSummarizeThreadSkill(Skill):
    name = "google_gmail_summarize_thread"

    def run(self, args: dict) -> str:
        alias = get_alias(args)
        if not _api.is_authed(alias):
            return not_authed_msg(alias)
        thread_id = (args.get("thread_id") or "").strip()
        if not thread_id:
            return "Campo 'thread_id' é obrigatório."
        try:
            messages = _api.get_thread(alias, thread_id)
            if not messages:
                return "Thread não encontrada ou sem mensagens."
            snippets = []
            for m in messages:
                snippets.append(
                    f"- De: {m['from']}\n"
                    f"  Assunto: {m['subject']}\n"
                    f"  Preview: {m['snippet'][:100]}"
                )
            prompt = (
                "Resuma esta conversa de email de forma curta e direta em português brasileiro:\n\n"
                + "\n".join(snippets)
            )
            msgs = [{"role": "user", "content": prompt}]
            return ask_llm(msgs, model="fast", role="gmail_summarize_thread")
        except Exception as e:
            return f"Erro ao resumir thread: {e}"
