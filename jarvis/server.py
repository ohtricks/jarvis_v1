"""
Jarvis Web API Server — FastAPI local server.

Uso:
    python -m jarvis.server
    JARVIS_EXECUTE=1 python -m jarvis.server   # modo execute
    JARVIS_PORT=9000 python -m jarvis.server   # porta customizada

Segurança:
    - Bind apenas em 127.0.0.1
    - JARVIS_TOKEN_REQUIRED=1 exige header X-Jarvis-Token
"""
from __future__ import annotations

import os
import secrets

from dotenv import load_dotenv
load_dotenv()  # carrega .env da raiz do projeto
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import JarvisAgent
from . import voice as _voice
from .modal_payload import extract_modal
import psutil

# ── Auth state (OAuth flows em progresso) ─────────────────────────────────────
# alias → {status: "pending"|"connected"|"error", error?: str}
_gmail_auth_states: dict[str, dict] = {}
# alias → {status: "pending"|"connected"|"error", user_code?: str, verification_url?: str, app?, flow?}
_outlook_auth_states: dict[str, dict] = {}

from .memory import (
    get_last_llm_ms,
    get_pending_policy_proposal,
    get_pending_recovery,
    get_pending_shell_allow_proposal,
    get_recent_execution,
    get_session,
)
from .queue import last_blocked, list_items

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Jarvis API", version="1.0.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8899",
        "http://127.0.0.1:8899",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

_executor = ThreadPoolExecutor(max_workers=1)

# ── Singleton Agent ───────────────────────────────────────────────────────────

_agent: JarvisAgent | None = None
_lock = threading.Lock()


def _get_agent() -> JarvisAgent:
    global _agent
    if _agent is None:
        execute = os.getenv("JARVIS_EXECUTE", "0") == "1"
        _agent = JarvisAgent(execute=execute)
    return _agent


# ── Token de segurança ────────────────────────────────────────────────────────

_TOKEN_PATH = Path.home() / ".jarvis" / "server_token"
_TOKEN_REQUIRED = os.getenv("JARVIS_TOKEN_REQUIRED", "0") == "1"


def _load_or_create_token() -> str:
    _TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _TOKEN_PATH.exists():
        return _TOKEN_PATH.read_text().strip()
    token = secrets.token_hex(16)
    _TOKEN_PATH.write_text(token)
    return token


_SERVER_TOKEN: str | None = None


def _verify_token(request: Request) -> None:
    if not _TOKEN_REQUIRED:
        return
    global _SERVER_TOKEN
    if _SERVER_TOKEN is None:
        _SERVER_TOKEN = _load_or_create_token()
    token = request.headers.get("X-Jarvis-Token", "")
    if token != _SERVER_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido.")


# ── Blocked info helper ───────────────────────────────────────────────────────

def _get_blocked_info() -> dict[str, Any]:
    """Detecta estado de bloqueio e retorna info + suggestions para a UI."""
    item, _ = last_blocked()
    if item:
        confirm = item.get("confirm") or {}
        required = (confirm.get("required") or "yes").strip()
        is_danger = required.upper() == "YES I KNOW"
        return {
            "blocked": True,
            "blocked_kind": "danger" if is_danger else "risk",
            "blocked_step": item.get("step") or item.get("action"),
            "blocked_note": item.get("error") or item.get("blocked_reason"),
            "suggestions": ["YES I KNOW", "não"] if is_danger else ["yes", "não"],
        }

    shell_proposal = get_pending_shell_allow_proposal()
    if shell_proposal:
        suggested = shell_proposal.get("suggested_prefix", "")
        return {
            "blocked": True,
            "blocked_kind": "allowlist",
            "blocked_step": None,
            "blocked_note": f"Comando bloqueado pela allowlist. Prefixo sugerido: {suggested}",
            "suggestions": ([f"permitir {suggested}", "cancelar"] if suggested else ["cancelar"]),
        }

    policy_proposal = get_pending_policy_proposal()
    if policy_proposal:
        cmd = policy_proposal.get("command", "")
        return {
            "blocked": True,
            "blocked_kind": "proposal",
            "blocked_step": None,
            "blocked_note": f"Adicionar '{cmd}' à policy?",
            "suggestions": ["adicionar safe", "adicionar risky", "adicionar danger", "cancelar"],
        }

    recovery = get_pending_recovery()
    if recovery:
        return {
            "blocked": True,
            "blocked_kind": "recovery",
            "blocked_step": None,
            "blocked_note": "Tentar recovery automático?",
            "suggestions": ["sim", "não"],
        }

    return {
        "blocked": False,
        "blocked_kind": None,
        "blocked_step": None,
        "blocked_note": None,
        "suggestions": [],
    }


# ── Queue summary helper ──────────────────────────────────────────────────────

def _queue_summary() -> dict[str, int]:
    items = list_items()
    counts: dict[str, int] = {
        "total": len(items),
        "pending": 0, "running": 0, "blocked": 0,
        "done": 0, "failed": 0, "skipped": 0,
    }
    for it in items:
        st = it.get("status", "")
        if st in counts:
            counts[st] += 1
    return counts


# ── Schemas ───────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    text: str


class RunResponse(BaseModel):
    response: str
    request_id: str
    blocked: bool
    blocked_kind: str | None = None
    blocked_step: str | None = None
    blocked_note: str | None = None
    suggestions: list[str] = []
    # Payload estruturado para a UI renderizar modais (git_diff_review, etc.)
    # Presente apenas quando a skill retorna embed_modal().
    modal_payload: dict | None = None


class ConfirmRequest(BaseModel):
    text: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/api/run", response_model=RunResponse)
async def run(body: RunRequest, _: None = Depends(_verify_token)):
    """Envia um comando ao Jarvis e retorna a resposta."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Campo 'text' não pode ser vazio.")

    acquired = _lock.acquire(blocking=False)
    if not acquired:
        raise HTTPException(status_code=429, detail="Jarvis já está processando um comando. Aguarde.")

    try:
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(_executor, _get_agent().run, body.text)
    finally:
        _lock.release()

    response_text, modal = extract_modal(response)
    blocked_info = _get_blocked_info()
    return RunResponse(
        response=response_text,
        request_id=uuid.uuid4().hex[:8],
        modal_payload=modal,
        **blocked_info,
    )


@app.post("/api/confirm", response_model=RunResponse)
async def confirm(body: ConfirmRequest, _: None = Depends(_verify_token)):
    """
    Confirma ou rejeita uma ação bloqueada.
    Internamente idêntico a /api/run — passa pelo handle_builtin → risk/recovery gate.
    """
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Campo 'text' não pode ser vazio.")

    acquired = _lock.acquire(blocking=False)
    if not acquired:
        raise HTTPException(status_code=429, detail="Jarvis já está processando. Aguarde.")

    try:
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(_executor, _get_agent().run, body.text)
    finally:
        _lock.release()

    response_text, modal = extract_modal(response)
    blocked_info = _get_blocked_info()
    return RunResponse(
        response=response_text,
        request_id=uuid.uuid4().hex[:8],
        modal_payload=modal,
        **blocked_info,
    )


@app.get("/api/status")
async def status(_: None = Depends(_verify_token)):
    """Retorna mode atual, resumo da queue, métricas de sistema e info de bloqueio."""
    session = get_session()
    blocked_info = _get_blocked_info()
    return {
        "mode":        session.get("mode", "dry"),
        "queue":       _queue_summary(),
        "cpu":         psutil.cpu_percent(interval=None),
        "ram":         psutil.virtual_memory().percent,
        "last_llm_ms": get_last_llm_ms(),
        **blocked_info,
    }


@app.get("/api/history")
async def history(limit: int = 20, _: None = Depends(_verify_token)):
    """Retorna as últimas execuções registradas."""
    limit = max(1, min(limit, 100))
    items = get_recent_execution(limit=limit)
    return {"items": list(reversed(items))}


@app.get("/api/skills")
async def skills(_: None = Depends(_verify_token)):
    """Retorna a lista de actions (skills) disponíveis."""
    return {"skills": sorted(_get_agent().SKILLS.keys())}


# ── Auth endpoints ────────────────────────────────────────────────────────────

class GmailStartRequest(BaseModel):
    alias: str = "default"
    client_secret: str  # JSON content do client_secret.json


class OutlookStartRequest(BaseModel):
    alias: str = "default"
    client_id: str   # Azure App (client) ID
    account_type: str = "personal"  # "personal" | "org" | "tenant"
    tenant_id: str = ""  # Directory (tenant) ID — obrigatório quando account_type="tenant"


@app.get("/api/auth/accounts")
async def auth_accounts(_: None = Depends(_verify_token)):
    """Retorna todas as contas Gmail e Outlook conectadas."""
    from .integrations.google import gmail_api as _gapi
    from .integrations.microsoft import outlook_api as _oapi

    gmail_accounts = []
    for base in [_gapi.NEW_CREDS_DIR, _gapi.OLD_CREDS_DIR]:
        if base.exists():
            for d in base.iterdir():
                if d.is_dir() and (d / "token.json").exists():
                    alias = d.name
                    if not any(a["alias"] == alias for a in gmail_accounts):
                        gmail_accounts.append({"alias": alias, "connected": True})

    outlook_accounts = []
    if _oapi.CREDS_DIR.exists():
        for d in _oapi.CREDS_DIR.iterdir():
            if d.is_dir() and (d / "token_cache.bin").exists():
                outlook_accounts.append({"alias": d.name, "connected": True})

    return {"gmail": gmail_accounts, "outlook": outlook_accounts}


@app.post("/api/auth/gmail/start")
async def auth_gmail_start(body: GmailStartRequest, _: None = Depends(_verify_token)):
    """
    Inicia autenticação Gmail OAuth.
    Valida client_secret, salva, abre browser em thread de fundo.
    O frontend deve polling em /api/auth/gmail/status/{alias}.
    """
    import json
    alias = (body.alias or "default").strip().lower() or "default"

    # Valida JSON
    try:
        data = json.loads(body.client_secret)
    except Exception:
        raise HTTPException(status_code=400, detail="client_secret inválido: JSON malformado.")
    inner = data.get("installed") or data.get("web") or data
    required = {"client_id", "client_secret", "token_uri"}
    missing = required - inner.keys()
    if missing:
        raise HTTPException(status_code=400, detail=f"Campos ausentes no JSON: {', '.join(sorted(missing))}")

    # Salva client_secret
    from .integrations.google.gmail_api import NEW_CREDS_DIR, normalize_alias
    norm = normalize_alias(alias)
    dest_dir = NEW_CREDS_DIR / norm
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "client_secret.json").write_text(body.client_secret, encoding="utf-8")

    _gmail_auth_states[norm] = {"status": "pending"}

    def _do_gmail_auth():
        from .integrations.google.gmail_api import gmail_auth_interactive
        from pathlib import Path
        success, msg = gmail_auth_interactive(norm, dest_dir / "client_secret.json")
        _gmail_auth_states[norm] = {
            "status": "connected" if success else "error",
            "error": None if success else msg,
        }

    import threading
    threading.Thread(target=_do_gmail_auth, daemon=True).start()

    return {"status": "pending", "alias": norm, "message": "Abrindo navegador para autenticação Gmail..."}


@app.get("/api/auth/gmail/status/{alias}")
async def auth_gmail_status(alias: str, _: None = Depends(_verify_token)):
    """Retorna o estado atual do fluxo OAuth Gmail para o alias."""
    from .integrations.google import gmail_api as _gapi
    norm = _gapi.normalize_alias(alias)
    state = _gmail_auth_states.get(norm)
    if state:
        return state
    # Se não há estado de auth em progresso, verifica se já está conectado
    connected = _gapi.is_authed(norm)
    return {"status": "connected" if connected else "disconnected"}


@app.post("/api/auth/outlook/start")
async def auth_outlook_start(body: OutlookStartRequest, _: None = Depends(_verify_token)):
    """
    Inicia autenticação Outlook Device Code Flow.
    Retorna {user_code, verification_url, expires_in} para exibir na UI.
    O frontend deve chamar /api/auth/outlook/poll/{alias} para verificar conclusão.
    initiate_device_flow faz rede → roda em executor para não bloquear o event loop.
    """
    import re
    import asyncio
    alias = (body.alias or "default").strip().lower() or "default"
    client_id = body.client_id.strip()
    account_type = (body.account_type or "personal").strip()
    tenant_id = (body.tenant_id or "").strip()

    if not re.match(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        client_id,
    ):
        raise HTTPException(status_code=400, detail="Client ID inválido. Formato esperado: UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)")

    if account_type == "tenant" and not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID obrigatório quando tipo de conta é 'tenant'.")

    try:
        import msal
    except ImportError:
        raise HTTPException(status_code=500, detail="Dependência 'msal' não instalada. Execute: pip install msal")

    from .integrations.microsoft.outlook_api import SCOPES, normalize_alias, get_paths, _AUTHORITY_ORG, _AUTHORITY_PERSONAL

    norm = normalize_alias(alias)

    if tenant_id:
        authority = f"https://login.microsoftonline.com/{tenant_id}"
    elif account_type == "org":
        authority = _AUTHORITY_ORG
    else:
        authority = _AUTHORITY_PERSONAL

    def _start_device_flow():
        cache = msal.SerializableTokenCache()
        app_msal = msal.PublicClientApplication(
            client_id,
            authority=authority,
            token_cache=cache,
        )
        flow = app_msal.initiate_device_flow(scopes=SCOPES)
        return app_msal, cache, flow

    try:
        loop = asyncio.get_event_loop()
        app_msal, cache, flow = await loop.run_in_executor(None, _start_device_flow)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar Device Code Flow: {e}")

    if "user_code" not in flow:
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar Device Code Flow: {flow.get('error_description', 'desconhecido')}")

    # Salva client_id, account_type e tenant_id antecipadamente
    paths = get_paths(norm)
    paths["base_dir"].mkdir(parents=True, exist_ok=True)
    paths["client_id_path"].write_text(client_id, encoding="utf-8")
    paths["account_type_path"].write_text(account_type, encoding="utf-8")
    if tenant_id:
        paths["tenant_id_path"].write_text(tenant_id, encoding="utf-8")
    elif paths["tenant_id_path"].exists():
        paths["tenant_id_path"].unlink()  # Remove tenant anterior se mudou para personal/org

    # Armazena estado (app e flow para polling posterior)
    _outlook_auth_states[norm] = {
        "status": "pending",
        "user_code": flow["user_code"],
        "verification_url": flow["verification_uri"],
        "expires_in": flow.get("expires_in", 900),
        "_app": app_msal,
        "_flow": flow,
        "_cache": cache,
        "_client_id": client_id,
        "_account_type": account_type,
        "_tenant_id": tenant_id,
    }

    return {
        "status": "pending",
        "alias": norm,
        "user_code": flow["user_code"],
        "verification_url": flow["verification_uri"],
        "expires_in": flow.get("expires_in", 900),
        "message": flow["message"],
    }


@app.get("/api/auth/outlook/poll/{alias}")
async def auth_outlook_poll(alias: str, _: None = Depends(_verify_token)):
    """
    Faz polling do Device Code Flow. Chame a cada 5s até status='connected' ou 'error'.
    acquire_token_by_device_flow é bloqueante → roda em executor.
    """
    import asyncio
    from .integrations.microsoft.outlook_api import normalize_alias, get_paths

    norm = normalize_alias(alias)
    state = _outlook_auth_states.get(norm)

    if not state:
        from .integrations.microsoft import outlook_api as _oapi
        connected = _oapi.is_authed(norm)
        return {"status": "connected" if connected else "disconnected"}

    if state["status"] in ("connected", "error"):
        return {"status": state["status"], "error": state.get("error")}

    app_msal = state["_app"]
    flow = state["_flow"]
    cache = state["_cache"]

    def _poll():
        # exit_condition=True → retorna após a primeira tentativa sem bloquear
        return app_msal.acquire_token_by_device_flow(flow, exit_condition=lambda f: True)

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _poll)
    except Exception:
        return {"status": "pending", "user_code": state["user_code"], "verification_url": state["verification_url"]}

    if "access_token" in result:
        paths = get_paths(norm)
        paths["token_cache_path"].write_text(cache.serialize(), encoding="utf-8")
        _outlook_auth_states[norm] = {"status": "connected"}
        return {"status": "connected"}

    err = result.get("error", "")
    if err == "authorization_pending":
        return {"status": "pending", "user_code": state["user_code"], "verification_url": state["verification_url"]}

    _outlook_auth_states[norm] = {"status": "error", "error": result.get("error_description", err)}
    return {"status": "error", "error": result.get("error_description", err)}


@app.delete("/api/auth/{provider}/{alias}")
async def auth_disconnect(provider: str, alias: str, _: None = Depends(_verify_token)):
    """Remove token de autenticação para o provider/alias informado."""
    import shutil

    if provider == "gmail":
        from .integrations.google import gmail_api as _gapi
        norm = _gapi.normalize_alias(alias)
        paths = _gapi.get_paths(norm)
        token = paths["token_path"]
        if token.exists():
            token.unlink()
        _gmail_auth_states.pop(norm, None)
        return {"ok": True, "message": f"Gmail '{norm}' desconectado."}

    elif provider == "outlook":
        from .integrations.microsoft import outlook_api as _oapi
        norm = _oapi.normalize_alias(alias)
        paths = _oapi.get_paths(norm)
        if paths["token_cache_path"].exists():
            paths["token_cache_path"].unlink()
        if paths["client_id_path"].exists():
            paths["client_id_path"].unlink()
        _outlook_auth_states.pop(norm, None)
        return {"ok": True, "message": f"Outlook '{norm}' desconectado."}

    raise HTTPException(status_code=400, detail=f"Provider desconhecido: {provider}")


@app.websocket("/api/voice")
async def voice_ws(websocket: WebSocket):
    """
    WebSocket de voz — relay entre browser e Gemini Live API.

    Browser envia chunks PCM 16-bit 16kHz (binário) ou JSON de controle.
    Server retorna JSON: {type: audio|transcript|response_text|tool_result|blocked|done|error}
    """
    await _voice.handle_session(websocket, _get_agent())


# ── Servir assets estáticos da UI (Tauri-ready) ───────────────────────────────

_UI_DIST = Path(__file__).parent.parent / "ui" / "dist"
if _UI_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_UI_DIST), html=True), name="static")


# ── Entry point ───────────────────────────────────────────────────────────────

def _run_server():
    import uvicorn  # type: ignore

    port = int(os.getenv("JARVIS_PORT", "8899"))
    token_required = _TOKEN_REQUIRED

    print(f"\n🤖  Jarvis API Server")
    print(f"    URL:     http://127.0.0.1:{port}")
    print(f"    Docs:    http://127.0.0.1:{port}/api/docs")
    print(f"    Mode:    {'execute' if os.getenv('JARVIS_EXECUTE') == '1' else 'dry-run'}")

    if token_required:
        token = _load_or_create_token()
        print(f"    Token:   {token}  (salvo em {_TOKEN_PATH})")
    else:
        print(f"    Token:   desabilitado  (JARVIS_TOKEN_REQUIRED=1 para ativar)")

    print()
    log_level = "debug" if os.getenv("JARVIS_DEBUG") == "1" else "info"
    uvicorn.run(app, host="127.0.0.1", port=port, log_level=log_level)


if __name__ == "__main__":
    _run_server()
