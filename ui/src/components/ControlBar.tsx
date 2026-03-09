import { useState } from 'react';
import { VoiceStatus } from '../hooks/useVoice';

const MIC_HINT: Record<VoiceStatus, string> = {
  disconnected: 'offline',
  connecting:   'aguarde',
  idle:         'toque para falar',
  listening:    'ouvindo — toque para mutar',
  processing:   'processando',
  speaking:     'falando',
};

function IconMic() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
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
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <rect x="5" y="5" width="14" height="14" rx="3" />
    </svg>
  );
}

function IconCamera() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M23 7l-7 5 7 5V7z" />
      <rect x="1" y="5" width="15" height="14" rx="2" />
    </svg>
  );
}

function IconText() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 7 4 4 20 4 20 7" />
      <line x1="9" y1="20" x2="15" y2="20" />
      <line x1="12" y1="4" x2="12" y2="20" />
    </svg>
  );
}

interface Props {
  status: VoiceStatus;
  isMuted: boolean;
  onStart: () => void;
  onStop: () => void;
  onSendText: (text: string) => void;
  onDisconnect: () => void;
  isConnected: boolean;
}

export function ControlBar({ status, isMuted, onStart, onStop, onSendText, onDisconnect, isConnected }: Props) {
  const [showText, setShowText] = useState(false);
  const [textVal, setTextVal]   = useState('');

  const isListening = status === 'listening';
  const isBusy      = status === 'connecting' || status === 'processing' || status === 'speaking';
  const isDisabled  = status === 'disconnected' || isBusy;

  const hint = isMuted && !isListening
    ? 'mutado — toque para falar'
    : MIC_HINT[status];

  function handleMic() {
    if (isDisabled) return;
    isListening ? onStop() : onStart();
  }

  function handleSend() {
    const t = textVal.trim();
    if (!t) return;
    onSendText(t);
    setTextVal('');
    setShowText(false);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') handleSend();
    if (e.key === 'Escape') { setShowText(false); setTextVal(''); }
  }

  return (
    <div className="ctrl-bar">
      {/* Main mic button */}
      <div className="ctrl-bar-row">
        <button
          className={`ctrl-icon-btn ${showText ? 'active' : ''}`}
          onClick={() => setShowText(v => !v)}
          title="Digitar comando"
          disabled={status === 'disconnected'}
        >
          <IconText />
        </button>

        <button
          className={`ctrl-mic ${isListening ? 'listening' : ''}`}
          onClick={handleMic}
          disabled={isDisabled}
          aria-label={isListening ? 'parar' : 'falar'}
        >
          <span className="ctrl-mic-ring" />
          <span className="ctrl-mic-ring" />
          <span className="ctrl-mic-ring" />
          {isListening ? <IconStop /> : <IconMic />}
        </button>

        <button
          className="ctrl-icon-btn"
          title="Câmera (em breve)"
          disabled
        >
          <IconCamera />
        </button>
      </div>

      {/* Hint label */}
      <div className="ctrl-mic-hint">{hint}</div>

      {/* Text input (toggleable) */}
      {showText && (
        <div className="ctrl-text-row">
          <input
            autoFocus
            className="ctrl-text-input"
            placeholder="digitar comando..."
            value={textVal}
            onChange={e => setTextVal(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button className="ctrl-text-send" onClick={handleSend}>enviar</button>
        </div>
      )}

      {/* Disconnect */}
      {isConnected && (
        <button className="ctrl-disconnect" onClick={onDisconnect}>
          desconectar
        </button>
      )}
    </div>
  );
}
