from .brain import ask_brain
from .skills.registry import SKILLS
import json


# ===============================
# JARVIS PERSONALITY
# ===============================
JARVIS_IDENTITY = """
You are J.A.R.V.I.S. (Just A Rather Very Intelligent System),
a professional personal AI assistant.

Language:
- Always respond in Brazilian Portuguese (pt-BR).
"""


# ===============================
# SKILL RULES
# ===============================
SKILL_RULES = """
You can execute system actions.

Available actions:
- open_app

RULES:

If an action is required, respond ONLY in JSON:

{
  "action": "open_app",
  "app": "Safari"
}

If no action is required:

{
  "action": "chat",
  "response": "message"
}
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

        print("DEBUG LLM:", decision)

        try:
            # limpa markdown/json fences
            cleaned = decision.strip()

            if cleaned.startswith("```"):
                cleaned = cleaned.replace("```json", "")
                cleaned = cleaned.replace("```", "").strip()

            data = json.loads(cleaned)

            action = data.get("action")

            if action in SKILLS:
                return SKILLS[action].run({"app": data.get("app")})

        except Exception as e:
            print("Skill parse error:", e)

        return decision