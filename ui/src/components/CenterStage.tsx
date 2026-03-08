import { useState } from 'react';
import { VoiceStatus, AgentState, BlockedInfo, SkillEvent } from '../hooks/useVoice';
import { useSkillBubbles, MOCK_SKILLS } from '../hooks/useSkillBubbles';
import { VoiceOrb } from './VoiceOrb';
import { ControlBar } from './ControlBar';
import { SkillBubbleLayer } from './orb/SkillBubbleLayer';

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
  agentState: AgentState;
  blocked: BlockedInfo | null;
  lastSkillEvent: SkillEvent | null;
  onStart: () => void;
  onStop: () => void;
  onSendText: (text: string) => void;
  onConfirm: (text: string) => void;
  onDisconnect: () => void;
}

export function CenterStage({
  status,
  agentState,
  blocked,
  lastSkillEvent,
  onStart,
  onStop,
  onSendText,
  onConfirm,
  onDisconnect,
}: Props) {
  const isConnected = status !== 'disconnected' && status !== 'connecting';
  const [debugState, setDebugState] = useState<VoiceStatus | null>(null);
  const effectiveStatus = debugState ?? status;

  const { bubbles, removeBubble, spawnBubble } = useSkillBubbles(lastSkillEvent);

  return (
    <main className="stage">

      {/* Skill execution bubbles — nascem com a skill e saem quando termina */}
      <SkillBubbleLayer bubbles={bubbles} onRemove={removeBubble} />

      <div className="stage-inner">

        {/* Orb — reage ao estado de voz E ao estado do agente */}
        <VoiceOrb status={effectiveStatus} agentState={agentState} />

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

        {/* Dev: state switcher + skill bubble mock */}
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
            <span className="orb-debug-sep" />
            <button className="orb-debug-btn" onClick={() => spawnBubble()}>
              +bubble
            </button>
            <button
              className="orb-debug-btn"
              onClick={() => MOCK_SKILLS.forEach((s, i) => setTimeout(() => spawnBubble(s), i * 350))}
            >
              burst
            </button>
          </div>
        )}

      </div>
    </main>
  );
}
