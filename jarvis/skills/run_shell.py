import os
import re
import subprocess
from datetime import datetime, timezone
from .base import Skill
from .. import shell_policy as _sp
from ..memory import set_pending_shell_allow_proposal

# Operadores que encadeiam comandos shell (vetores de injeção).
# Nota: pipe `|` não está aqui — tem usos legítimos amplamente comuns.
_CHAIN_RE = re.compile(r'(?:;|&&|\|\|)')


def _base_prefix(cmd: str) -> str:
    """Extrai até 2 tokens não-flag como prefixo base. Ex: 'git commit -m x' → 'git commit'."""
    tokens = cmd.strip().split()
    base: list[str] = []
    for token in tokens:
        if token.startswith("-"):
            break
        base.append(token)
        if len(base) >= 2:
            break
    return " ".join(base)


def _split_compound(cmd: str) -> list[str]:
    """Divide comando composto por ; && || em subcmds individuais."""
    parts = _CHAIN_RE.split(cmd)
    return [p.strip() for p in parts if p.strip()]


class RunShellSkill(Skill):
    name = "run_shell"

    def __init__(self, execute: bool = False):
        self.execute = execute

    def run(self, args: dict):
        command = (args.get("command") or "").strip()
        cwd = args.get("cwd")

        if not command:
            return "Nenhum comando informado."

        # Expandir ~ e variáveis de ambiente no cwd para evitar "No such file"
        if cwd:
            cwd = os.path.expanduser(os.path.expandvars(cwd))

        # ── Shell policy gate ────────────────────────────────────────────────
        # Detecta comandos compostos (injeção de shell via ; && ||).
        # Cada subcmd é validado separadamente contra a allowlist.
        sub_cmds = _split_compound(command)
        if len(sub_cmds) > 1:
            for sub in sub_cmds:
                sub_allowed, sub_reason, _ = _sp.is_allowed(sub)
                if not sub_allowed:
                    suggested = _base_prefix(sub)
                    set_pending_shell_allow_proposal({
                        "command": sub,
                        "suggested_prefix": suggested,
                        "ts": datetime.now(timezone.utc).isoformat(),
                    })
                    return (
                        f"Bloqueado por segurança: subcmd '{sub}' não está na allowlist. {sub_reason}\n"
                        f"Posso adicionar '{suggested}' na allowlist.\n"
                        f"Para adicionar: permitir {suggested}\n"
                        f"Para cancelar: cancelar"
                    )
        else:
            allowed, reason, matched = _sp.is_allowed(command)
            if not allowed:
                suggested = _base_prefix(command)
                set_pending_shell_allow_proposal({
                    "command": command,
                    "suggested_prefix": suggested,
                    "ts": datetime.now(timezone.utc).isoformat(),
                })
                return (
                    f"Bloqueado por segurança. {reason}\n"
                    f"Posso adicionar '{suggested}' na allowlist.\n"
                    f"Para adicionar: permitir {suggested}\n"
                    f"Para cancelar: cancelar"
                )

        if not self.execute:
            return f"(dry-run) Eu executaria:\n{command}"

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
            )
            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()

            if result.returncode == 0:
                return out if out else "Comando executado com sucesso."
            else:
                msg = out if out else ""
                if err:
                    msg = (msg + "\n" + err).strip()
                return f"Erro (code {result.returncode}):\n{msg}" if msg else f"Erro (code {result.returncode})."

        except Exception as e:
            return f"Erro ao executar comando: {e}"
