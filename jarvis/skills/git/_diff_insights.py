"""
_diff_insights.py — Heurísticas para gerar insights sobre um git diff.

Não usa LLM — processamento local, instantâneo.
O campo `level` pode ser: "ok" | "info" | "warning" | "error"
"""
from __future__ import annotations


# ── Padrões de risco por categoria ───────────────────────────────────────────

_SECURITY_PATTERNS = [
    "auth", "login", "permission", "middleware", "policy", "security",
    "oauth", "token", "credential", "password", "secret", "jwt", "session",
    "encrypt", "decrypt", "hash", "signature", "key",
]

_INFRA_PATTERNS = [
    ".env", "config", "docker", "dockerfile", ".yml", ".yaml",
    "migration", "schema", "settings", "database", "nginx",
    "deploy", "ci", ".github", "workflow", "terraform", "ansible",
]

_LOGIC_PATTERNS = [
    "controller", "service", "route", "handler", "api",
    "processor", "manager", "repository", "usecase",
]

_TEST_PATTERNS = [
    "test", "spec", "__test__", ".test.", ".spec.",
]

_UI_PATTERNS = [
    "component", ".css", ".scss", ".tsx", ".vue", ".svelte",
    "style", ".html", "template", "page",
]


def risk_level_for_files(files: list[str]) -> str:
    """
    Calcula nível de risco geral ('high' | 'medium' | 'low') baseado nos arquivos.
    """
    joined = " ".join(f.lower() for f in files)
    if any(p in joined for p in _SECURITY_PATTERNS):
        return "high"
    if any(p in joined for p in _INFRA_PATTERNS):
        return "medium"
    return "low"


def compute_insights(
    file_stats: list[dict],
    diff_sections: list[dict],  # não usados nesta versão, reservado para LLM
) -> list[dict]:
    """
    Gera lista de insights heurísticos baseados nos arquivos alterados.

    Retorna:
        [{level: "ok"|"info"|"warning"|"error", message: str}]
    """
    insights: list[dict] = []
    files_lower = [f["file"].lower() for f in file_stats]
    file_str = " ".join(files_lower)

    # ── Segurança ─────────────────────────────────────────────────────────────
    sec_matches = [f for f in files_lower if any(p in f for p in _SECURITY_PATTERNS)]
    if sec_matches:
        names = ", ".join(sec_matches[:3])
        insights.append({
            "level": "warning",
            "message": f"Arquivos sensíveis detectados: {names}. Revise com atenção redobrada.",
        })

    # ── Infraestrutura / Config ───────────────────────────────────────────────
    infra_matches = [f for f in files_lower if any(p in f for p in _INFRA_PATTERNS)]
    if infra_matches:
        names = ", ".join(infra_matches[:3])
        insights.append({
            "level": "info",
            "message": f"Arquivos de configuração/infra alterados: {names}.",
        })

    # ── Mudanças muito grandes ────────────────────────────────────────────────
    large = [f for f in file_stats if f["additions"] + f["deletions"] > 100]
    if large:
        names = ", ".join(f["file"] for f in large[:3])
        insights.append({
            "level": "info",
            "message": (
                f"{'Arquivo' if len(large) == 1 else 'Arquivos'} com >100 linhas alteradas: {names}. "
                "Considere revisar em partes."
            ),
        })

    # ── Muitos arquivos ───────────────────────────────────────────────────────
    if len(file_stats) > 10:
        insights.append({
            "level": "info",
            "message": (
                f"{len(file_stats)} arquivos alterados. "
                "Considere dividir em commits menores para facilitar revisão."
            ),
        })

    # ── Lógica de negócio ─────────────────────────────────────────────────────
    logic_matches = [f for f in files_lower if any(p in f for p in _LOGIC_PATTERNS)]
    if logic_matches:
        names = ", ".join(logic_matches[:3])
        insights.append({
            "level": "info",
            "message": f"Lógica de negócio alterada: {names}. Verifique cobertura de testes.",
        })

    # ── Positivo: testes incluídos ────────────────────────────────────────────
    test_matches = [f for f in files_lower if any(p in f for p in _TEST_PATTERNS)]
    if test_matches:
        insights.append({
            "level": "ok",
            "message": f"Testes incluídos no diff ({len(test_matches)} arquivo(s)). Boa prática.",
        })

    # ── Positivo: só UI ───────────────────────────────────────────────────────
    ui_matches = [f for f in files_lower if any(p in f for p in _UI_PATTERNS)]
    if ui_matches and len(ui_matches) == len(file_stats):
        insights.append({
            "level": "ok",
            "message": "Alterações concentradas em UI/componentes — risco geral baixo.",
        })

    # ── Fallback: nenhum padrão detectado ────────────────────────────────────
    if not insights:
        insights.append({
            "level": "ok",
            "message": "Nenhum padrão de risco óbvio detectado nas alterações.",
        })

    return insights
