import { useEffect, useRef } from 'react';
import { useVoice, VoiceStatus, TranscriptEntry, BlockedInfo } from './hooks/useVoice';

// ── Status helpers ────────────────────────────────────────────────────────────

const STATUS_COLOR: Record<VoiceStatus, string> = {
  disconnected: '#3a3d52',
  connecting:   '#fbbf24',
  idle:         '#1de9b6',
  listening:    '#ff7828',
  processing:   '#fbbf24',
  speaking:     '#a78bfa',
};

const STATUS_LABEL: Record<VoiceStatus, string> = {
  disconnected: 'desconectado',
  connecting:   'conectando',
  idle:         'aguardando',
  listening:    'ouvindo',
  processing:   'processando',
  speaking:     'falando',
};

const MIC_HINT: Record<VoiceStatus, string> = {
  disconnected: 'conectando...',
  connecting:   'aguarde...',
  idle:         'toque para falar',
  listening:    'toque para parar',
  processing:   'processando...',
  speaking:     'reproduzindo...',
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtTime(d: Date) {
  return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function btnClass(suggestion: string): string {
  const s = suggestion.toLowerCase();
  if (s === 'yes i know') return 'blocked-btn danger-confirm';
  if (s === 'yes' || s === 'sim' || s === 'confirmar' || s === 'ok' || s === 'manda ver') {
    return 'blocked-btn confirm';
  }
  if (s === 'não' || s === 'cancelar' || s === 'n') return 'blocked-btn cancel';
  return 'blocked-btn neutral';
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function IconMic() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="2" width="6" height="11" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}

function IconStop() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
      <rect x="5" y="5" width="14" height="14" rx="2" />
    </svg>
  );
}

// ── Status Bar ────────────────────────────────────────────────────────────────

function StatusBar({ status, mode }: { status: VoiceStatus; mode: 'dry' | 'execute' }) {
  return (
    <div className="status-bar">
      <div className="status-brand">
        <span className="brand-dot" />
        JARVIS
      </div>
      <div className="status-right">
        <span className={`status-mode${mode === 'execute' ? ' execute' : ''}`}>
          {mode === 'execute' ? 'EXECUTE' : 'DRY-RUN'}
        </span>
        <div className="status-indicator" style={{ color: STATUS_COLOR[status] }}>
          <span className="status-dot" />
          {STATUS_LABEL[status]}
        </div>
      </div>
    </div>
  );
}

// ── Voice Orb (visual feedback only) ─────────────────────────────────────────

function VoiceOrb({ status }: { status: VoiceStatus }) {
  return (
    <div className={`orb-container ${status}`}>
      <div className="ripple-ring" />
      <div className="ripple-ring" />
      <div className="ripple-ring" />
      <div className="spinner-ring" />
      <div className="wave-ring" />
      <div className="wave-ring" />
      <div className="wave-ring" />
      <div className="orb" />
    </div>
  );
}

// ── Mic Button (flame style) ──────────────────────────────────────────────────

function MicButton({
  status,
  onStart,
  onStop,
}: {
  status: VoiceStatus;
  onStart: () => void;
  onStop: () => void;
}) {
  const isListening = status === 'listening';
  const isDisabled  = status === 'connecting' || status === 'disconnected'
                   || status === 'processing'  || status === 'speaking';

  function handleClick() {
    if (isDisabled) return;
    isListening ? onStop() : onStart();
  }

  return (
    <div className="mic-area">
      <button
        className={[
          'mic-btn',
          isListening ? 'listening' : '',
          isDisabled  ? 'disabled'  : '',
        ].join(' ').trim()}
        onClick={handleClick}
        disabled={isDisabled}
        aria-label={isListening ? 'parar de ouvir' : 'falar com o Jarvis'}
      >
        {isListening && (
          <>
            <span className="flame-ring fr1" />
            <span className="flame-ring fr2" />
            <span className="flame-ring fr3" />
          </>
        )}
        <span className="mic-icon-wrap">
          {isListening ? <IconStop /> : <IconMic />}
        </span>
      </button>
      <p className="mic-hint">{MIC_HINT[status]}</p>
    </div>
  );
}

// ── Blocked Panel ─────────────────────────────────────────────────────────────

function BlockedPanel({
  info,
  onConfirm,
}: {
  info: BlockedInfo;
  onConfirm: (text: string) => void;
}) {
  const isDanger = info.blocked_kind === 'danger';
  return (
    <div className={`blocked-panel${isDanger ? ' danger' : ''}`}>
      <div className="blocked-header">
        <span className="blocked-icon">{isDanger ? '⚡' : '⚠'}</span>
        <span className="blocked-kind">
          {isDanger ? 'ação perigosa' : 'confirmação necessária'}
        </span>
      </div>
      {(info.blocked_note || info.blocked_step) && (
        <div className="blocked-note">{info.blocked_note ?? info.blocked_step}</div>
      )}
      <div className="blocked-suggestions">
        {info.suggestions.map(s => (
          <button key={s} className={btnClass(s)} onClick={() => onConfirm(s)}>
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Chat Entry ────────────────────────────────────────────────────────────────

function EntryRow({ entry }: { entry: TranscriptEntry }) {
  return (
    <div className="entry">
      <div className={`entry-role ${entry.role}`}>
        <span className="entry-role-dot" />
      </div>
      <div className={`entry-content ${entry.role}`}>
        <div className="entry-label">
          {entry.role === 'user' ? 'você' : entry.role === 'assistant' ? 'jarvis' : 'sistema'}
        </div>
        <div className="entry-text">{entry.text}</div>
        <div className="entry-ts">{fmtTime(entry.ts)}</div>
      </div>
    </div>
  );
}

// ── Chat Panel (right column) ─────────────────────────────────────────────────

function ChatPanel({ entries }: { entries: TranscriptEntry[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span>conversa</span>
        <span className="chat-count">{entries.length} mensagens</span>
      </div>
      <div className="transcript-area">
        {entries.length === 0 ? (
          <div className="transcript-empty">
            <span className="transcript-empty-icon">◎</span>
            <span>nenhuma conversa ainda</span>
          </div>
        ) : (
          entries.map(e => <EntryRow key={e.id} entry={e} />)
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const {
    status,
    transcript,
    blocked,
    mode,
    error,
    connect,
    disconnect,
    startListening,
    stopListening,
    sendConfirmation,
    clearError,
  } = useVoice();

  // Auto-connect WebSocket + Gemini Live ao montar (sem mic — precisa de gesto)
  useEffect(() => {
    connect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isConnected = status !== 'disconnected' && status !== 'connecting';

  return (
    <div className="app">
      <StatusBar status={status} mode={mode} />

      {error && (
        <div className="error-toast">
          <span>{error}</span>
          <button className="error-close" onClick={clearError} aria-label="fechar">×</button>
        </div>
      )}

      <div className="app-body">

        {/* ── Esquerda: voz ── */}
        <div className="voice-panel">
          <VoiceOrb status={status} />

          <MicButton
            status={status}
            onStart={startListening}
            onStop={stopListening}
          />

          {blocked && (
            <BlockedPanel info={blocked} onConfirm={sendConfirmation} />
          )}

          {isConnected && (
            <button className="ctrl-btn active" onClick={disconnect}>
              desconectar
            </button>
          )}
        </div>

        {/* ── Direita: chat ── */}
        <ChatPanel entries={transcript} />

      </div>
    </div>
  );
}
