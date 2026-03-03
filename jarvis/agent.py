import os

from .skills.registry import build_skills
from .memory import add_turn, set_state, set_session
from .commands import handle_builtin
from .router import route_input, strip_forced_prefix
from .planner import make_plan
from .queue import enqueue_plan, clear_queue, has_active_queue
from .executor import execute_next, execute_until_blocked

DEBUG = os.getenv("JARVIS_DEBUG", "0") == "1"


class JarvisAgent:
    def __init__(self, execute: bool = False):
        self.SKILLS = build_skills(execute=execute)

        if execute:
            set_session({"mode": "execute"})

    def _learn_state_from_action(self, action: str, args: dict):
        patch = {}

        if action == "open_app":
            app = args.get("app")
            if app:
                patch["last_opened_app"] = app
                if app.lower() in ("google chrome", "chrome", "safari", "firefox", "microsoft edge", "edge"):
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

    def run(self, user_input: str) -> str:
        def remember(resp: str) -> str:
            try:
                add_turn(user_input, resp)
            except Exception:
                pass
            return resp

        # built-ins first (NO LLM)
        out = handle_builtin(user_input, self.SKILLS, self._learn_state_from_action)
        if out is not None:
            return remember(out)

        # forced prefix handling
        stripped, forced = strip_forced_prefix(user_input)
        text = stripped

        # route
        if forced:
            r = {"route": forced, "needs_actions": forced != "fast_reply"}
        else:
            r = route_input(text)

        if r["route"] == "fast_reply":
            return remember(r.get("response") or text)

        # planner route => create queue + execute until blocked/end (V3)
        if r["route"] == "planner":
            plan_data = make_plan(text)
            goal = plan_data["goal"]
            plan = plan_data["plan"]

            clear_queue()
            enqueue_plan(goal, plan)

            run_out = execute_until_blocked(self.SKILLS, self._learn_state_from_action)

            # se ainda sobrou fila (blocked/pending), orienta
            if has_active_queue():
                run_out = (
                    run_out
                    + "\n\n➡️ Se bloquear, confirme com 'yes' ou 'YES I KNOW'. "
                      "Para seguir manualmente: 'continue'. "
                      "Para rodar tudo até o próximo bloqueio: 'executar tudo'."
                )
            return remember(run_out)

        # executor route => single-step queue
        if r["route"] == "executor":
            plan_data = make_plan(text)
            goal = plan_data["goal"]
            plan = plan_data["plan"][:1]

            clear_queue()
            enqueue_plan(goal, plan)
            return remember(execute_next(self.SKILLS, self._learn_state_from_action))

        return remember("Não consegui processar seu pedido agora.")