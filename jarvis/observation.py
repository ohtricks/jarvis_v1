"""
Observa o resultado de um step executado e extrai sinais para tomada de decisão.
Não faz nenhuma ação — só lê e classifica.
"""


def observe_step(action: str, args: dict, output: str, state: str) -> dict:
    """
    Analisa o output de um step e detecta sinais conhecidos.

    Retorna um dict com:
      - action: str
      - command: str (para run_shell)
      - output: str
      - state: str (done/failed/blocked/empty)
      - signals: list[str]
    """
    out = (output or "").lower()
    command = (args.get("command") or "") if args else ""

    signals: list[str] = []

    if "command not found" in out:
        signals.append("cmd_not_found")

    if "not a git repository" in out:
        signals.append("not_git_repo")

    if "permission denied" in out:
        signals.append("permission_denied")

    if "already exists" in out:
        signals.append("already_exists")

    if "merge conflict" in out or ("conflict" in out and ("unresolved" in out or "both modified" in out)):
        signals.append("merge_conflict")

    if "untracked files" in out:
        signals.append("untracked_files")

    if "nothing to commit" in out:
        signals.append("nothing_to_commit")

    if "no such file or directory" in out:
        signals.append("no_such_file")

    if "fatal:" in out and not signals:
        signals.append("git_fatal")

    if "error:" in out and not signals:
        signals.append("generic_error")

    if state == "failed" and not signals:
        signals.append("unknown_error")

    return {
        "action": action,
        "command": command,
        "output": output,
        "state": state,
        "signals": signals,
    }


def should_propose_recovery(observation: dict) -> bool:
    """
    Retorna True apenas quando vale a pena propor um recovery plan.
    Primeira versão: só para run_shell com falha.
    """
    return (
        observation.get("state") == "failed"
        and observation.get("action") == "run_shell"
    )
