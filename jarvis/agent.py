# jarvis/agent.py
import os
from .skills.registry import build_skills
from .memory import add_turn, build_context, should_inject_memory, set_state
from .prompts import EXECUTOR_PROMPT
from .utils import safe_load
from .brain import ask_llm
from .router import route_input
from .planner import normalize_actions_to_plan, start_plan
from .commands import handle_builtin

DEBUG = os.getenv("JARVIS_DEBUG", "0") == "1"
BROWSERS = ("google chrome", "chrome", "safari", "firefox", "microsoft edge", "edge")

class JarvisAgent:
    def __init__(self, execute: bool = False):
        self.SKILLS = build_skills(execute=execute)

    def decide(self, user_input: str, model: str) -> dict:
        context = build_context(max_turns=4) if should_inject_memory(user_input) else ""
        system_prompt = EXECUTOR_PROMPT + ("\n\n" + context if context else "")
        msgs = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]
        raw = ask_llm(msgs, model=model, temperature=0.1)
        if DEBUG:
            print(f"DEBUG EXECUTOR({model}):", raw)
        try:
            return safe_load(raw)
        except Exception:
            return {"action": "chat", "response": raw}

    def run(self, user_input: str) -> str:
        def remember(response: str) -> str:
            try:
                add_turn(user_input, response)
            except Exception:
                pass
            return response

        def learn_state_from_action(action: str, args: dict):
            patch = {}
            if action == "open_app":
                app = args.get("app")
                if app:
                    patch["last_opened_app"] = app
                    if app.lower() in BROWSERS:
                        patch["current_browser"] = app
            elif action == "open_url":
                url = args.get("url")
                browser = args.get("browser")
                if url:
                    patch["last_opened_url"] = url
                if browser:
                    patch["current_browser"] = browser
            elif action == "run_shell":
                cmd = args.get("command")
                cwd = args.get("cwd")
                if cmd:
                    patch["last_shell_command"] = cmd
                if cwd:
                    patch["last_cwd"] = cwd
            if patch:
                set_state(patch)

        # forced prefix
        forced = None
        raw_text = (user_input or "").strip()
        lower = raw_text.lower()
        prefixes = {
            "reason:": "reasoning",
            "think:": "reasoning",
            "plan:": "reasoning",
            "brain:": "brain",
            "fast:": "fast_reply",
        }
        for p, route in prefixes.items():
            if lower.startswith(p):
                forced = route
                user_input = raw_text[len(p):].strip()
                if DEBUG:
                    print(f"DEBUG FORCED ROUTE: {forced} (prefix {p})")
                break

        # built-in commands (NO LLM)
        handled = handle_builtin((user_input or "").strip(), self.SKILLS, learn_state_from_action)
        if handled is not None:
            return remember(handled)

        # routing
        if forced == "fast_reply":
            return remember(user_input)

        if forced in ("brain", "reasoning"):
            r = {"route": forced, "needs_actions": True}
        else:
            try:
                r = route_input(user_input, debug=DEBUG)
            except Exception as e:
                if DEBUG:
                    print("DEBUG ROUTER ERROR:", e)
                r = {"route": "brain", "needs_actions": True}

        if r["route"] == "fast_reply":
            return remember(r["response"])

        model = r["route"]

        # decide
        try:
            d = self.decide(user_input, model=model)
        except Exception as e:
            if DEBUG:
                print("DEBUG EXECUTOR ERROR:", e)
            if model != "reasoning":
                d = self.decide(user_input, model="reasoning")
            else:
                return remember("Não consegui processar seu pedido agora.")

        # forced plan mode (plan:/think:/reason:) -> step-by-step
        if forced == "reasoning":
            d = normalize_actions_to_plan(d)

        if "plan" in d and isinstance(d["plan"], list):
            return remember(start_plan(d["plan"], user_input, self.SKILLS, learn_state_from_action))

        # actions
        if "actions" in d and isinstance(d["actions"], list):
            out = []
            for step in d["actions"]:
                action = step.get("action")
                if action in self.SKILLS:
                    args = {k: v for k, v in step.items() if k != "action"}
                    learn_state_from_action(action, args)
                    out.append(self.SKILLS[action].run(args))
                else:
                    out.append(f"Ação desconhecida: {action}")
            return remember("\n".join(out))

        # single
        action = d.get("action")
        if action == "chat":
            return remember(d.get("response", ""))

        if action in self.SKILLS:
            args = {k: v for k, v in d.items() if k != "action"}
            learn_state_from_action(action, args)
            return remember(self.SKILLS[action].run(args))

        return remember("Não entendi como executar isso ainda.")