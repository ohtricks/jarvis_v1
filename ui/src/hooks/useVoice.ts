import { useRef, useState, useCallback } from 'react';

export type VoiceStatus =
  | 'disconnected'
  | 'connecting'
  | 'idle'
  | 'listening'
  | 'processing'
  | 'speaking';

// Estado do agente — mais granular que VoiceStatus
export type AgentState =
  | 'idle'
  | 'thinking'
  | 'planning'
  | 'compiling'
  | 'executing'
  | 'blocked'
  | 'responding';

export interface TranscriptEntry {
  id: string;
  role: 'user' | 'assistant' | 'system';
  text: string;
  ts: Date;
}

export interface BlockedInfo {
  blocked_kind: string;
  blocked_step: string | null;
  blocked_note: string | null;
  suggestions: string[];
}

export interface SkillEvent {
  action: string;
  ts: number;
  skillId?: string;
  phase?: 'started' | 'completed' | 'failed';
}

// ── Activity Feed ─────────────────────────────────────────────────────────────

export type ActivityEventType =
  | 'jarvis_command'
  | 'thinking'
  | 'planning'
  | 'compiling'
  | 'executing'
  | 'skill_start'
  | 'skill_done'
  | 'skill_fail'
  | 'blocked'
  | 'responding'
  | 'user'
  | 'assistant';

export interface ActivityEvent {
  id: string;
  type: ActivityEventType;
  label: string;
  ts: Date;
  skillId?: string;
  action?: string;
}

// ── Active Skills ─────────────────────────────────────────────────────────────

export interface ActiveSkill {
  skillId: string;
  action: string;
  label: string;
  startedAt: Date;
  status: 'running' | 'completed' | 'failed';
}

// ── Modal payload types ───────────────────────────────────────────────────────

export interface DiffFileEntry {
  file: string;
  additions: number;
  deletions: number;
  status: 'added' | 'modified' | 'deleted';
}

export interface DiffSection {
  file: string;
  content: string;
  truncated: boolean;
}

export interface DiffInsight {
  level: 'ok' | 'info' | 'warning' | 'error';
  message: string;
}

export interface DiffAction {
  id: string;
  label: string;
  description: string;
  command: string;
  enabled: boolean;
  risk?: string;
}

export interface GitDiffPayload {
  title: string;
  summary: string;
  meta: {
    files_changed: number;
    additions: number;
    deletions: number;
    risk_level: 'low' | 'medium' | 'high';
    truncated: boolean;
    total_files: number;
    shown_files: number;
  };
  sections: {
    files: DiffFileEntry[];
    diff: DiffSection[];
    insights: DiffInsight[];
  };
  actions: DiffAction[];
}

export interface ModalPayload {
  ui_hint: 'modal';
  modal_type: 'git_diff_review';
  payload: GitDiffPayload;
}

export interface QueueData {
  total: number;
  pending: number;
  running: number;
  blocked: number;
  done: number;
  failed: number;
  skipped: number;
}

export interface HistoryItem {
  ts: string;
  action: string;
  args: Record<string, unknown>;
  status: 'done' | 'failed' | 'blocked';
  output: string;
}

export interface SystemMetrics {
  cpu: number | null;
  ram: number | null;
  wsPing: number | null;
  llmMs: number | null;
}

// ── Utils ─────────────────────────────────────────────────────────────────────

function formatSkillLabel(action: string): string {
  return action
    .replace(/^google_/, '')
    .replace(/_/g, '.');
}

const ACTIVITY_LABEL: Record<ActivityEventType, string> = {
  jarvis_command: '',  // label built dynamically (command text)
  thinking:   'Analisando solicitação',
  planning:   'Planejando estratégia',
  compiling:  'Compilando ações',
  executing:  'Executando plano',
  skill_start:'',  // label built dynamically
  skill_done: '',
  skill_fail: '',
  blocked:    'Aguardando confirmação',
  responding: 'Gerando resposta',
  user:       '',
  assistant:  '',
};

const WS_URL      = 'ws://127.0.0.1:8899/api/voice';
const STATUS_URL  = 'http://127.0.0.1:8899/api/status';
const SKILLS_URL  = 'http://127.0.0.1:8899/api/skills';
const HISTORY_URL = 'http://127.0.0.1:8899/api/history';

export function useVoice() {
  const [status,        setStatus]        = useState<VoiceStatus>('disconnected');
  const [agentState,    setAgentState]    = useState<AgentState>('idle');
  const [transcript,    setTranscript]    = useState<TranscriptEntry[]>([]);
  const [blocked,       setBlocked]       = useState<BlockedInfo | null>(null);
  const [modalPayload,  setModalPayload]  = useState<ModalPayload | null>(null);
  const [lastSkillEvent, setLastSkillEvent] = useState<SkillEvent | null>(null);
  const [activityFeed,  setActivityFeed]  = useState<ActivityEvent[]>([]);
  const [activeSkills,  setActiveSkills]  = useState<ActiveSkill[]>([]);
  const [mode,          setMode]          = useState<'dry' | 'execute'>('dry');
  const [error,        setError]        = useState<string | null>(null);
  const [queueData,    setQueueData]    = useState<QueueData | null>(null);
  const [skills,       setSkills]       = useState<string[]>([]);
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [metrics,      setMetrics]      = useState<SystemMetrics>({ cpu: null, ram: null, wsPing: null, llmMs: null });

  const [isMuted,        setIsMuted]        = useState<boolean>(false);

  const wsRef              = useRef<WebSocket | null>(null);
  const captureCtxRef      = useRef<AudioContext | null>(null);
  const playbackCtxRef     = useRef<AudioContext | null>(null);
  const nextPlayTimeRef    = useRef<number>(0);
  const streamRef          = useRef<MediaStream | null>(null);
  const processorRef       = useRef<ScriptProcessorNode | null>(null);
  const sourceRef          = useRef<MediaStreamAudioSourceNode | null>(null);
  const isCapturingRef     = useRef<boolean>(false);
  const isMutedRef         = useRef<boolean>(false);
  const speakTimerRef      = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollRef            = useRef<ReturnType<typeof setInterval> | null>(null);
  const pingIntervalRef    = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectTimerRef  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef  = useRef<number>(2000);
  const shouldReconnectRef = useRef<boolean>(false);

  // ── helpers ──────────────────────────────────────────────────────────────

  const addEntry = useCallback((role: TranscriptEntry['role'], text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setTranscript(prev => [
      ...prev,
      { id: crypto.randomUUID(), role, text: trimmed, ts: new Date() },
    ]);
  }, []);

  const addActivity = useCallback((
    type: ActivityEventType,
    label: string,
    extra?: { skillId?: string; action?: string },
  ) => {
    setActivityFeed(prev => [
      ...prev.slice(-79), // manter últimos 80 eventos
      { id: crypto.randomUUID(), type, label, ts: new Date(), ...extra },
    ]);
  }, []);

  const ensurePlayback = useCallback(async (): Promise<AudioContext> => {
    if (!playbackCtxRef.current || playbackCtxRef.current.state === 'closed') {
      playbackCtxRef.current = new AudioContext({ sampleRate: 24000 });
      nextPlayTimeRef.current = 0;
    }
    if (playbackCtxRef.current.state === 'suspended') {
      await playbackCtxRef.current.resume();
    }
    return playbackCtxRef.current;
  }, []);

  const playAudioChunk = useCallback(async (base64: string) => {
    try {
      const ctx = await ensurePlayback();
      const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
      const int16 = new Int16Array(bytes.buffer);
      const float32 = new Float32Array(int16.length);
      for (let i = 0; i < int16.length; i++) {
        float32[i] = int16[i] / 32768;
      }

      const buf = ctx.createBuffer(1, float32.length, 24000);
      buf.getChannelData(0).set(float32);

      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.connect(ctx.destination);

      const now = ctx.currentTime;
      const startAt = Math.max(now + 0.02, nextPlayTimeRef.current);
      src.start(startAt);
      nextPlayTimeRef.current = startAt + buf.duration;

      setStatus('speaking');

      if (speakTimerRef.current) clearTimeout(speakTimerRef.current);
      const delayMs = (nextPlayTimeRef.current - now) * 1000 + 300;
      speakTimerRef.current = setTimeout(() => {
        const c = playbackCtxRef.current;
        if (c && nextPlayTimeRef.current <= c.currentTime + 0.15) {
          setStatus('idle');
        }
      }, delayMs);
    } catch (e) {
      console.error('Audio playback error:', e);
    }
  }, [ensurePlayback]);

  // ── polling status (cpu/ram/queue/llm) ───────────────────────────────────

  const _stopPoll = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }, []);

  const _startPoll = useCallback(() => {
    _stopPoll();
    const fetchStatus = async () => {
      try {
        const res  = await fetch(STATUS_URL);
        const data = await res.json();
        setMode(data.mode === 'execute' ? 'execute' : 'dry');
        if (data.queue) setQueueData(data.queue as QueueData);
        setMetrics(prev => ({
          ...prev,
          cpu:   typeof data.cpu   === 'number' ? Math.round(data.cpu)   : prev.cpu,
          ram:   typeof data.ram   === 'number' ? Math.round(data.ram)   : prev.ram,
          llmMs: typeof data.last_llm_ms === 'number' ? data.last_llm_ms : prev.llmMs,
        }));
      } catch { /* server may be busy */ }
    };
    fetchStatus();
    pollRef.current = setInterval(fetchStatus, 3000);
  }, [_stopPoll]);

  // ── WebSocket ping ────────────────────────────────────────────────────────

  const _stopPing = useCallback(() => {
    if (pingIntervalRef.current) { clearInterval(pingIntervalRef.current); pingIntervalRef.current = null; }
  }, []);

  const _startPing = useCallback(() => {
    _stopPing();
    const sendPing = () => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      ws.send(JSON.stringify({ type: 'ping', ts: Date.now() }));
    };
    sendPing();
    pingIntervalRef.current = setInterval(sendPing, 5000);
  }, [_stopPing]);

  // ── WebSocket message handler ─────────────────────────────────────────────

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const msg = JSON.parse(event.data as string);
      switch (msg.type) {

        // ── Comando Gemini → Jarvis ───────────────────────────────────────
        case 'jarvis:command':
          addActivity('jarvis_command', (msg.command as string) ?? '');
          break;

        // ── Voz / transcrição ─────────────────────────────────────────────
        case 'transcript': {
          // Upsert: atualiza a última entrada do usuário se chegou recentemente (streaming),
          // ou cria nova entrada. Garante que todos os chunks de transcrição apareçam completos.
          const text = (msg.text as string ?? '').trim();
          if (text) {
            setTranscript(prev => {
              const last = prev[prev.length - 1];
              const isRecentUser = last?.role === 'user' && (Date.now() - last.ts.getTime()) < 8000;
              if (isRecentUser) {
                return [...prev.slice(0, -1), { ...last, text }];
              }
              return [...prev, { id: crypto.randomUUID(), role: 'user', text, ts: new Date() }];
            });
            setActivityFeed(prev => {
              const last = prev[prev.length - 1];
              const isRecentUser = last?.type === 'user' && (Date.now() - last.ts.getTime()) < 8000;
              if (isRecentUser) {
                return [...prev.slice(0, -1), { ...last, label: text }];
              }
              return [...prev.slice(-79), { id: crypto.randomUUID(), type: 'user' as ActivityEventType, label: text, ts: new Date() }];
            });
            setStatus('processing');
          }
          break;
        }
        case 'response_text':
          addEntry('assistant', msg.text ?? '');
          addActivity('assistant', msg.text ?? '');
          break;
        case 'audio':
          if (msg.data) playAudioChunk(msg.data);
          break;

        // ── Resultado final (legado — mantém compatibilidade) ─────────────
        case 'tool_result':
          if (msg.result) addEntry('system', `[${msg.action ?? 'jarvis'}] ${msg.result}`);
          // Bubble legado: spawna para tool_results sem skill_id (antes do realtime)
          if (msg.action && msg.action !== 'ask_jarvis') {
            setLastSkillEvent({ action: msg.action as string, ts: Date.now() });
          }
          break;

        // ── Eventos de estado do agente ───────────────────────────────────
        case 'agent:thinking':
          setAgentState('thinking');
          addActivity('thinking', ACTIVITY_LABEL['thinking']);
          break;
        case 'agent:planning':
          setAgentState('planning');
          addActivity('planning', ACTIVITY_LABEL['planning']);
          break;
        case 'agent:compiling':
          setAgentState('compiling');
          addActivity('compiling', `Compilando ações (${(msg.model as string) ?? 'fast'})`);
          break;
        case 'agent:executing':
          setAgentState('executing');
          addActivity('executing', ACTIVITY_LABEL['executing']);
          break;
        case 'agent:responding':
          setAgentState('responding');
          addActivity('responding', ACTIVITY_LABEL['responding']);
          break;

        // ── Ciclo de vida das skills ──────────────────────────────────────
        case 'skill:started': {
          const skillId = (msg.skill_id as string) ?? '';
          const action  = (msg.action  as string) ?? '';
          const label   = formatSkillLabel(action);
          setAgentState('executing');
          setActiveSkills(prev => [
            ...prev,
            { skillId, action, label, startedAt: new Date(), status: 'running' },
          ]);
          setLastSkillEvent({ action, ts: Date.now(), skillId, phase: 'started' });
          addActivity('skill_start', `Iniciando ${label}`, { skillId, action });
          break;
        }
        case 'skill:completed': {
          const skillId = (msg.skill_id as string) ?? '';
          const action  = (msg.action  as string) ?? '';
          const label   = formatSkillLabel(action);
          setActiveSkills(prev =>
            prev.map(s => s.skillId === skillId ? { ...s, status: 'completed' as const } : s)
          );
          setLastSkillEvent({ action, ts: Date.now(), skillId, phase: 'completed' });
          addActivity('skill_done', `Concluído: ${label}`, { skillId, action });
          // Remove o skill da lista ativa após a animação de saída (~1.2s)
          setTimeout(() => {
            setActiveSkills(prev => prev.filter(s => s.skillId !== skillId));
          }, 1400);
          break;
        }
        case 'skill:failed': {
          const skillId = (msg.skill_id as string) ?? '';
          const action  = (msg.action  as string) ?? '';
          const label   = formatSkillLabel(action);
          setActiveSkills(prev =>
            prev.map(s => s.skillId === skillId ? { ...s, status: 'failed' as const } : s)
          );
          setLastSkillEvent({ action, ts: Date.now(), skillId, phase: 'failed' });
          addActivity('skill_fail', `Falhou: ${label}`, { skillId, action });
          setTimeout(() => {
            setActiveSkills(prev => prev.filter(s => s.skillId !== skillId));
          }, 2200);
          break;
        }
        case 'task:blocked': {
          const action = (msg.action as string) ?? '';
          setAgentState('blocked');
          addActivity('blocked', `Confirmação: ${action}`, { action });
          break;
        }

        // ── Bloqueio / modal / sistema ────────────────────────────────────
        case 'blocked':
          setBlocked({
            blocked_kind: msg.blocked_kind ?? 'risk',
            blocked_step: msg.blocked_step ?? null,
            blocked_note: msg.blocked_note ?? null,
            suggestions:  msg.suggestions  ?? [],
          });
          break;
        case 'modal':
          if (msg.modal_payload) setModalPayload(msg.modal_payload as ModalPayload);
          break;
        case 'pong':
          if (typeof msg.ts === 'number') {
            setMetrics(prev => ({ ...prev, wsPing: Date.now() - msg.ts }));
          }
          break;
        case 'done': {
          const c = playbackCtxRef.current;
          if (!c || nextPlayTimeRef.current <= c.currentTime + 0.1) {
            setStatus('idle');
          }
          setAgentState('idle');
          setActiveSkills([]);
          break;
        }
        case 'error':
          setError(msg.message ?? 'Erro desconhecido');
          addEntry('system', `⚠ ${msg.message ?? 'erro'}`);
          setStatus('idle');
          setAgentState('idle');
          break;
      }
    } catch { /* non-JSON frame */ }
  }, [addEntry, addActivity, playAudioChunk]);

  // ── capture teardown ──────────────────────────────────────────────────────

  const stopCapture = useCallback(() => {
    isCapturingRef.current = false;
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    processorRef.current = null;
    sourceRef.current    = null;
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    captureCtxRef.current?.close().catch(() => {});
    captureCtxRef.current = null;
  }, []);

  // ── public API ────────────────────────────────────────────────────────────

  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return;

    // Cancel any pending reconnect timer
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    shouldReconnectRef.current = true;
    setStatus('connecting');
    setError(null);

    // Fetch skills once (best-effort)
    try {
      const res  = await fetch(SKILLS_URL);
      const data = await res.json();
      setSkills(data.skills ?? []);
    } catch { /* ignore */ }

    // Start polling /api/status for mode + queue + cpu/ram/llm
    _startPoll();

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen    = () => {
      reconnectDelayRef.current = 2000; // reset backoff on success
      setStatus('idle');
      addEntry('system', 'Conectado.');
      _startPing();
    };
    ws.onclose   = () => {
      setStatus('disconnected');
      setAgentState('idle');
      stopCapture();
      isMutedRef.current = false;
      setIsMuted(false);
      _stopPoll();
      _stopPing();

      if (shouldReconnectRef.current) {
        const delay = reconnectDelayRef.current;
        reconnectDelayRef.current = Math.min(delay * 2, 30000);
        reconnectTimerRef.current = setTimeout(() => {
          reconnectTimerRef.current = null;
          connect();
        }, delay);
      }
    };
    ws.onerror   = () => {
      // onclose will fire right after — let it handle reconnect
      setError('Não foi possível conectar. Verifique se o server Jarvis está rodando em :8899.');
    };
    ws.onmessage = handleMessage;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [addEntry, handleMessage, stopCapture, _startPoll, _stopPoll, _startPing, _stopPing]);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    _stopPoll();
    _stopPing();
    stopCapture();
    isMutedRef.current = false;
    setIsMuted(false);
    wsRef.current?.close();
    wsRef.current = null;
  }, [stopCapture, _stopPoll, _stopPing]);

  const startListening = useCallback(async () => {
    // If already capturing (was muted), just unmute
    if (isCapturingRef.current) {
      isMutedRef.current = false;
      setIsMuted(false);
      setStatus('listening');
      return;
    }

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      await connect();
      await new Promise<void>(resolve => {
        const t = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) { clearInterval(t); resolve(); }
        }, 80);
        setTimeout(() => { clearInterval(t); resolve(); }, 4000);
      });
    }

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    setBlocked(null);
    setError(null);

    try {
      await ensurePlayback();

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;

      const captureCtx = new AudioContext({ sampleRate: 16000 });
      captureCtxRef.current = captureCtx;

      const src = captureCtx.createMediaStreamSource(stream);
      sourceRef.current = src;

      const processor = captureCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (!isCapturingRef.current) return;
        if (isMutedRef.current) return;
        const ws = wsRef.current;
        if (!ws || ws.readyState !== WebSocket.OPEN) return;

        const f32 = e.inputBuffer.getChannelData(0);
        const i16 = new Int16Array(f32.length);
        for (let i = 0; i < f32.length; i++) {
          i16[i] = Math.max(-32768, Math.min(32767, f32[i] * 32768));
        }
        ws.send(i16.buffer);
      };

      src.connect(processor);
      processor.connect(captureCtx.destination);

      isCapturingRef.current = true;
      isMutedRef.current = false;
      setIsMuted(false);
      setStatus('listening');
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(`Microfone inacessível: ${msg}`);
    }
  }, [connect, ensurePlayback]);

  const stopListening = useCallback(() => {
    // Mute only — keep capture pipeline alive for quick unmute
    isMutedRef.current = true;
    setIsMuted(true);
    setStatus(wsRef.current?.readyState === WebSocket.OPEN ? 'idle' : 'idle');
  }, []);

  const sendConfirmation = useCallback((text: string) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: 'text_command', text }));
    addEntry('user', text);
    setBlocked(null);
    setStatus('processing');
  }, [addEntry]);

  const refreshHistory = useCallback(async () => {
    try {
      const res  = await fetch(HISTORY_URL);
      const data = await res.json();
      setHistoryItems(data.items ?? []);
    } catch { /* ignore */ }
  }, []);

  return {
    status,
    agentState,
    isMuted,
    transcript,
    blocked,
    modalPayload,
    lastSkillEvent,
    activityFeed,
    activeSkills,
    mode,
    error,
    queueData,
    skills,
    historyItems,
    metrics,
    connect,
    disconnect,
    startListening,
    stopListening,
    sendConfirmation,
    refreshHistory,
    clearError:  () => setError(null),
    clearModal:  () => setModalPayload(null),
  };
}
