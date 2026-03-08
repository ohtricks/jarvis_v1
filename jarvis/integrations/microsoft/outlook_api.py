"""
Microsoft Outlook API — autenticação OAuth via MSAL e operações via Microsoft Graph.

SEGURANÇA:
- Credenciais e tokens são salvos apenas em ~/.jarvis/credentials/microsoft/outlook/<alias>/
- Nenhum token ou credential é enviado para LLM ou gravado em telemetry.
- As funções deste módulo nunca chamam add_turn(), telemetry ou logger.
- Usa Device Code Flow (sem servidor local) — ideal para CLI.
"""

from __future__ import annotations

from pathlib import Path

CREDS_DIR = Path.home() / ".jarvis" / "credentials" / "microsoft" / "outlook"

SCOPES = [
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/Mail.Send",
    "https://graph.microsoft.com/Mail.ReadWrite",
]

# consumers = contas pessoais (Outlook.com, Hotmail, Live)
# organizations = contas corporativas/escola (Microsoft 365)
# common = ambos (requer configuração específica no Azure)
_AUTHORITY_PERSONAL = "https://login.microsoftonline.com/consumers"
_AUTHORITY_ORG      = "https://login.microsoftonline.com/organizations"
_AUTHORITY_DEFAULT  = _AUTHORITY_PERSONAL  # padrão: contas pessoais

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


# ── Paths ─────────────────────────────────────────────────────────────────────

def normalize_alias(alias) -> str:
    return (str(alias or "default").strip().lower()) or "default"


def get_paths(alias: str = "default") -> dict:
    """Retorna dict com base_dir, token_cache_path, client_id_path, account_type_path, tenant_id_path."""
    alias = normalize_alias(alias)
    base = CREDS_DIR / alias
    return {
        "base_dir": base,
        "token_cache_path": base / "token_cache.bin",
        "client_id_path": base / "client_id.txt",
        "account_type_path": base / "account_type.txt",
        "tenant_id_path": base / "tenant_id.txt",
    }


def is_authed(alias: str = "default") -> bool:
    """Verifica se existe token salvo para o alias."""
    paths = get_paths(alias)
    return paths["token_cache_path"].exists() and paths["client_id_path"].exists()


# ── Auth ──────────────────────────────────────────────────────────────────────

def _load_cache(alias: str):
    """Carrega o SerializableTokenCache do disco."""
    try:
        import msal
    except ImportError:
        raise ImportError(
            "Dependência ausente. Instale com:\n  pip install msal"
        )
    cache = msal.SerializableTokenCache()
    token_cache_path = get_paths(alias)["token_cache_path"]
    if token_cache_path.exists():
        cache.deserialize(token_cache_path.read_text(encoding="utf-8"))
    return cache


def _save_cache(alias: str, cache) -> None:
    """Persiste o cache se foi modificado."""
    if cache.has_state_changed:
        token_cache_path = get_paths(alias)["token_cache_path"]
        token_cache_path.parent.mkdir(parents=True, exist_ok=True)
        token_cache_path.write_text(cache.serialize(), encoding="utf-8")


def _get_app(alias: str, client_id: str | None = None):
    """Constrói o PublicClientApplication com cache persistente."""
    try:
        import msal
    except ImportError:
        raise ImportError(
            "Dependência ausente. Instale com:\n  pip install msal"
        )
    paths = get_paths(alias)
    if client_id is None:
        client_id = paths["client_id_path"].read_text(encoding="utf-8").strip()
    atype = paths["account_type_path"].read_text(encoding="utf-8").strip() if paths["account_type_path"].exists() else "personal"
    if paths["tenant_id_path"].exists():
        tid = paths["tenant_id_path"].read_text(encoding="utf-8").strip()
        authority = f"https://login.microsoftonline.com/{tid}"
    elif atype == "org":
        authority = _AUTHORITY_ORG
    else:
        authority = _AUTHORITY_PERSONAL
    cache = _load_cache(alias)
    app = msal.PublicClientApplication(
        client_id,
        authority=authority,
        token_cache=cache,
    )
    return app, cache


def _get_token(alias: str) -> str:
    """
    Retorna access token válido. MSAL auto-renova via refresh token.
    Levanta RuntimeError se não conseguir.
    """
    app, cache = _get_app(alias)
    accounts = app.get_accounts()
    if not accounts:
        raise RuntimeError(
            f"Conta Outlook '{alias}' não autenticada. Execute: auth outlook {alias}"
        )
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    _save_cache(alias, cache)
    if result and "access_token" in result:
        import base64, json as _j, sys
        try:
            parts = result["access_token"].split(".")
            pad = parts[1] + "=" * (4 - len(parts[1]) % 4)
            claims = _j.loads(base64.b64decode(pad))
            print(f"[OUTLOOK DEBUG] Token obtido. aud={claims.get('aud')} | scp={claims.get('scp')} | roles={claims.get('roles')}", file=sys.stderr, flush=True)
        except Exception:
            pass
        return result["access_token"]
    import json as _json
    import sys
    detail = _json.dumps(result, ensure_ascii=False, indent=2) if result else "None (sem token em cache)"
    print(f"\n[OUTLOOK DEBUG] acquire_token_silent falhou para '{alias}':\n{detail}\n", file=sys.stderr, flush=True)
    raise RuntimeError(
        f"Não foi possível renovar token para '{alias}'. Resposta MSAL: {detail}"
    )


def outlook_auth_interactive(alias: str, client_id: str, account_type: str = "personal", tenant_id: str = "") -> tuple[bool, str]:
    """
    Executa o fluxo Device Code OAuth.
    Exibe código + URL para o usuário autenticar no browser.
    Salva client_id, account_type, tenant_id e token_cache no diretório do alias.
    NUNCA loga o token.
    Retorna (success: bool, mensagem: str).
    """
    try:
        import msal
    except ImportError:
        return False, (
            "Dependência ausente. Instale com:\n  pip install msal"
        )

    try:
        if tenant_id:
            authority = f"https://login.microsoftonline.com/{tenant_id}"
        elif account_type == "org":
            authority = _AUTHORITY_ORG
        else:
            authority = _AUTHORITY_PERSONAL
        cache = msal.SerializableTokenCache()
        app = msal.PublicClientApplication(
            client_id,
            authority=authority,
            token_cache=cache,
        )
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            return False, f"Erro ao iniciar autenticação: {flow.get('error_description', 'desconhecido')}"

        print(flow["message"], flush=True)

        result = app.acquire_token_by_device_flow(flow)
        if "access_token" not in result:
            err = result.get("error_description") or result.get("error", "desconhecido")
            return False, f"Autenticação falhou: {err}"

        # Salva client_id, account_type, tenant_id e cache
        paths = get_paths(alias)
        paths["base_dir"].mkdir(parents=True, exist_ok=True)
        paths["client_id_path"].write_text(client_id, encoding="utf-8")
        paths["account_type_path"].write_text(account_type, encoding="utf-8")
        if tenant_id:
            paths["tenant_id_path"].write_text(tenant_id, encoding="utf-8")
        paths["token_cache_path"].write_text(cache.serialize(), encoding="utf-8")

        return True, f"✅ Outlook conectado com sucesso (alias: {alias})"

    except Exception as e:
        return False, f"Erro durante autenticação OAuth: {e}"


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def _graph_get(alias: str, path: str, params: dict | None = None) -> dict:
    """GET na Microsoft Graph API. Levanta RuntimeError em falha."""
    import urllib.request
    import urllib.parse
    import json as _json

    token = _get_token(alias)
    url = f"{_GRAPH_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)

    import sys
    print(f"[OUTLOOK DEBUG] GET {url}", file=sys.stderr, flush=True)

    # Teste de sanidade: verifica se /me funciona com o token
    if path != "/me":
        try:
            test_req = urllib.request.Request(f"{_GRAPH_BASE}/me", headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(test_req) as r:
                me = _json.loads(r.read().decode())
                print(f"[OUTLOOK DEBUG] /me OK → {me.get('userPrincipalName')}", file=sys.stderr, flush=True)
        except urllib.error.HTTPError as te:
            print(f"[OUTLOOK DEBUG] /me FALHOU → {te.code}: {te.read().decode('utf-8', errors='replace')}", file=sys.stderr, flush=True)

    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            return _json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        import sys
        headers_str = dict(e.headers) if e.headers else {}
        print(f"\n[OUTLOOK DEBUG] Graph API GET {path} → {e.code}", file=sys.stderr, flush=True)
        print(f"[OUTLOOK DEBUG] Headers: {headers_str}", file=sys.stderr, flush=True)
        print(f"[OUTLOOK DEBUG] Body: {repr(body)}\n", file=sys.stderr, flush=True)
        raise RuntimeError(f"Graph API GET {path} retornou {e.code}: {body}")


def _graph_post(alias: str, path: str, body: dict) -> dict:
    """POST na Microsoft Graph API."""
    import urllib.request
    import json as _json

    token = _get_token(alias)
    url = f"{_GRAPH_BASE}{path}"
    data = _json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return _json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Graph API POST {path} retornou {e.code}: {body}")


def _graph_patch(alias: str, path: str, body: dict) -> dict:
    """PATCH na Microsoft Graph API."""
    import urllib.request
    import json as _json

    token = _get_token(alias)
    url = f"{_GRAPH_BASE}{path}"
    data = _json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return _json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Graph API PATCH {path} retornou {e.code}: {body}")


# ── Read ──────────────────────────────────────────────────────────────────────

def list_message_ids(
    alias: str,
    filter_str: str = "",
    top: int = 10,
) -> list[str]:
    """Retorna lista de message IDs do inbox que batem com o filtro OData."""
    params: dict = {
        "$top": top,
        "$select": "id",
        "$orderby": "receivedDateTime desc",
    }
    if filter_str:
        params["$filter"] = filter_str

    result = _graph_get(alias, "/me/messages", params)
    return [m["id"] for m in result.get("value", [])]


def get_message_meta(alias: str, message_id: str) -> dict:
    """
    Retorna metadata básica de uma mensagem.
    {id, from, to, subject, date, snippet, conversationId, isRead}
    """
    params = {
        "$select": "id,subject,from,toRecipients,receivedDateTime,bodyPreview,conversationId,isRead"
    }
    msg = _graph_get(alias, f"/me/messages/{message_id}", params)
    from_addr = (msg.get("from") or {}).get("emailAddress", {})
    to_list = msg.get("toRecipients") or []
    to_str = ", ".join(
        r.get("emailAddress", {}).get("address", "") for r in to_list
    )
    return {
        "id": msg.get("id", ""),
        "from": f"{from_addr.get('name', '')} <{from_addr.get('address', '')}>".strip(),
        "to": to_str,
        "subject": msg.get("subject") or "(sem assunto)",
        "date": msg.get("receivedDateTime", ""),
        "snippet": msg.get("bodyPreview", ""),
        "conversationId": msg.get("conversationId", ""),
        "isRead": msg.get("isRead", True),
    }


def get_message_full(alias: str, message_id: str) -> dict:
    """
    Retorna metadata + body_text do email.
    {id, from, to, subject, date, snippet, conversationId, isRead, body_text}
    """
    params = {
        "$select": "id,subject,from,toRecipients,receivedDateTime,bodyPreview,conversationId,isRead,body"
    }
    msg = _graph_get(alias, f"/me/messages/{message_id}", params)
    from_addr = (msg.get("from") or {}).get("emailAddress", {})
    to_list = msg.get("toRecipients") or []
    to_str = ", ".join(
        r.get("emailAddress", {}).get("address", "") for r in to_list
    )
    body_content = (msg.get("body") or {}).get("content", "")
    # Remove tags HTML simples se o content-type for html
    if (msg.get("body") or {}).get("contentType", "") == "html":
        import re
        body_content = re.sub(r"<[^>]+>", " ", body_content)
        body_content = re.sub(r"\s+", " ", body_content).strip()

    return {
        "id": msg.get("id", ""),
        "from": f"{from_addr.get('name', '')} <{from_addr.get('address', '')}>".strip(),
        "to": to_str,
        "subject": msg.get("subject") or "(sem assunto)",
        "date": msg.get("receivedDateTime", ""),
        "snippet": msg.get("bodyPreview", ""),
        "conversationId": msg.get("conversationId", ""),
        "isRead": msg.get("isRead", True),
        "body_text": body_content,
    }


def get_conversation(alias: str, conversation_id: str, max_messages: int = 20) -> list[dict]:
    """Retorna lista de metadados de mensagens de uma conversa."""
    params = {
        "$filter": f"conversationId eq '{conversation_id}'",
        "$top": max_messages,
        "$orderby": "receivedDateTime asc",
        "$select": "id,subject,from,toRecipients,receivedDateTime,bodyPreview,conversationId,isRead",
    }
    result = _graph_get(alias, "/me/messages", params)
    messages = []
    for msg in result.get("value", []):
        from_addr = (msg.get("from") or {}).get("emailAddress", {})
        to_list = msg.get("toRecipients") or []
        to_str = ", ".join(r.get("emailAddress", {}).get("address", "") for r in to_list)
        messages.append({
            "id": msg.get("id", ""),
            "from": f"{from_addr.get('name', '')} <{from_addr.get('address', '')}>".strip(),
            "to": to_str,
            "subject": msg.get("subject") or "(sem assunto)",
            "date": msg.get("receivedDateTime", ""),
            "snippet": msg.get("bodyPreview", ""),
            "conversationId": msg.get("conversationId", ""),
            "isRead": msg.get("isRead", True),
        })
    return messages


def list_folders(alias: str) -> list[dict]:
    """Retorna [{id, name}] com as pastas do mailbox."""
    result = _graph_get(alias, "/me/mailFolders", {"$select": "id,displayName"})
    return [{"id": f["id"], "name": f["displayName"]} for f in result.get("value", [])]


# ── Modify ────────────────────────────────────────────────────────────────────

def mark_read(alias: str, message_id: str) -> dict:
    """Marca mensagem como lida. Retorna o objeto atualizado."""
    return _graph_patch(alias, f"/me/messages/{message_id}", {"isRead": True})


def move_to_archive(alias: str, message_id: str) -> dict:
    """Move mensagem para a pasta Archive. Retorna o objeto movido."""
    return _graph_post(alias, f"/me/messages/{message_id}/move", {"destinationId": "archive"})


# ── Write ─────────────────────────────────────────────────────────────────────

def send_message(
    alias: str,
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
) -> dict:
    """Envia email via Graph API. Retorna dict com id da mensagem enviada."""
    def _make_recipients(addrs: str | None) -> list[dict]:
        if not addrs:
            return []
        return [
            {"emailAddress": {"address": a.strip()}}
            for a in addrs.split(",")
            if a.strip()
        ]

    message: dict = {
        "subject": subject,
        "body": {"contentType": "Text", "content": body},
        "toRecipients": _make_recipients(to),
    }
    if cc:
        message["ccRecipients"] = _make_recipients(cc)
    if bcc:
        message["bccRecipients"] = _make_recipients(bcc)

    _graph_post(alias, "/me/sendMail", {"message": message, "saveToSentItems": True})
    return {"sent": True}


def reply_message(
    alias: str,
    message_id: str,
    body: str,
    reply_all: bool = False,
) -> dict:
    """Reply a uma mensagem. Retorna dict confirmando envio."""
    endpoint = "replyAll" if reply_all else "reply"
    _graph_post(
        alias,
        f"/me/messages/{message_id}/{endpoint}",
        {"message": {"body": {"contentType": "Text", "content": body}}},
    )
    return {"replied": True}
