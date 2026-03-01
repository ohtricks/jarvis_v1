import json
import os
from .brain import ask_llm
from .skills.registry import build_skills
from .memory import add_turn, build_context, clear_memory, should_inject_memory

DEBUG = os.getenv("JARVIS_DEBUG", "0") == "1"

# Router FAST: curtinho e claro
ROUTER_PROMPT = """
Você é um roteador. Responda APENAS JSON válido, sem texto extra.

Formato:
{"route":"fast_reply|brain|reasoning","needs_actions":true|false,"response":"..."}

Regras:
- Se for resposta curta e simples, sem abrir apps/usar tools: route="fast_reply", needs_actions=false e inclua "response" (pt-BR).
- Se precisar abrir apps/usar tools (ex: abrir Safari, VSCode, Outlook): route="brain", needs_actions=true.
- Se for tarefa complexa/multi-etapas (planejar, analisar, priorizar): route="reasoning", needs_actions=true.
"""

# Executor: também curto e claro
EXECUTOR_PROMPT = """
Responda APENAS JSON válido, sem texto extra.

Ações disponíveis:
- open_app
- open_url
- run_shell

Se 1 ação:
{"action":"open_app","app":"Safari"}
{"action":"open_url","url":"https://mail.google.com","browser":"Google Chrome"}
{"action":"run_shell","command":"git status","cwd":"/caminho/opcional"}

Se várias ações:
{"actions":[{"action":"open_app","app":"Safari"},{"action":"open_app","app":"Visual Studio Code"}]}
{"actions":[{"action":"open_app","app":"Google Chrome"}, {"action":"open_url","url":"https://mail.google.com","browser":"Google Chrome"}]}
{"actions":[{"action":"run_shell","command":"pwd"},{"action":"run_shell","command":"ls"}]}

Se não precisar ação:
{"action":"chat","response":"mensagem em pt-BR"}
"""


def clean_json(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.replace("```json", "").replace("```", "").strip()
    return t


def safe_load(text: str) -> dict:
    return json.loads(clean_json(text))


class JarvisAgent:
    def __init__(self, execute: bool = False):
        self.SKILLS = build_skills(execute=execute)

    def route(self, user_input: str) -> dict:
        msgs = [
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user", "content": user_input},
        ]
        raw = ask_llm(msgs, model="fast", temperature=0.0)
        if DEBUG:
            print("DEBUG ROUTER:", raw)
        data = safe_load(raw)

        # validações mínimas
        if data.get("route") not in ("fast_reply", "brain", "reasoning"):
            return {"route": "brain", "needs_actions": True}

        if data["route"] == "fast_reply":
            resp = data.get("response", "").strip()
            if not resp:
                return {"route": "brain", "needs_actions": False}
            return {"route": "fast_reply", "needs_actions": False, "response": resp}

        return {"route": data["route"], "needs_actions": bool(data.get("needs_actions", True))}

    def decide(self, user_input: str, model: str) -> dict:
        # injeta memória só quando fizer sentido (pra não gastar tokens à toa)
        context = build_context(max_turns=4) if should_inject_memory(user_input) else ""
        system_prompt = EXECUTOR_PROMPT + ("\n\n" + context if context else "")

        msgs = [
            {"role": "system", "content": system_prompt},  # <-- FIX: usar system_prompt com memória
            {"role": "user", "content": user_input},
        ]
        raw = ask_llm(msgs, model=model, temperature=0.1)
        if DEBUG:
            print(f"DEBUG EXECUTOR({model}):", raw)
        return safe_load(raw)

    def run(self, user_input: str) -> str:
        def remember(response: str) -> str:
            try:
                add_turn(user_input, response)
            except Exception as e:
                if DEBUG:
                    print("DEBUG MEMORY ERROR:", e)
            return response

        cmd = user_input.strip().lower()
        if cmd in ("limpar memoria", "limpar memória", "clear memory", "reset memory"):
            clear_memory()
            return "Memória limpa."

        # 1) Router (FAST)
        try:
            r = self.route(user_input)
        except Exception as e:
            if DEBUG:
                print("DEBUG ROUTER ERROR:", e)
            r = {"route": "brain", "needs_actions": True}

        # 2) Fast reply (1 chamada total)
        if r["route"] == "fast_reply":
            return remember(r["response"])

        model = r["route"]  # brain ou reasoning

        # 3) Executor (brain/reasoning)
        try:
            d = self.decide(user_input, model=model)
        except Exception as e:
            if DEBUG:
                print("DEBUG EXECUTOR ERROR:", e)
            # fallback pro reasoning
            if model != "reasoning":
                d = self.decide(user_input, model="reasoning")
            else:
                return remember("Não consegui processar seu pedido agora.")

        # 4) Multi actions
        if "actions" in d and isinstance(d["actions"], list):
            results = []
            for step in d["actions"]:
                action = step.get("action")
                if action in self.SKILLS:
                    args = {k: v for k, v in step.items() if k != "action"}
                    results.append(self.SKILLS[action].run(args))
                else:
                    results.append(f"Ação desconhecida: {action}")
            return remember("\n".join(results))

        # 5) Single action / chat
        action = d.get("action")

        if action == "chat":
            return remember(d.get("response", ""))

        if action in self.SKILLS:
            args = {k: v for k, v in d.items() if k != "action"}
            return remember(self.SKILLS[action].run(args))

        return remember("Não entendi como executar isso ainda.")