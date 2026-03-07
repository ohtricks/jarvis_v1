import { VoiceStatus } from '../hooks/useVoice';

// ── Placeholder data (replace with real data when backend exposes it) ──────────
const MOCK = {
  cpu: 23,
  ram: 61,
  latency: 12,
  modelMain: 'claude-sonnet-4.6',
  modelVoice: 'gemini-2.5-flash',
  skills: [
    { ns: 'system', count: 3 },
    { ns: 'dev', count: 4 },
    { ns: 'google.gmail', count: 6 },
  ],
};

function StatBar({ value, color = '' }: { value: number; color?: string }) {
  return (
    <div className="sidebar-bar">
      <div
        className={`sidebar-bar-fill ${color}`}
        style={{ '--val': `${value}%` } as React.CSSProperties}
      />
    </div>
  );
}

interface ConnStatus {
  ws: boolean;
  gemini: boolean;
}

function getConnStatus(status: VoiceStatus): ConnStatus {
  return {
    ws:     status !== 'disconnected',
    gemini: status === 'idle' || status === 'listening' || status === 'processing' || status === 'speaking',
  };
}

function ConnBadge({ ok, wait }: { ok: boolean; wait?: boolean }) {
  if (wait) return <span className="sidebar-conn-badge wait">aguardando</span>;
  return <span className={`sidebar-conn-badge ${ok ? 'ok' : 'off'}`}>{ok ? 'online' : 'offline'}</span>;
}

interface Props {
  status: VoiceStatus;
  mode: 'dry' | 'execute';
}

export function LeftSidebar({ status, mode }: Props) {
  const conn = getConnStatus(status);
  const isExecute = mode === 'execute';

  return (
    <aside className="sidebar">

      {/* Sistema */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">sistema</div>

        <div className="sidebar-stat">
          <div className="sidebar-stat-row">
            <span className="sidebar-stat-label">CPU</span>
            <span className="sidebar-stat-val">{MOCK.cpu}%</span>
          </div>
          <StatBar value={MOCK.cpu} />
        </div>

        <div className="sidebar-stat">
          <div className="sidebar-stat-row">
            <span className="sidebar-stat-label">RAM</span>
            <span className="sidebar-stat-val">{MOCK.ram}%</span>
          </div>
          <StatBar value={MOCK.ram} color="violet" />
        </div>

        <div className="sidebar-stat">
          <div className="sidebar-stat-row">
            <span className="sidebar-stat-label">LATÊNCIA</span>
            <span className="sidebar-stat-val">{MOCK.latency} ms</span>
          </div>
        </div>
      </div>

      {/* Conexões */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">conexão</div>

        <div className="sidebar-conn-row">
          <span className="sidebar-conn-label">WEBSOCKET</span>
          <ConnBadge ok={conn.ws} />
        </div>

        <div className="sidebar-conn-row">
          <span className="sidebar-conn-label">GEMINI</span>
          <ConnBadge ok={conn.gemini} wait={status === 'connecting'} />
        </div>
      </div>

      {/* Modelos */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">modelos</div>
        <div className="sidebar-model-name">{MOCK.modelMain}</div>
        <div className="sidebar-model-sub">raciocínio · agent</div>
        <div style={{ marginTop: 10 }}>
          <div className="sidebar-model-name">{MOCK.modelVoice}</div>
          <div className="sidebar-model-sub">voz nativa · gemini live</div>
        </div>
      </div>

      {/* Modo */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">modo</div>
        <div className={`sidebar-mode-badge ${isExecute ? 'execute' : ''}`}>
          <span className="sidebar-mode-badge-dot" />
          <span className="sidebar-mode-badge-text">{isExecute ? 'execute' : 'dry-run'}</span>
        </div>
      </div>

      {/* Fila */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">fila de tarefas</div>
        <span className="sidebar-queue-empty">nenhuma tarefa ativa</span>
      </div>

      {/* Skills */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">skills</div>
        {MOCK.skills.map(s => (
          <div key={s.ns} className="sidebar-skill-row">
            <span className="sidebar-skill-ns">{s.ns}</span>
            <span className="sidebar-skill-count">{s.count}</span>
          </div>
        ))}
      </div>

    </aside>
  );
}
