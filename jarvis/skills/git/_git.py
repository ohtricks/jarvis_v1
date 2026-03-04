import os
import subprocess
from ...memory import get_state


def get_cwd(args: dict) -> str:
    cwd = args.get("cwd") or (get_state().get("cwd")) or os.getcwd()
    return os.path.expanduser(os.path.expandvars(str(cwd)))


def run_git(cmd: str, cwd: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        combined = (out + "\n" + err).strip() if err else out
        return result.returncode == 0, combined or ("ok" if result.returncode == 0 else "sem output")
    except Exception as e:
        return False, f"Erro ao executar git: {e}"


def ensure_git_repo(cwd: str) -> tuple[bool, str]:
    ok, _ = run_git("git rev-parse --is-inside-work-tree", cwd)
    if not ok:
        return False, f"Não parece ser um repositório git no cwd atual: {cwd}"
    return True, ""
