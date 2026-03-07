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
from .memory import (
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

    blocked_info = _get_blocked_info()
    return RunResponse(
        response=response,
        request_id=uuid.uuid4().hex[:8],
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

    blocked_info = _get_blocked_info()
    return RunResponse(
        response=response,
        request_id=uuid.uuid4().hex[:8],
        **blocked_info,
    )


@app.get("/api/status")
async def status(_: None = Depends(_verify_token)):
    """Retorna mode atual, resumo da queue e info de bloqueio."""
    session = get_session()
    blocked_info = _get_blocked_info()
    return {
        "mode": session.get("mode", "dry"),
        "queue": _queue_summary(),
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
