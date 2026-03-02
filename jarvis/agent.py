import json
import os
from .brain import ask_llm
from .skills.registry import build_skills

from .memory import (
    add_turn, build_context, clear_memory, should_inject_memory, set_state,
    set_active_plan, get_active_plan, advance_active_plan,
    clear_active_plan, format_active_plan_status, set_goal,
    set_pending_action, set_pending_risk, get_pending
)

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

Se precisar planejamento (várias etapas com dependência), use:
{"plan":[
  {"step":"...", "action":"open_app", "app":"Google Chrome"},
  {"step":"...", "action":"open_url", "url":"https://mail.google.com", "browser":"Google Chrome"}
]}
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
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        raw = ask_llm(msgs, model=model, temperature=0.1)
        if DEBUG:
            print(f"DEBUG EXECUTOR({model}):", raw)

        # robustez: se não vier JSON, vira chat
        try:
            return safe_load(raw)
        except Exception:
            return {"action": "chat", "response": raw}

    def run(self, user_input: str) -> str:
        def learn_state_from_action(action: str, args: dict):
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
                try:
                    set_state(patch)
                except Exception as e:
                    if DEBUG:
                        print("DEBUG STATE ERROR:", e)

        def remember(response: str) -> str:
            try:
                add_turn(user_input, response)
            except Exception as e:
                if DEBUG:
                    print("DEBUG MEMORY ERROR:", e)
            return response

        # -----------------------------
        # RISK GATE (local, no LLM)
        # -----------------------------
        def classify_action_risk(action: str, args: dict) -> tuple[str, str]:
            """
            return (risk_level, note)
            risk_level in: safe|risky|danger
            """
            if action in ("open_app", "open_url"):
                return "safe", ""

            if action != "run_shell":
                return "risky", "Ação não classificada."

            cmd = (args.get("command") or "").strip()
            c = cmd.lower()

            safe_prefixes = (
                "pwd", "ls", "whoami", "date",
                "git status", "git diff", "git log", "git branch",
                "python --version", "python3 --version",
                "node -v", "npm -v", "yarn -v", "pnpm -v",
            )
            if any(c == p or c.startswith(p + " ") for p in safe_prefixes):
                return "safe", ""

            danger_patterns = [
                "rm -rf", "rm -fr", "sudo ", "dd ", "mkfs", "diskutil erase",
                "shutdown", "reboot", ":(){ :|:& };:",
                "chmod -r", "chown -r",
                ">/dev/sd", " /dev/sd",
            ]
            if any(p in c for p in danger_patterns):
                return "danger", f"Comando potencialmente destrutivo: {cmd}"

            risky_patterns = [
                "git push", "git reset --hard", "git clean -fd", "git clean -xdf",
                "docker system prune", "docker volume prune", "docker image prune",
                "npm install", "pnpm install", "yarn install",
                "npm run", "pnpm run", "yarn run",
                "pip install", "pip3 install",
                "composer install", "composer update",
                "brew install", "brew upgrade",
                "kill ", "pkill ",
            ]
            if any(p in c for p in risky_patterns):
                return "risky", f"Comando com impacto: {cmd}"

            return "risky", f"Confirmar execução: {cmd}"

        def guarded_execute(action: str, args: dict) -> tuple[bool, str]:
            """
            Returns (executed, output_or_prompt)
            """
            risk, note = classify_action_risk(action, args)

            if risk == "safe":
                learn_state_from_action(action, args)
                return True, self.SKILLS[action].run(args)

            # salva pendência
            set_pending_action({"action": action, **args})
            set_pending_risk(risk, note)

            if risk == "danger":
                return False, (
                    "⚠️ AÇÃO PERIGOSA detectada.\n"
                    f"{note}\n\n"
                    "Para confirmar, digite exatamente: YES I KNOW\n"
                    "Para cancelar: jarvis no"
                )

            return False, (
                "⚠️ Confirmação necessária.\n"
                f"{note}\n\n"
                "Para confirmar: jarvis yes\n"
                "Para cancelar: jarvis no"
            )

        # -----------------------------
        # Forced routing via prefix
        # -----------------------------
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

        # -----------------------------
        # LOCAL COMMANDS (NO LLM)
        # -----------------------------
        cmd = (user_input or "").strip().lower()

        # confirmar/recusar pendência
        if cmd in ("yes", "y", "confirmar"):
            pending, risk, note = get_pending()
            if not pending:
                return remember("Não há nenhuma ação pendente para confirmar.")

            if risk == "danger":
                return remember("Esta ação é PERIGOSA. Para confirmar, digite exatamente: YES I KNOW")

            action = pending.get("action")
            args = {k: v for k, v in pending.items() if k != "action"}
            set_pending_action(None)

            if action in self.SKILLS:
                ok, out = guarded_execute(action, args)
                return remember(out)
            return remember("Ação pendente inválida.")

        if cmd.replace('"', "").strip().lower() == "yes i know":
            pending, risk, note = get_pending()
            if not pending:
                return remember("Não há nenhuma ação pendente para confirmar.")

            action = pending.get("action")
            args = {k: v for k, v in pending.items() if k != "action"}
            set_pending_action(None)

            if action in self.SKILLS:
                # executa mesmo sendo danger
                learn_state_from_action(action, args)
                out = self.SKILLS[action].run(args)
                return remember(out)

            return remember("Ação pendente inválida.")

        if cmd in ("no", "n", "cancelar isso", "cancel"):
            pending, risk, note = get_pending()
            if not pending:
                return remember("Ok.")
            set_pending_action(None)
            return remember("Cancelado.")

        # limpar memória
        if cmd in ("limpar memoria", "limpar memória", "clear memory", "reset memory"):
            clear_memory()
            return "Memória limpa."

        # status do plano
        if cmd in ("status", "status plano", "plano status"):
            return remember(format_active_plan_status())

        # cancelar plano
        if cmd in ("cancelar", "cancelar plano", "parar", "stop"):
            clear_active_plan()
            return remember("Plano cancelado. Pronto para o próximo comando.")

        # listar etapas
        if cmd in ("listar etapas", "etapas", "listar plano", "mostrar plano"):
            plan, idx = get_active_plan()
            if not plan:
                return remember("Não há plano ativo.")
            lines = []
            for i, p in enumerate(plan):
                mark = "✅" if i < idx else "•"
                step = p.get("step") or p.get("action") or ""
                lines.append(f"{mark} {i+1}. {step}")
            return remember("\n".join(lines))

        # continuar (aceita continue) - step-by-step + risk gate
        if cmd in ("continua", "continuar", "seguir", "next", "continue"):
            plan, idx = get_active_plan()
            if not plan:
                return remember("Não há plano ativo. Diga o que você quer que eu faça.")
            if idx >= len(plan):
                clear_active_plan()
                return remember("Plano já estava completo. Se quiser, descreva um novo objetivo.")

            item = plan[idx]
            action = item.get("action")

            if not action:
                advance_active_plan(1)
                return remember("Passei um passo sem ação. Diga 'continua' novamente.")

            if action == "chat":
                msg = item.get("response") or item.get("t") or ""
                advance_active_plan(1)
                return remember(msg or "Ok.")

            if action in self.SKILLS:
                args = {k: v for k, v in item.items() if k not in ("action", "step")}
                executed, out = guarded_execute(action, args)

                if not executed:
                    # não avança índice, aguarda confirmação
                    return remember(out)

                advance_active_plan(1)

                plan2, idx2 = get_active_plan()
                if idx2 >= len(plan2):
                    clear_active_plan()
                    return remember(out + "\n\n✅ Plano concluído.")
                return remember(out + "\n\n➡️ Diga 'continua' para o próximo passo.")

            advance_active_plan(1)
            return remember(f"Ação desconhecida no plano: {action}. Diga 'continua' para pular.")

        # executar tudo (sem LLM) + risk gate
        if cmd in (
            "executar tudo", "executar todas", "executar plano",
            "run all", "execute all", "executar todas as etapas"
        ):
            plan, idx = get_active_plan()
            if not plan:
                return remember("Não há plano ativo.")

            results = []
            while idx < len(plan):
                item = plan[idx]
                action = item.get("action")

                if not action:
                    advance_active_plan(1)
                    idx += 1
                    continue

                if action == "chat":
                    msg = item.get("response") or item.get("t") or ""
                    if msg:
                        results.append(msg)
                    advance_active_plan(1)
                    idx += 1
                    continue

                if action in self.SKILLS:
                    args = {k: v for k, v in item.items() if k not in ("action", "step")}
                    executed, out = guarded_execute(action, args)

                    if not executed:
                        # pausa e espera confirmação
                        return remember(out)

                    results.append(out)
                    advance_active_plan(1)
                    idx += 1
                    continue

                results.append(f"Ação desconhecida no plano: {action}")
                advance_active_plan(1)
                idx += 1

            clear_active_plan()
            out = "\n".join([r for r in results if r]).strip()
            if not out:
                out = "✅ Plano concluído."
            else:
                out += "\n\n✅ Plano concluído."
            return remember(out)

        # -----------------------------
        # 1) Router (FAST) or forced
        # -----------------------------
        if forced == "fast_reply":
            return remember(user_input)

        if forced in ("brain", "reasoning"):
            r = {"route": forced, "needs_actions": True}
        else:
            try:
                r = self.route(user_input)
            except Exception as e:
                if DEBUG:
                    print("DEBUG ROUTER ERROR:", e)
                r = {"route": "brain", "needs_actions": True}

        # 2) Fast reply (router decided)
        if r["route"] == "fast_reply":
            return remember(r["response"])

        model = r["route"]  # brain ou reasoning

        # 3) Executor (brain/reasoning)
        try:
            d = self.decide(user_input, model=model)
        except Exception as e:
            if DEBUG:
                print("DEBUG EXECUTOR ERROR:", e)
            if model != "reasoning":
                d = self.decide(user_input, model="reasoning")
            else:
                return remember("Não consegui processar seu pedido agora.")

        # -----------------------------
        # FORCED PLAN MODE: plan:/think:/reason:
        # - normaliza actions -> plan
        # - salva plano
        # - executa só 1º passo (step-by-step) + risk gate
        # -----------------------------
        if forced == "reasoning":
            if "plan" not in d and "actions" in d and isinstance(d["actions"], list):
                d["plan"] = []
                for a in d["actions"]:
                    if isinstance(a, dict) and a.get("action"):
                        d["plan"].append({"step": a.get("action"), **a})

            if "plan" in d and isinstance(d["plan"], list):
                plan = d["plan"]

                set_goal(user_input)
                set_active_plan(plan, goal=user_input)

                if not plan:
                    clear_active_plan()
                    return remember("Plano vazio. Diga o que você quer que eu faça.")

                first = plan[0]
                action = first.get("action")

                if not action:
                    advance_active_plan(1)
                    return remember("Plano iniciado, mas o primeiro passo não tinha ação. Diga 'continua'.")

                if action == "chat":
                    msg = first.get("response") or first.get("t") or ""
                    advance_active_plan(1)
                    return remember((msg or "Ok.") + "\n\n➡️ Diga 'continua' para prosseguir.")

                if action in self.SKILLS:
                    args = {k: v for k, v in first.items() if k not in ("action", "step")}
                    executed, out = guarded_execute(action, args)

                    if not executed:
                        return remember(out)

                    advance_active_plan(1)
                    return remember(out + "\n\n➡️ Diga 'continua' para o próximo passo.")

                advance_active_plan(1)
                return remember(f"Ação desconhecida no plano: {action}. Diga 'continua' para pular.")

        # Plan mode normal (caso LLM devolva plan explicitamente) - step-by-step + risk gate
        if "plan" in d and isinstance(d["plan"], list):
            plan = d["plan"]

            set_goal(user_input)
            set_active_plan(plan, goal=user_input)

            if not plan:
                clear_active_plan()
                return remember("Plano vazio. Diga o que você quer fazer.")

            first = plan[0]
            action = first.get("action")

            if not action:
                advance_active_plan(1)
                return remember("Plano iniciado, mas o primeiro passo não tinha ação. Diga 'continua'.")

            if action == "chat":
                msg = first.get("response") or first.get("t") or ""
                advance_active_plan(1)
                return remember((msg or "Ok.") + "\n\n➡️ Diga 'continua' para prosseguir.")

            if action in self.SKILLS:
                args = {k: v for k, v in first.items() if k not in ("action", "step")}
                executed, out = guarded_execute(action, args)

                if not executed:
                    return remember(out)

                advance_active_plan(1)
                return remember(out + "\n\n➡️ Diga 'continua' para o próximo passo.")

            advance_active_plan(1)
            return remember(f"Ação desconhecida no plano: {action}. Diga 'continua' para pular.")

        # Multi actions (normal) - aqui mantém como antes (executa tudo) + risk gate por ação
        if "actions" in d and isinstance(d["actions"], list):
            results = []
            for step in d["actions"]:
                action = step.get("action")
                if action in self.SKILLS:
                    args = {k: v for k, v in step.items() if k != "action"}
                    executed, out = guarded_execute(action, args)
                    if not executed:
                        return remember(out)
                    results.append(out)
                else:
                    results.append(f"Ação desconhecida: {action}")
            return remember("\n".join(results))

        # Single action / chat
        action = d.get("action")

        if action == "chat":
            return remember(d.get("response", ""))

        if action in self.SKILLS:
            args = {k: v for k, v in d.items() if k != "action"}
            executed, out = guarded_execute(action, args)
            return remember(out)

        return remember("Não entendi como executar isso ainda.")