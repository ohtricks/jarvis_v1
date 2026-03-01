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

Always respond ONLY in JSON.

If one action is required:
{
  "action": "open_app",
  "app": "Safari"
}

If multiple actions are required:
{
  "actions": [
    {"action": "open_app", "app": "Safari"},
    {"action": "open_app", "app": "Visual Studio Code"}
  ]
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

            data = json.loads(cleaned)

            # 1) multi-actions
            if "actions" in data and isinstance(data["actions"], list):
                results = []
                for step in data["actions"]:
                    action = step.get("action")
                    if action in SKILLS:
                        results.append(SKILLS[action].run({"app": step.get("app")}))
                    else:
                        results.append(f"Ação desconhecida: {action}")
                return "\n".join(results)

            # 2) single action
            action = data.get("action")

            if action == "chat":
                return data.get("response")

            if action in SKILLS:
                return SKILLS[action].run({"app": data.get("app")})

            return f"Ação desconhecida: {action}"

        except Exception as e:
            print("Skill parse error:", e)

        return decision