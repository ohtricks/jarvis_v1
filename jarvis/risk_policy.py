"""
Política de risco editável — persistida em ~/.jarvis/risk_policy.json.

Backward compatible: se o arquivo não existir, usa os defaults internos.
O usuário (via comandos Jarvis) pode adicionar padrões sem mexer no código-fonte.
"""

import json
from pathlib import Path

POLICY_PATH = Path.home() / ".jarvis" / "risk_policy.json"

# Defaults idênticos às listas hardcoded do risk.py original +
# git add / git commit / git stash como safe (operações comuns reversíveis).
_DEFAULTS: dict = {
    "safe_prefixes": [
        "pwd", "ls", "whoami", "date",
        "git status", "git diff", "git log", "git branch",
        "git add", "git commit", "git stash",
        "python --version", "python3 --version",
        "node -v", "npm -v", "yarn -v", "pnpm -v",
    ],
    "risky_patterns": [
        "git reset --hard",
        "git clean -fd",
        "git clean -xdf",
        "docker system prune",
        "docker volume prune",
        "docker image prune",
        "npm install", "pnpm install", "yarn install",
        "npm run", "pnpm run", "yarn run",
        "pip install", "pip3 install",
        "composer install", "composer update",
        "brew install", "brew upgrade",
        "kill ", "pkill ",
    ],
    "danger_patterns": [
        "rm -rf", "rm -fr",
        "sudo ",
        "dd ",
        "mkfs",
        "diskutil erase",
        "shutdown", "reboot",
        ":(){ :|:& };:",
        "chmod -r", "chown -r",
        ">/dev/sd", " /dev/sd",
    ],
}


def ensure_policy_shape(data: dict) -> dict:
    """Garante que todas as chaves existem; preenche com defaults se ausente."""
    result = {}
    for key in ("safe_prefixes", "risky_patterns", "danger_patterns"):
        v = data.get(key)
        result[key] = list(v) if isinstance(v, list) else list(_DEFAULTS[key])
    return result


def load_policy() -> dict:
    if not POLICY_PATH.exists():
        return ensure_policy_shape({})
    try:
        data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        return ensure_policy_shape(data)
    except Exception:
        return ensure_policy_shape({})


def save_policy(policy: dict) -> None:
    POLICY_PATH.parent.mkdir(parents=True, exist_ok=True)
    POLICY_PATH.write_text(
        json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add_to_policy(bucket: str, value: str) -> bool:
    """
    Adiciona value ao bucket especificado (deduplica).
    bucket ∈ {"safe_prefixes", "risky_patterns", "danger_patterns"}
    Retorna True se foi adicionado, False se inválido ou já existia.
    """
    if bucket not in ("safe_prefixes", "risky_patterns", "danger_patterns"):
        return False
    value = value.strip()
    if not value:
        return False
    policy = load_policy()
    lst = policy.get(bucket, [])
    if value in lst:
        return False  # já existe
    lst.append(value)
    policy[bucket] = lst
    save_policy(policy)
    return True
