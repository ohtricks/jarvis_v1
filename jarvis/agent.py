import os
import time

from .skills.registry import build_skills
from .memory import add_turn, set_state, set_session, get_session
from .commands import handle_builtin
from .router import route_input, strip_forced_prefix
from .planner import make_plan
from .queue import enqueue_plan, clear_queue, has_active_queue
from .executor import execute_until_blocked
from .telemetry import start_debug_entry, debug_set, flush_debug_entry

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
        sess = get_session()
        mode = (sess.get("mode") or "dry").lower()
        start_debug_entry(user_input, mode)
        t0 = time.time()
        _resp: list[str] = [""]  # captura resposta para o finally

        def remember(resp: str) -> str:
            _resp[0] = resp
            try:
                add_turn(user_input, resp)
            except Exception:
                pass
            return resp

        try:
            # built-ins first (NO LLM)
            out = handle_builtin(user_input, self.SKILLS, self._learn_state_from_action)
            if out is not None:
                debug_set("route", "builtin")
                return remember(out)

            # forced prefix handling
            stripped, forced = strip_forced_prefix(user_input)
            text = stripped

            # route
            if forced:
                debug_set("route", forced)
                debug_set("route_forced", True)
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

            # executor route => executa todos os steps do plano
            if r["route"] == "executor":
                plan_data = make_plan(text)
                goal = plan_data["goal"]
                plan = plan_data["plan"]

                clear_queue()
                enqueue_plan(goal, plan)

                run_out = execute_until_blocked(self.SKILLS, self._learn_state_from_action)
                if has_active_queue():
                    run_out = (
                        run_out
                        + "\n\n➡️ Se bloquear, confirme com 'yes' ou 'YES I KNOW'. "
                          "Para seguir manualmente: 'continue'."
                    )
                return remember(run_out)

            return remember("Não consegui processar seu pedido agora.")

        except Exception as e:
            return remember(f"Erro: {e}")

        finally:
            flush_debug_entry(_resp[0], int((time.time() - t0) * 1000))