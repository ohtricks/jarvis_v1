import os
import subprocess
from datetime import datetime


def collect_system_context() -> dict:
    """
    Captura contexto do sistema operacional.
    Nunca levanta exceção — erros são ignorados silenciosamente.
    """
    ctx = {}

    try:
        ctx["cwd"] = os.getcwd()
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=2,
        )
        ctx["git_repo"] = result.returncode == 0
    except Exception:
        ctx["git_repo"] = False

    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=2,
        )
        branch = result.stdout.strip()
        if branch:
            ctx["git_branch"] = branch
    except Exception:
        pass

    try:
        ctx["timestamp"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass

    return ctx


def update_context_state() -> None:
    """
    Atualiza memory.state com contexto atual do sistema.
    Só sobrescreve campos de contexto (cwd, git_repo, git_branch).
    Nunca levanta exceção.
    """
    try:
        from .memory import get_state, set_state

        ctx = collect_system_context()
        current = get_state()

        patch = {
            f: ctx[f]
            for f in ("cwd", "git_repo", "git_branch")
            if f in ctx and ctx[f] != current.get(f)
        }
        if patch:
            set_state(patch)
    except Exception:
        pass
