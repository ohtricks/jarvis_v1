"""
Outlook OAuth Wizard — fluxo interativo 100% local, sem LLM.

SEGURANÇA:
- Toda leitura de dados sensíveis usa secure_prompt().
- O Client ID é salvo localmente em ~/.jarvis/credentials/microsoft/outlook/<alias>/client_id.txt
- O token NUNCA é printado, logado ou enviado para IA.
- Este módulo NUNCA chama add_turn(), telemetry.debug_set() ou qualquer logger.
- Usa Device Code Flow: exibe código + URL para o usuário autenticar no browser.
"""

from ..security import secure_prompt
from ..integrations.microsoft.outlook_api import (
    outlook_auth_interactive,
    CREDS_DIR,
    normalize_alias,
)


def _normalize_alias(raw: str) -> str:
    alias = (raw or "").strip().lower().replace(" ", "_")
    return alias or "default"


def explain_outlook_oauth_requirements() -> str:
    return (
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📧  Configuração Outlook OAuth (Microsoft Graph)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Para ler seus emails, o Jarvis precisa de um\n"
        "App registrado no Azure Portal. Siga os passos:\n\n"
        "  1. Acesse: portal.azure.com\n"
        "  2. Pesquise 'App registrations' e clique em '+ New registration'\n"
        "  3. Nome: qualquer (ex: Jarvis)\n"
        "     Tipo de conta: 'Accounts in any organizational directory\n"
        "                     and personal Microsoft accounts'\n"
        "  4. Em 'Authentication' → 'Add a platform' → 'Mobile and desktop'\n"
        "     Marque: https://login.microsoftonline.com/common/oauth2/nativeclient\n"
        "  5. Copie o 'Application (client) ID' da visão geral do app\n\n"
        "⚠️  Seus dados ficam APENAS no seu computador.\n"
        "    Nada é enviado para IA ou servidores externos.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )


def run_outlook_oauth_wizard(
    initial_alias: str | None = None,
) -> tuple[bool, str]:
    """
    Wizard interativo para autenticar Outlook via OAuth Device Code Flow.

    Retorna (success: bool, mensagem: str).
    Ctrl+C em qualquer ponto cancela o wizard graciosamente.
    Fluxo:
      1. Explica requisitos (Azure Portal)
      2. Coleta alias
      3. Coleta Client ID
      4. Executa Device Code Flow → salva token
    """
    try:
        return _run_wizard_inner(initial_alias)
    except KeyboardInterrupt:
        print("\n\nWizard cancelado pelo usuário (Ctrl+C).", flush=True)
        return False, "Configuração cancelada. Execute 'auth outlook' quando quiser tentar novamente."


def _run_wizard_inner(
    initial_alias: str | None = None,
) -> tuple[bool, str]:
    """Corpo do wizard — chamado por run_outlook_oauth_wizard com tratamento de Ctrl+C."""
    print(explain_outlook_oauth_requirements())

    # ── Verificar se msal está instalado ──────────────────────────────────────
    try:
        import msal  # noqa: F401
    except ImportError:
        return False, (
            "Dependência ausente. Instale com:\n"
            "  pip install msal\n\n"
            "Depois execute novamente: auth outlook"
        )

    # ── Alias ─────────────────────────────────────────────────────────────────
    if initial_alias:
        alias = _normalize_alias(initial_alias)
        print(f"Alias: {alias}")
    else:
        raw_alias = secure_prompt(
            "\nQual apelido para essa conta Outlook?\n(ex: empresa, pessoal) [default]:"
        )
        alias = _normalize_alias(raw_alias) or "default"

    # ── Client ID ─────────────────────────────────────────────────────────────
    print(
        "\nVocê precisará do 'Application (client) ID' do Azure Portal.\n"
        "É um UUID com formato: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\n"
    )
    client_id = secure_prompt("Cole aqui o Application (client) ID:").strip()

    if not client_id:
        return False, "Client ID não informado. Execute 'auth outlook' para tentar novamente."

    # Validação básica de formato UUID
    import re
    if not re.match(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        client_id,
    ):
        return False, (
            "O Client ID informado não tem o formato correto de UUID.\n"
            "Esperado: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\n"
            "Execute 'auth outlook' para tentar novamente."
        )

    # ── Device Code Flow ──────────────────────────────────────────────────────
    print(
        "\nIniciando autenticação com a Microsoft...\n"
        "Você verá um código e uma URL para abrir no navegador.\n"
    )
    success, msg = outlook_auth_interactive(alias, client_id)

    return success, msg
