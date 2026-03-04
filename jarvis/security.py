"""
Camada de segurança local — sem telemetry, sem logging, sem LLM.
Usada pelo Gmail OAuth Wizard e outros fluxos que lidam com credentials.
"""

_SENSITIVE_KEYS = [
    "client_secret",
    "refresh_token",
    "access_token",
    "private_key",
    "-----BEGIN",
    '"token":',
    "auth_uri",
    "client_id",
    "token_uri",
    "client_email",
    "private_key_id",
]


def is_sensitive_text(s: str) -> bool:
    """Retorna True se o texto contiver padrões que indicam credenciais ou tokens."""
    sl = (s or "").lower()
    return any(p.lower() in sl for p in _SENSITIVE_KEYS)


def redact(s: str) -> str:
    """Mascara texto sensível. Seguro para usar em logs/telemetry."""
    return "***REDACTED***" if is_sensitive_text(s) else s


def secure_prompt(label: str, multiline: bool = False) -> str:
    """
    Lê input do usuário diretamente via stdin.

    GARANTIAS DE SEGURANÇA:
    - NUNCA chama telemetry, add_turn ou qualquer logger.
    - O valor retornado não passa pelo pipeline normal do Jarvis.
    - Destinado apenas para escrita em arquivo local.

    multiline=True: aceita múltiplas linhas até o usuário digitar uma
    linha contendo apenas 'EOF'.
    """
    print(label, flush=True)
    if multiline:
        print(
            "\n┌─ Cole o JSON abaixo ───────────────────────────────────────────┐\n"
            "│  Depois de colar, pressione Enter para ir à próxima linha,     │\n"
            "│  e então digite  EOF  (sozinho) e pressione Enter para finalizar│\n"
            "└────────────────────────────────────────────────────────────────┘",
            flush=True,
        )
        lines: list[str] = []
        try:
            while True:
                try:
                    line = input()
                except EOFError:
                    break
                if line.strip() == "EOF":
                    break
                lines.append(line)
        except KeyboardInterrupt:
            raise  # re-raise para o wizard tratar
        return "\n".join(lines)
    try:
        return input("> ").strip()
    except KeyboardInterrupt:
        raise
