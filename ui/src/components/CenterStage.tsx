import { useState } from 'react';
import { VoiceStatus, BlockedInfo } from '../hooks/useVoice';
import { VoiceOrb } from './VoiceOrb';
import { ControlBar } from './ControlBar';

function btnClass(s: string): string {
  const l = s.toLowerCase();
  if (l === 'yes i know') return 'blocked-btn danger-confirm';
  if (l === 'yes' || l === 'sim' || l === 'confirmar' || l === 'ok' || l === 'manda ver')
    return 'blocked-btn confirm';
  if (l === 'não' || l === 'cancelar' || l === 'n') return 'blocked-btn cancel';
  return 'blocked-btn neutral';
}

const DEBUG_STATES: VoiceStatus[] = ['idle', 'listening', 'processing', 'speaking'];
const DEBUG_LABELS: Record<string, string> = {
  idle: 'idle', listening: 'listen', processing: 'think', speaking: 'speak',
};

interface Props {
  status: VoiceStatus;
  blocked: BlockedInfo | null;
  onStart: () => void;
  onStop: () => void;
  onSendText: (text: string) => void;
  onConfirm: (text: string) => void;
  onDisconnect: () => void;
}

export function CenterStage({
  status,
  blocked,
  onStart,
  onStop,
  onSendText,
  onConfirm,
  onDisconnect,
}: Props) {
  const isConnected = status !== 'disconnected' && status !== 'connecting';
  const [debugState, setDebugState] = useState<VoiceStatus | null>(null);
  const effectiveStatus = debugState ?? status;

  return (
    <main className="stage">
      <div className="stage-inner">

        {/* Orb */}
        <VoiceOrb status={effectiveStatus} />

        {/* Controls */}
        <ControlBar
          status={status}
          onStart={onStart}
          onStop={onStop}
          onSendText={onSendText}
          onDisconnect={onDisconnect}
          isConnected={isConnected}
        />

        {/* Blocked confirmation panel */}
        {blocked && (
          <div className={`blocked ${blocked.blocked_kind === 'danger' ? 'danger' : ''}`}>
            <div className="blocked-header">
              <span className="blocked-icon">
                {blocked.blocked_kind === 'danger' ? '⚡' : '⚠'}
              </span>
              <span className="blocked-label">
                {blocked.blocked_kind === 'danger' ? 'ação perigosa' : 'confirmação necessária'}
              </span>
            </div>
            {(blocked.blocked_note || blocked.blocked_step) && (
              <div className="blocked-note">
                {blocked.blocked_note ?? blocked.blocked_step}
              </div>
            )}
            <div className="blocked-actions">
              {blocked.suggestions.map(s => (
                <button key={s} className={btnClass(s)} onClick={() => onConfirm(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Dev: state switcher */}
        {import.meta.env.DEV && (
          <div className="orb-debug-bar">
            <button
              className={`orb-debug-btn ${debugState === null ? 'active' : ''}`}
              onClick={() => setDebugState(null)}
            >
              live
            </button>
            {DEBUG_STATES.map(s => (
              <button
                key={s}
                className={`orb-debug-btn ${debugState === s ? 'active' : ''}`}
                onClick={() => setDebugState(debugState === s ? null : s)}
              >
                {DEBUG_LABELS[s]}
              </button>
            ))}
          </div>
        )}

      </div>
    </main>
  );
}
