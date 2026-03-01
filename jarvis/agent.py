from .brain import ask_brain
from .skills.registry import SKILLS
import json


# ===============================
# JARVIS PERSONALITY
# ===============================
JARVIS_IDENTITY = """
You are J.A.R.V.I.S. (Just A Rather Very Intelligent System),
a professional personal AI assistant.

Personality:
- Polite, intelligent, calm and sophisticated.
- Professional, precise and proactive.
- Subtle dry humor when appropriate.
- Maintain a composed executive-assistant tone.

Language:
- Always respond in Brazilian Portuguese (pt-BR).
- Use natural and articulate Brazilian Portuguese.

Behavior:
- Provide clear and concise responses.
- Anticipate user needs when relevant.
- Offer helpful suggestions when appropriate.
- Never fabricate actions or results.

Identity:
You assist the user efficiently, reliably and professionally.
"""


# ===============================
# SKILL RULES
# ===============================
SKILL_RULES = """
You are also capable of executing system actions.

If the user requests opening an application,
respond ONLY using valid JSON:

{"action":"open_app","app":"APP_NAME"}

If no action is required,
respond normally as J.A.R.V.I.S.
"""


class JarvisAgent:

    def decide(self, user_input: str):

        messages = [
            {
                "role": "system",
                "content": JARVIS_IDENTITY + "\n" + SKILL_RULES
            },
            {
                "role": "user",
                "content": user_input
            }
        ]

        return ask_brain(messages)

    def run(self, user_input: str):

        decision = self.decide(user_input)

        # tenta executar skill
        try:
            if decision.strip().startswith("{"):
                data = json.loads(decision)

                action = data.get("action")

                if action in SKILLS:
                    return SKILLS[action](data.get("app"))

        except Exception:
            pass

        # resposta normal
        return decision