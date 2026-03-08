"""
events.py — Emissão de eventos em tempo real para o frontend via WebSocket.

Usa thread-local storage para injetar o emitter no thread do agent.run()
sem alterar assinaturas de funções internas.

Uso no agent/executor:
    from .events import emit
    emit("skill:started", skill_id="abc", action="google_gmail_list_today")

Uso no voice.py (setup):
    em = EventEmitter(loop, queue)
    set_emitter_for_thread(em, fn)   # envolve fn em closure que seta/limpa thread-local
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

_local = threading.local()


class EventEmitter:
    """
    Ponte thread-safe entre o thread do agent.run() e o loop asyncio do WebSocket.
    Usa loop.call_soon_threadsafe para enfileirar eventos na asyncio.Queue.
    """

    def __init__(self, loop, queue) -> None:
        self._loop  = loop
        self._queue = queue
        self._active = True
        self._lock   = threading.Lock()

    def emit(self, event_type: str, **kwargs) -> None:
        with self._lock:
            if not self._active:
                return
        event = {"type": event_type, **kwargs}
        try:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, event)
        except Exception:
            pass

    def deactivate(self) -> None:
        with self._lock:
            self._active = False


def set_emitter(emitter: Optional[EventEmitter]) -> None:
    """Define o emitter para o thread atual."""
    _local.emitter = emitter


def get_emitter() -> Optional[EventEmitter]:
    """Retorna o emitter do thread atual (ou None)."""
    return getattr(_local, "emitter", None)


def emit(event_type: str, **kwargs) -> None:
    """Emite evento se houver emitter ativo no thread atual. Silencioso caso contrário."""
    em = get_emitter()
    if em:
        em.emit(event_type, **kwargs)


def wrap_with_emitter(fn: Callable, emitter: EventEmitter) -> Callable:
    """
    Retorna um callable que seta o emitter no thread-local antes de chamar fn,
    e limpa depois (mesmo em caso de exceção).

    Uso em voice.py:
        wrapped = wrap_with_emitter(agent.run, emitter)
        result = await loop.run_in_executor(_executor, wrapped, command)
    """
    def _wrapped(*args, **kwargs):
        set_emitter(emitter)
        try:
            return fn(*args, **kwargs)
        finally:
            set_emitter(None)
            emitter.deactivate()
    return _wrapped
