from dataclasses import dataclass, field


@dataclass
class Capability:
    name: str           # action name usado no JSON (ex: "open_app")
    namespace: str      # domínio funcional (ex: "system", "browser", "dev")
    title: str          # rótulo humano curto
    description: str    # 1 frase
    args_schema: dict   # {arg_name: "type" ou "type?"} — "?" = opcional
    examples: list[str] = field(default_factory=list)  # até 3 exemplos naturais
    risk: str = "risky" # "safe" | "risky" | "danger"
    version: str | None = None


def format_capabilities_for_prompt(caps: list[Capability]) -> str:
    """
    Gera texto compacto para inserir em system prompts.

    Formato:
      CAPABILITIES:
      - system.open_app(app: string) — Abrir um aplicativo no sistema.
        ex: "abra o chrome", "abra o vscode"
    """
    if not caps:
        return ""

    lines = ["CAPABILITIES:"]
    for cap in caps:
        arg_parts = []
        for k, v in cap.args_schema.items():
            optional = v.endswith("?")
            base_type = v.rstrip("?")
            if optional:
                arg_parts.append(f"{k}?: {base_type}")
            else:
                arg_parts.append(f"{k}: {base_type}")
        args_str = ", ".join(arg_parts)
        lines.append(f"- {cap.namespace}.{cap.name}({args_str}) — {cap.description}")
        if cap.examples:
            exs = ", ".join(f'"{e}"' for e in cap.examples[:2])
            lines.append(f"  ex: {exs}")

    return "\n".join(lines)
