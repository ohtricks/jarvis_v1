import os
import time

from .skills.registry import build_skills
from .memory import add_turn, set_state, set_session, get_session
from .commands import handle_builtin
from .router import route_input, strip_forced_prefix
from .planner import make_plan
from .executor_llm import make_actions
from .context_engine import update_context_state
from .queue import enqueue_plan, clear_queue, has_active_queue
from .executor import execute_until_blocked
from .telemetry import start_debug_entry, debug_set, flush_debug_entry
from .ux import ux_stage, ux_format_response

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

        stages: list[str] = []

        try:
            # captura contexto do sistema antes de tudo (silencioso em caso de erro)
            update_context_state()

            stages.append(ux_stage("analisando"))

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
                stages.append(ux_stage("roteando", "planner"))
                stages.append(ux_stage("planejando", "reasoning"))

                plan_data = make_plan(text)
                goal = plan_data["goal"]
                plan = plan_data["plan"]

                clear_queue()
                enqueue_plan(goal, plan)

                stages.append(ux_stage("enfileirando"))
                stages.append(ux_stage("executando"))

                run_out = execute_until_blocked(self.SKILLS, self._learn_state_from_action)

                blocked = has_active_queue()
                if blocked:
                    stages.append(ux_stage("bloqueado", "aguardando confirmação"))
                else:
                    stages.append(ux_stage("finalizado"))

                if DEBUG:
                    debug_set("ux_stages", stages)
                return remember(ux_format_response(stages, run_out, blocked))

            # executor route => fast/brain compila 1-3 ações diretas (sem reasoning)
            if r["route"] == "executor":
                exec_model = r.get("executor_model", "fast")
                stages.append(ux_stage("roteando", f"executor ({exec_model})"))
                stages.append(ux_stage("compilando", exec_model))

                result = make_actions(text, model=exec_model)

                # chat: skill inexistente ou limitação — responde direto
                if "chat" in result:
                    return remember(result["chat"])

                goal = result["goal"]
                plan = result["plan"]

                clear_queue()
                enqueue_plan(goal, plan)

                stages.append(ux_stage("enfileirando"))
                stages.append(ux_stage("executando"))

                run_out = execute_until_blocked(self.SKILLS, self._learn_state_from_action)

                blocked = has_active_queue()
                if blocked:
                    stages.append(ux_stage("bloqueado", "aguardando confirmação"))
                else:
                    stages.append(ux_stage("finalizado"))

                if DEBUG:
                    debug_set("ux_stages", stages)
                return remember(ux_format_response(stages, run_out, blocked))

            return remember("Não consegui processar seu pedido agora.")

        except Exception as e:
            return remember(f"Erro: {e}")

        finally:
            flush_debug_entry(_resp[0], int((time.time() - t0) * 1000))