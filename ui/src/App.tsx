import { useEffect } from 'react';
import { useVoice, VoiceStatus } from './hooks/useVoice';
import { LeftSidebar } from './components/LeftSidebar';
import { CenterStage } from './components/CenterStage';
import { RightLog } from './components/RightLog';
import { GitDiffReviewModal } from './components/modal/GitDiffReviewModal';

const STATUS_COLOR: Record<VoiceStatus, string> = {
  disconnected: 'var(--t3)',
  connecting:   'var(--amber)',
  idle:         'var(--cyan)',
  listening:    'var(--cyan)',
  processing:   'var(--amber)',
  speaking:     'var(--violet)',
};

const STATUS_LABEL: Record<VoiceStatus, string> = {
  disconnected: 'desconectado',
  connecting:   'conectando',
  idle:         'aguardando',
  listening:    'ouvindo',
  processing:   'processando',
  speaking:     'falando',
};

export default function App() {
  const {
    status,
    agentState,
    transcript,
    blocked,
    modalPayload,
    lastSkillEvent,
    activityFeed,
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
    clearError,
    clearModal,
  } = useVoice();

  // Auto-connect WebSocket on mount (sem mic — exige gesto do usuário)
  useEffect(() => {
    connect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="app">

      {/* ── Header ── */}
      <header className="hdr">
        <div className="hdr-brand">
          <span className="hdr-brand-pulse" />
          <span className="hdr-brand-name">JARVIS</span>
          <span className="hdr-brand-version">v1</span>
        </div>

        <div className="hdr-center">
          assistente local · macOS
        </div>

        <div className="hdr-right">
          <span className={`hdr-mode ${mode}`}>
            {mode === 'execute' ? 'execute' : 'dry-run'}
          </span>
          <div className="hdr-status" style={{ color: STATUS_COLOR[status] }}>
            <span className="hdr-status-dot" />
            {STATUS_LABEL[status]}
          </div>
        </div>
      </header>

      {/* ── Error Toast ── */}
      {error && (
        <div className="error-toast">
          <span>{error}</span>
          <button className="error-close" onClick={clearError} aria-label="fechar">×</button>
        </div>
      )}

      {/* ── Git Diff Review Modal ── */}
      {modalPayload?.modal_type === 'git_diff_review' && (
        <GitDiffReviewModal
          payload={modalPayload}
          onClose={clearModal}
          onAction={sendConfirmation}
        />
      )}

      {/* ── 3-Column Body ── */}
      <div className="app-body">
        <LeftSidebar status={status} mode={mode} queueData={queueData} skills={skills} metrics={metrics} />

        <CenterStage
          status={status}
          agentState={agentState}
          blocked={blocked}
          lastSkillEvent={lastSkillEvent}
          onStart={startListening}
          onStop={stopListening}
          onSendText={sendConfirmation}
          onConfirm={sendConfirmation}
          onDisconnect={disconnect}
        />

        <RightLog
          entries={transcript}
          activityFeed={activityFeed}
          historyItems={historyItems}
          onRefreshHistory={refreshHistory}
        />
      </div>

    </div>
  );
}
