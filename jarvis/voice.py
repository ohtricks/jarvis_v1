"""
voice.py — Relay WebSocket entre o browser e o Gemini Live API.

Fluxo:
  Browser (PCM 16kHz) → WS /api/voice → Gemini Live API
  Gemini Live API → (áudio 24kHz + tool calls) → Browser

Quando Gemini chama ask_jarvis(command):
  → agent.run(command) no thread executor (preserva todo o pipeline)
  → resultado retorna ao Gemini como tool response
  → Gemini sintetiza resposta em voz

Protocolo WS (server → browser):
  {"type": "transcript",    "text": "..."}         transcrição da fala do usuário
  {"type": "response_text", "text": "..."}         texto da resposta do Gemini
  {"type": "audio",         "data": "<base64>"}    áudio PCM 24kHz para tocar
  {"type": "tool_result",   "action": "ask_jarvis", "command": "...", "result": "..."}
  {"type": "blocked",       "blocked_kind": "...", "blocked_step": "...",
                             "blocked_note": "...", "suggestions": [...]}
  {"type": "error",         "message": "..."}
  {"type": "done"}

Protocolo WS (browser → server):
  binário  — chunk PCM 16-bit 16kHz mono
  JSON     — {"type": "end_of_speech"} ou {"type": "ping"}
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

from .voice_tools import build_voice_tools

logger = logging.getLogger(__name__)

_GEMINI_MODEL_PREFERRED = "gemini-2.5-flash-native-audio-latest"
_GEMINI_MODEL_FALLBACK  = "gemini-2.5-flash-native-audio-preview-12-2025"

_SYSTEM_PROMPT_BASE = """\
Você é J.A.R.V.I.S. — Just A Rather Very Intelligent System.
Assistente pessoal de IA do seu criador, operando em macOS.

IDIOMA: português brasileiro (pt-BR) em todas as respostas e raciocínios.
Sempre realize seu raciocínio interno (chain of thought) e sua resposta final exclusivamente em português do Brasil (PT-BR).

PERSONALIDADE:
- Tom formal, preciso e levemente britânico — como o J.A.R.V.I.S. do Homem de Ferro.
- NUNCA cumprimente ou se apresente — vá direto ao ponto sempre.
- Seja direto, elegante e inteligente. Nunca prolixo.
- Demonstre iniciativa: se detectar algo relevante no contexto, mencione brevemente.
- Humor seco e sofisticado quando apropriado — nunca forçado.
- Confirme ações executadas com concisão: "Concluído, senhor." ou "Feito."
- Ao receber bloqueio de risco, informe com clareza e aguarde confirmação do usuário.

EXEMPLOS DE TOM:
- "Já providenciei isso, senhor."
- "Devo alertá-lo que essa ação requer confirmação."
- "Prontamente, senhor."
- "Identificado. Executando agora."

FERRAMENTAS:
- Use ask_jarvis para qualquer ação solicitada pelo usuário.
- Se o retorno indicar confirmação necessária (risky/danger), informe o usuário e aguarde.
- Confirmação do usuário ("sim", "pode", "confirmar") → chame ask_jarvis com esse texto.
- Cancelamento ("não", "cancela") → chame ask_jarvis com "não".
"""

_HISTORY_MAX_TURNS = 10  # turns a injetar no contexto de sessões novas


def _build_system_prompt(history: list[dict]) -> str:
    """Constrói o system prompt injetando o histórico recente da conversa."""
    if not history:
        return _SYSTEM_PROMPT_BASE

    recent = history[-_HISTORY_MAX_TURNS:]
    lines = ["\nCONTEXTO DA CONVERSA ANTERIOR (continue a partir daqui, sem cumprimentar):"]
    for turn in recent:
        role = "Usuário" if turn["role"] == "user" else "J.A.R.V.I.S."
        lines.append(f"  {role}: {turn['text']}")

    return _SYSTEM_PROMPT_BASE + "\n".join(lines) + "\n"

_executor = ThreadPoolExecutor(max_workers=2)


def _detect_blocked(result: str) -> dict | None:
    """
    Detecta se o resultado do agent.run() indica uma ação bloqueada.
    O Jarvis retorna texto com padrões reconhecíveis quando bloqueia.
    """
    lower = result.lower()
    if "confirmação necessária" in lower or "confirmar:" in lower or "aguarda" in lower:
        # Tenta detectar o kind pelo texto
        if "yes i know" in lower:
            kind = "danger"
            suggestions = ["YES I KNOW", "não"]
        else:
            kind = "risk"
            suggestions = ["yes", "não"]
        return {
            "type": "blocked",
            "blocked_kind": kind,
            "blocked_step": None,
            "blocked_note": result,
            "suggestions": suggestions,
        }
    return None


async def _send_json(ws: WebSocket, data: dict) -> None:
    try:
        await ws.send_text(json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


async def _wait_for_first_audio(websocket: WebSocket) -> bytes | None:
    """
    Aguarda o primeiro chunk de áudio binário do browser.
    Fica em loop ignorando pings/JSONs de controle até receber PCM binário.
    Retorna o chunk ou None se o browser desconectar antes de enviar áudio.
    """
    try:
        while True:
            msg = await websocket.receive()
            if msg["type"] == "websocket.disconnect":
                return None
            if "bytes" in msg and msg["bytes"]:
                return msg["bytes"]
            # ignora pings e outros JSONs de controle enquanto aguarda
    except WebSocketDisconnect:
        return None
    except Exception as e:
        logger.debug("wait_for_first_audio error: %s", e)
        return None


async def handle_session(websocket: WebSocket, agent) -> None:
    """
    Gerencia uma sessão de voz completa.
    `agent` é a instância de JarvisAgent (singleton do server.py).

    Estratégia lazy: o Gemini Live só é conectado quando o primeiro chunk
    de áudio chegar — evita timeout de inatividade durante o auto-connect.
    """
    await websocket.accept()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        await _send_json(websocket, {
            "type": "error",
            "message": "GEMINI_API_KEY não configurada. Adicione ao .env.",
        })
        await websocket.close()
        return

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(api_version="v1alpha"),
    )
    tools = build_voice_tools()

    def _make_config(history: list[dict]) -> types.LiveConnectConfig:
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            tools=tools,
            system_instruction=_build_system_prompt(history),
            # Habilita transcrição de input e output para popular o histórico
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Charon")
                )
            ),
        )

    # Histórico da conversa — persiste entre sessões Gemini na mesma conexão WS.
    # Cada nova sessão injeta os turns anteriores no system prompt para dar continuidade.
    conversation_history: list[dict] = []

    # Loop de sessões: cada clique no mic inicia uma nova sessão Gemini.
    # Quando o Gemini encerra (timeout ou limit), volta a aguardar áudio sem fechar o WS.
    session_count = 0
    while True:
        # Fase 1 — aguarda o próximo chunk de áudio (mic clicado pelo usuário)
        logger.info("[voice] Aguardando áudio do browser (sessão %d)…", session_count)
        first_chunk = await _wait_for_first_audio(websocket)
        if first_chunk is None:
            logger.info("[voice] Browser desconectou — encerrando handle_session.")
            return  # browser fechou o WS

        session_count += 1
        logger.info("[voice] Áudio recebido — iniciando sessão Gemini Live #%d (histórico: %d turns)", session_count, len(conversation_history))

        # Fase 2 — conecta ao Gemini Live com contexto do histórico
        if conversation_history:
            for i, t in enumerate(conversation_history):
                logger.info("[voice] history[%d] %s: %s", i, t["role"], t["text"][:80])

        model = _GEMINI_MODEL_PREFERRED
        live_config = _make_config(conversation_history)
        try:
            async with client.aio.live.connect(model=model, config=live_config) as session:
                await _run_session(websocket, session, agent, conversation_history, first_chunk=first_chunk)
            logger.info("[voice] Sessão Gemini #%d encerrada normalmente.", session_count)
        except Exception as e:
            err_msg = str(e)
            if any(k in err_msg.lower() for k in ("not found", "invalid", "not supported", "1008")):
                logger.warning("[voice] Modelo %s indisponível, tentando fallback %s", model, _GEMINI_MODEL_FALLBACK)
                try:
                    async with client.aio.live.connect(model=_GEMINI_MODEL_FALLBACK, config=live_config) as session:
                        await _run_session(websocket, session, agent, conversation_history, first_chunk=first_chunk)
                    logger.info("[voice] Sessão fallback #%d encerrada normalmente.", session_count)
                except WebSocketDisconnect:
                    return
                except Exception as e2:
                    logger.error("[voice] Erro no fallback: %s", e2)
                    await _send_json(websocket, {"type": "error", "message": str(e2)})
            else:
                logger.error("[voice] Erro na sessão Gemini #%d: %s", session_count, err_msg)
                await _send_json(websocket, {"type": "error", "message": err_msg})
        # Continua o loop — aguarda próximo clique no mic


async def _run_session(
    websocket: WebSocket,
    gemini_session,
    agent,
    history: list[dict],
    first_chunk: bytes | None = None,
) -> None:
    """Loop principal da sessão: recebe áudio do browser e processa respostas do Gemini.

    `history` é mutado in-place: turns desta sessão são acrescentados para
    serem injetados como contexto na próxima sessão Gemini.
    """
    _pending_user_text: list[str] = []   # acumula transcrição do usuário até turn_complete
    _pending_jarvis_text: list[str] = [] # acumula texto do Jarvis até turn_complete

    async def _receive_from_browser():
        """Task: lê mensagens do browser e envia ao Gemini."""
        try:
            # Repassa o primeiro chunk capturado antes do Gemini conectar
            if first_chunk:
                await gemini_session.send(
                    input=types.LiveClientRealtimeInput(
                        media_chunks=[
                            types.Blob(
                                data=first_chunk,
                                mime_type="audio/pcm;rate=16000",
                            )
                        ]
                    )
                )

            while True:
                msg = await websocket.receive()
                if msg["type"] == "websocket.disconnect":
                    break

                if "bytes" in msg and msg["bytes"]:
                    # Áudio binário PCM 16-bit 16kHz mono
                    pcm_bytes = msg["bytes"]
                    await gemini_session.send(
                        input=types.LiveClientRealtimeInput(
                            media_chunks=[
                                types.Blob(
                                    data=pcm_bytes,
                                    mime_type="audio/pcm;rate=16000",
                                )
                            ]
                        )
                    )
                elif "text" in msg and msg["text"]:
                    try:
                        ctrl = json.loads(msg["text"])
                        if ctrl.get("type") == "end_of_speech":
                            pass  # Gemini VAD detecta silêncio automaticamente
                        elif ctrl.get("type") == "ping":
                            await _send_json(websocket, {"type": "pong", "ts": ctrl.get("ts")})
                        elif ctrl.get("type") == "text_command":
                            text = str(ctrl.get("text", "")).strip()
                            if text:
                                await gemini_session.send(
                                    input=types.LiveClientContent(
                                        turns=[
                                            types.Content(
                                                role="user",
                                                parts=[types.Part(text=text)],
                                            )
                                        ],
                                        turn_complete=True,
                                    )
                                )
                    except json.JSONDecodeError:
                        pass
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug("receive_from_browser error: %s", e)

    async def _receive_from_gemini():
        """Task: lê respostas do Gemini e despacha ao browser."""
        try:
            async for response in gemini_session.receive():
                if response.server_content:
                    sc = response.server_content

                    # Debug: mostra o que o Gemini está mandando
                    logger.info(
                        "[voice] sc: input_tr=%s output_tr=%s model_turn=%s turn_complete=%s",
                        bool(sc.input_transcription and sc.input_transcription.text),
                        bool(sc.output_transcription and sc.output_transcription.text),
                        bool(sc.model_turn),
                        sc.turn_complete,
                    )

                    # Transcrição da fala do usuário — acumula, não envia por chunk
                    if sc.input_transcription and sc.input_transcription.text:
                        _pending_user_text.append(sc.input_transcription.text)

                    # Transcrição do áudio do Jarvis — acumula, não envia por chunk
                    if sc.output_transcription and sc.output_transcription.text:
                        _pending_jarvis_text.append(sc.output_transcription.text)

                    # Áudio da resposta — envia imediatamente (streaming de áudio é ok)
                    if sc.model_turn and sc.model_turn.parts:
                        for part in sc.model_turn.parts:
                            if part.inline_data and part.inline_data.data:
                                audio_b64 = base64.b64encode(part.inline_data.data).decode()
                                await websocket.send_text(json.dumps({
                                    "type": "audio",
                                    "data": audio_b64,
                                }))
                            elif part.text:
                                # fallback: text parts sem output_audio_transcription
                                _pending_jarvis_text.append(part.text)

                    if sc.turn_complete:
                        # Envia textos completos de uma vez (sem parcelamento)
                        if _pending_user_text:
                            full_user = " ".join(_pending_user_text)
                            await _send_json(websocket, {"type": "transcript", "text": full_user})
                            history.append({"role": "user", "text": full_user})
                            _pending_user_text.clear()

                        if _pending_jarvis_text:
                            full_jarvis = " ".join(_pending_jarvis_text)
                            await _send_json(websocket, {"type": "response_text", "text": full_jarvis})
                            history.append({"role": "assistant", "text": full_jarvis})
                            _pending_jarvis_text.clear()

                        await _send_json(websocket, {"type": "done"})

                # Tool call — Gemini quer executar ask_jarvis
                if response.tool_call:
                    for fc in response.tool_call.function_calls:
                        if fc.name == "ask_jarvis":
                            command = (fc.args or {}).get("command", "")
                            await _execute_ask_jarvis(
                                websocket, gemini_session, agent, fc.id, command
                            )

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.warning("[voice] receive_from_gemini encerrado com erro: %s", e)
            await _send_json(websocket, {"type": "error", "message": str(e)})

    # Roda as duas tasks concorrentemente
    browser_task = asyncio.create_task(_receive_from_browser())
    gemini_task = asyncio.create_task(_receive_from_gemini())
    done, pending = await asyncio.wait(
        [browser_task, gemini_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()


async def _execute_ask_jarvis(
    websocket: WebSocket,
    gemini_session,
    agent,
    call_id: str,
    command: str,
) -> None:
    """Executa agent.run(command) e envia o tool_response de volta ao Gemini."""
    loop = asyncio.get_event_loop()
    try:
        result: str = await loop.run_in_executor(_executor, agent.run, command)
    except Exception as e:
        result = f"Erro ao executar: {e}"

    # Notifica browser do resultado (para UI)
    await _send_json(websocket, {
        "type": "tool_result",
        "action": "ask_jarvis",
        "command": command,
        "result": result,
    })

    # Verifica se é uma ação bloqueada e notifica browser
    blocked = _detect_blocked(result)
    if blocked:
        await _send_json(websocket, blocked)

    # Envia tool response ao Gemini para ele continuar a conversa
    await gemini_session.send(
        input=types.LiveClientToolResponse(
            function_responses=[
                types.FunctionResponse(
                    id=call_id,
                    name="ask_jarvis",
                    response={"result": result},
                )
            ]
        )
    )
