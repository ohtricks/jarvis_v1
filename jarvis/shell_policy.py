"""
Allowlist/blocklist dinâmica para run_shell — persistida em ~/.jarvis/shell_policy.json.

Backward compatible: se o arquivo não existir, usa os defaults atuais do run_shell.
"""

import json
from pathlib import Path

SHELL_POLICY_PATH = Path.home() / ".jarvis" / "shell_policy.json"

# Defaults idênticos ao comportamento atual + git add/commit/stash e cd
_DEFAULTS: dict = {
    "allowlist_prefixes": [
        # sistema
        "ls", "pwd", "whoami", "date", "cd", "cat", "echo",
        "mkdir", "touch", "cp", "mv", "grep", "find", "open",
        # git (subcomandos comuns como safe)
        "git",
        "git status", "git diff", "git log", "git branch",
        "git add", "git commit", "git stash",
        # linguagens
        "python", "python3", "pip", "pip3",
        "node", "npm", "pnpm", "yarn",
        "php", "composer",
        # infra
        "docker", "docker-compose",
        # editor
        "code",
        # curl para dev
        "curl",
    ],
    "blocklist_patterns": [
        # destrutivos absolutos
        " rm ", " rm-", " rm\t", " rm\n", " rm/",
        "sudo",
        "shutdown", "reboot",
        "mkfs", " dd ",
        "killall", "kill -9",
        ":(){",   # fork bomb
    ],
}


def _ensure_dir() -> None:
    SHELL_POLICY_PATH.parent.mkdir(parents=True, exist_ok=True)


def _ensure_shape(data: dict) -> dict:
    result = {}
    for key in ("allowlist_prefixes", "blocklist_patterns"):
        v = data.get(key)
        result[key] = list(v) if isinstance(v, list) else list(_DEFAULTS[key])
    return result


def load_policy() -> dict:
    if not SHELL_POLICY_PATH.exists():
        return _ensure_shape({})
    try:
        data = json.loads(SHELL_POLICY_PATH.read_text(encoding="utf-8"))
        return _ensure_shape(data)
    except Exception:
        return _ensure_shape({})


def save_policy(policy: dict) -> None:
    _ensure_dir()
    SHELL_POLICY_PATH.write_text(
        json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def is_allowed(command: str) -> tuple[bool, str, str]:
    """
    Retorna (allowed, reason, matched) onde matched:
      "blocklist"           — padrão bloqueado (nunca permitir)
      "allowlist_prefix"    — bate em prefixo multi-palavra
      "allowlist_first"     — bate no primeiro token
      "not_found"           — não encontrado na allowlist
    """
    policy = load_policy()
    cmd = command.strip()
    c_space = f" {cmd.lower()} "

    # 1. Blocklist tem precedência absoluta
    for pattern in policy.get("blocklist_patterns", []):
        if pattern in c_space:
            return False, f"Padrão bloqueado: {pattern.strip()}", "blocklist"

    prefixes: list[str] = policy.get("allowlist_prefixes", [])
    c = cmd.lower()

    # 2. Prefixos multi-palavra (mais específicos primeiro)
    multi = sorted([p for p in prefixes if " " in p], key=len, reverse=True)
    for prefix in multi:
        if c == prefix or c.startswith(prefix + " "):
            return True, "", "allowlist_prefix"

    # 3. Primeiro token
    first = cmd.split()[0] if cmd.split() else ""
    single = [p for p in prefixes if " " not in p]
    if first and first in single:
        return True, "", "allowlist_first"

    return False, f"Comando '{first or cmd}' nao esta na allowlist.", "not_found"


def add_allow_prefix(prefix: str) -> bool:
    """Adiciona prefix à allowlist (dedupe). Retorna True se adicionado."""
    prefix = prefix.strip()
    if not prefix:
        return False
    policy = load_policy()
    lst: list[str] = policy.get("allowlist_prefixes", [])
    if prefix in lst:
        return False
    lst.append(prefix)
    policy["allowlist_prefixes"] = lst
    save_policy(policy)
    return True
