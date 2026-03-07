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

  return (
    <main className="stage">
      <div className="stage-inner">

        {/* Orb */}
        <VoiceOrb status={status} />

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

      </div>
    </main>
  );
}
