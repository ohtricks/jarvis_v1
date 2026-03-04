from .open_app import OpenAppSkill
from .open_url import OpenUrlSkill
from .run_shell import RunShellSkill
from .capabilities import Capability, format_capabilities_for_prompt


def build_skills(execute: bool = False):
    """Retorna dict action->skill_obj. Contrato imutável — executor.py depende disso."""
    return {
        "open_app": OpenAppSkill(execute=execute),
        "open_url": OpenUrlSkill(execute=execute),
        "run_shell": RunShellSkill(execute=execute),
    }


# ── Catálogo de capabilities ──────────────────────────────────────────────────
# Adicione aqui ao criar novas skills. Os action names DEVEM bater com as chaves
# de build_skills() (ou "chat" para a resposta direta do executor_llm).

_CATALOG: list[Capability] = [
    Capability(
        name="open_app",
        namespace="system",
        title="Abrir aplicativo",
        description="Abre um aplicativo no macOS pelo nome.",
        args_schema={"app": "string"},
        examples=["abra o chrome", "abra o vscode", "abra o slack"],
        risk="safe",
    ),
    Capability(
        name="open_url",
        namespace="browser",
        title="Abrir URL no navegador",
        description="Abre uma URL no navegador padrão ou especificado.",
        args_schema={"url": "string", "browser": "string?"},
        examples=["abra https://gmail.com", "abra o youtube no chrome"],
        risk="safe",
    ),
    Capability(
        name="run_shell",
        namespace="dev",
        title="Executar comando no terminal",
        description="Executa um comando shell (allowlist de prefixos seguros).",
        args_schema={"command": "string", "cwd": "string?"},
        examples=["git status", "npm install", "ls -la"],
        risk="risky",
    ),
    Capability(
        name="chat",
        namespace="meta",
        title="Resposta direta",
        description="Retorna texto diretamente sem executar ação (limitação ou conversa).",
        args_schema={"response": "string"},
        examples=["o que é Python?", "explique git rebase"],
        risk="safe",
    ),
]


def get_capabilities() -> list[Capability]:
    """Retorna lista completa de capabilities registradas."""
    return list(_CATALOG)


def get_capabilities_text() -> str:
    """Texto compacto pronto para inserir em system prompts."""
    return format_capabilities_for_prompt(_CATALOG)


def find_capability(action: str) -> Capability | None:
    """Busca uma capability pelo action name. Retorna None se não encontrar."""
    for cap in _CATALOG:
        if cap.name == action:
            return cap
    return None
