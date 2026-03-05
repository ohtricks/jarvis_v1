"""
Gmail OAuth Wizard — fluxo interativo 100% local, sem LLM.

SEGURANÇA:
- Toda leitura de dados sensíveis usa secure_prompt() ou input() direto.
- O conteúdo de client_secret.json NUNCA é printado, logado ou enviado para IA.
- Este módulo NUNCA chama add_turn(), telemetry.debug_set() ou qualquer logger.
"""

import json
import shutil
from pathlib import Path

from ..security import secure_prompt, is_sensitive_text
from ..integrations.google.gmail_api import (
    gmail_auth_interactive,
    NEW_CREDS_DIR,
    normalize_alias,
)
from pathlib import Path as _Path


def _alias_dir(alias: str) -> _Path:
    return NEW_CREDS_DIR / normalize_alias(alias)

_REQUIRED_FIELDS = {"client_id", "client_secret", "token_uri"}


def explain_gmail_oauth_requirements() -> str:
    return (
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📧  Configuração Gmail OAuth\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Para ler seus emails, o Jarvis precisa de um\n"
        "OAuth Client ID do Google. Siga os passos:\n\n"
        "  1. Acesse: console.cloud.google.com\n"
        "  2. Crie ou selecione um projeto\n"
        "  3. APIs e Serviços → Biblioteca → habilite 'Gmail API'\n"
        "  4. Credenciais → Criar credenciais → ID do cliente OAuth\n"
        "     Tipo: 'App para computador' (Desktop app)\n"
        "  5. Baixe o arquivo JSON (client_secret_*.json)\n\n"
        "⚠️  Seus dados ficam APENAS no seu computador.\n"
        "    Nada é enviado para IA ou servidores externos.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )


def _normalize_alias(raw: str) -> str:
    alias = (raw or "").strip().lower().replace(" ", "_")
    return alias or "default"


def _validate_client_secret(content: str) -> tuple[bool, str, dict]:
    """
    Valida JSON do client_secret. Retorna (ok, erro, dados).
    NÃO loga nem printa o conteúdo.
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return False, f"JSON inválido: {e}", {}

    # O Google wrap em {"installed":{...}} ou {"web":{...}}
    inner = data.get("installed") or data.get("web") or data
    missing = _REQUIRED_FIELDS - inner.keys()
    if missing:
        return False, f"Campos ausentes no JSON: {', '.join(sorted(missing))}", {}

    return True, "", inner


def _save_client_secret(alias: str, content: str) -> Path:
    dest_dir = _alias_dir(alias)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "client_secret.json"
    # Escreve diretamente — sem passar pelo pipeline do Jarvis
    dest.write_text(content, encoding="utf-8")
    return dest


def run_gmail_oauth_wizard(
    initial_alias: str | None = None,
) -> tuple[bool, str]:
    """
    Wizard interativo para autenticar Gmail via OAuth.

    Retorna (success: bool, mensagem: str).
    Ctrl+C em qualquer ponto cancela o wizard graciosamente.
    Fluxo:
      1. Explica requisitos
      2. Verifica se usuário já tem client_secret.json
      3. Coleta alias
      4. Coleta credencial (path ou paste)
      5. Roda OAuth → salva token
    """
    try:
        return _run_wizard_inner(initial_alias)
    except KeyboardInterrupt:
        print("\n\nWizard cancelado pelo usuário (Ctrl+C).", flush=True)
        return False, "Configuração cancelada. Execute 'auth gmail' quando quiser tentar novamente."


def _run_wizard_inner(
    initial_alias: str | None = None,
) -> tuple[bool, str]:
    """Corpo do wizard — chamado por run_gmail_oauth_wizard com tratamento de Ctrl+C."""
    print(explain_gmail_oauth_requirements())

    # ── Passo 1: Verificar se já tem client_secret ────────────────────────────
    resp = secure_prompt("Você já tem o arquivo client_secret.json? (sim/não)").lower()
    has_secret = resp in ("sim", "s", "yes", "y")

    if not has_secret:
        print(
            "\nPara obter o arquivo:\n"
            "  • console.cloud.google.com → seu projeto\n"
            "  • APIs e Serviços → Credenciais → Criar → OAuth (Desktop app)\n"
            "  • Clique em Download JSON\n"
        )
        resp2 = secure_prompt(
            "Quer cancelar por agora? (sim para cancelar / não para continuar)"
        ).lower()
        if resp2 in ("sim", "s", "yes", "y"):
            return False, "Configuração cancelada. Execute 'auth gmail' quando tiver o arquivo."

    # ── Passo 2: Alias ────────────────────────────────────────────────────────
    if initial_alias:
        alias = _normalize_alias(initial_alias)
        print(f"Alias: {alias}")
    else:
        raw_alias = secure_prompt(
            "\nQual apelido para essa conta?\n(ex: empresa, pessoal) [default]:"
        )
        alias = _normalize_alias(raw_alias) or "default"

    # ── Passo 3: Método de fornecer credencial ────────────────────────────────
    print(
        "\nComo deseja fornecer as credenciais?\n"
        "  1) Informar o caminho do arquivo\n"
        "  2) Colar o JSON aqui no terminal"
    )

    for _attempt in range(3):
        method = secure_prompt("Escolha (1/2):").strip()
        if method in ("1", "2"):
            break
        print("Digite 1 ou 2.")
    else:
        return False, "Número de tentativas excedido. Use 'auth gmail' para tentar novamente."

    client_secret_path: Path | None = None
    secret_content: str = ""

    if method == "1":
        # ── Método A: caminho do arquivo ──────────────────────────────────────
        raw_path = secure_prompt("\nInforme o caminho do arquivo client_secret.json:")
        file_path = Path(raw_path).expanduser()

        if not file_path.exists():
            return False, f"Arquivo não encontrado: {file_path}"

        try:
            secret_content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return False, f"Erro ao ler arquivo: {e}"

        ok, err, _ = _validate_client_secret(secret_content)
        if not ok:
            return False, f"Credencial inválida: {err}"

        # Copia para diretório do alias (não loga o path completo original)
        client_secret_path = _save_client_secret(alias, secret_content)
        print(f"\n✓ Credencial salva para alias '{alias}'.")

    else:
        # ── Método B: colar JSON ──────────────────────────────────────────────
        secret_content = secure_prompt(
            "\nCole o conteúdo do client_secret.json:", multiline=True
        )

        ok, err, _ = _validate_client_secret(secret_content)
        if not ok:
            return False, f"JSON inválido: {err}"

        client_secret_path = _save_client_secret(alias, secret_content)
        # NÃO imprimir o conteúdo — apenas confirmar salvamento
        print(f"\n✓ Credencial salva para alias '{alias}'.")

    # ── Passo 4: OAuth flow ───────────────────────────────────────────────────
    print("\nAbrindo o navegador para autenticação com o Google...\n")
    success, msg = gmail_auth_interactive(alias, client_secret_path)

    return success, msg
