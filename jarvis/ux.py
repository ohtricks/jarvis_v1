def ux_stage(label: str, detail: str | None = None) -> str:
    return f"→ {label}: {detail}" if detail else f"→ {label}"


def ux_next_steps(has_blocked: bool) -> str:
    if not has_blocked:
        return ""
    return (
        "➡️  Para confirmar: sim / não  (ação perigosa exige: YES I KNOW)\n"
        "➡️  Para continuar manualmente: continue\n"
        "➡️  Para rodar até o próximo bloqueio: executar tudo"
    )


def ux_format_response(stages: list[str], body: str, blocked: bool) -> str:
    parts = []
    if stages:
        parts.append("\n".join(stages[:8]))
    if body and body.strip():
        parts.append(body.strip())
    next_steps = ux_next_steps(blocked)
    if next_steps:
        parts.append(next_steps)
    return "\n\n".join([p for p in parts if p]).strip()
