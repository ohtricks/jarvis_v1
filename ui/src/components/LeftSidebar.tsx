import { VoiceStatus, QueueData, SystemMetrics } from '../hooks/useVoice';

function groupSkills(skills: string[]): { ns: string; count: number }[] {
  const map: Record<string, number> = {};
  for (const s of skills) {
    const ns = s.startsWith('google_gmail_') ? 'google.gmail'
             : s.startsWith('git_')          ? 'dev'
             : 'system';
    map[ns] = (map[ns] ?? 0) + 1;
  }
  return Object.entries(map).map(([ns, count]) => ({ ns, count }));
}

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

interface ConnStatus { ws: boolean; gemini: boolean; }

function getConnStatus(status: VoiceStatus): ConnStatus {
  return {
    ws:     status !== 'disconnected',
    gemini: ['idle', 'listening', 'processing', 'speaking'].includes(status),
  };
}

function ConnBadge({ ok, wait }: { ok: boolean; wait?: boolean }) {
  if (wait) return <span className="sidebar-conn-badge wait">aguardando</span>;
  return <span className={`sidebar-conn-badge ${ok ? 'ok' : 'off'}`}>{ok ? 'online' : 'offline'}</span>;
}

interface Props {
  status: VoiceStatus;
  mode: 'dry' | 'execute';
  queueData: QueueData | null;
  skills: string[];
  metrics: SystemMetrics;
}

export function LeftSidebar({ status, mode, queueData, skills, metrics }: Props) {
  const conn      = getConnStatus(status);
  const isExecute = mode === 'execute';
  const grouped   = groupSkills(skills);
  const queueActive = queueData && queueData.total > 0;

  const cpuVal  = metrics.cpu  ?? 0;
  const ramVal  = metrics.ram  ?? 0;
  const cpuStr  = metrics.cpu  != null ? `${Math.round(metrics.cpu)}%`  : '--';
  const ramStr  = metrics.ram  != null ? `${Math.round(metrics.ram)}%`  : '--';
  const pingStr = metrics.wsPing != null ? `${metrics.wsPing} ms`        : '--';
  const llmStr  = metrics.llmMs  != null ? `${(metrics.llmMs / 1000).toFixed(1)} s` : '--';

  return (
    <aside className="sidebar">

      {/* Sistema */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">sistema</div>

        <div className="sidebar-stat">
          <div className="sidebar-stat-row">
            <span className="sidebar-stat-label">CPU</span>
            <span className="sidebar-stat-val">{cpuStr}</span>
          </div>
          <StatBar value={cpuVal} />
        </div>

        <div className="sidebar-stat">
          <div className="sidebar-stat-row">
            <span className="sidebar-stat-label">RAM</span>
            <span className="sidebar-stat-val">{ramStr}</span>
          </div>
          <StatBar value={ramVal} color="violet" />
        </div>

        <div className="sidebar-stat">
          <div className="sidebar-stat-row">
            <span className="sidebar-stat-label">WS PING</span>
            <span className="sidebar-stat-val">{pingStr}</span>
          </div>
        </div>

        <div className="sidebar-stat">
          <div className="sidebar-stat-row">
            <span className="sidebar-stat-label">ÚLTIMO LLM</span>
            <span className="sidebar-stat-val">{llmStr}</span>
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
        <div className="sidebar-model-name">claude-sonnet-4.6</div>
        <div className="sidebar-model-sub">raciocínio · agent</div>
        <div style={{ marginTop: 10 }}>
          <div className="sidebar-model-name">gemini-2.5-flash</div>
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

      {/* Fila de tarefas — dados reais via GET /api/status */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">
          fila de tarefas
          {queueActive && (
            <span className="sidebar-section-badge">{queueData!.total}</span>
          )}
        </div>

        {!queueActive ? (
          <span className="sidebar-queue-empty">nenhuma tarefa ativa</span>
        ) : (
          <div className="sidebar-queue-rows">
            {queueData!.running > 0 && (
              <div className="sidebar-queue-row running">
                <span>executando</span><span>{queueData!.running}</span>
              </div>
            )}
            {queueData!.pending > 0 && (
              <div className="sidebar-queue-row">
                <span>pendente</span><span>{queueData!.pending}</span>
              </div>
            )}
            {queueData!.blocked > 0 && (
              <div className="sidebar-queue-row blocked">
                <span>bloqueado</span><span>{queueData!.blocked}</span>
              </div>
            )}
            {queueData!.done > 0 && (
              <div className="sidebar-queue-row done">
                <span>concluído</span><span>{queueData!.done}</span>
              </div>
            )}
            {queueData!.failed > 0 && (
              <div className="sidebar-queue-row failed">
                <span>falhou</span><span>{queueData!.failed}</span>
              </div>
            )}
            {queueData!.skipped > 0 && (
              <div className="sidebar-queue-row">
                <span>ignorado</span><span>{queueData!.skipped}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Skills — dados reais via GET /api/skills */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">
          skills
          {skills.length > 0 && (
            <span className="sidebar-section-badge">{skills.length}</span>
          )}
        </div>

        {grouped.length === 0 ? (
          <span className="sidebar-queue-empty">carregando…</span>
        ) : (
          grouped.map(s => (
            <div key={s.ns} className="sidebar-skill-row">
              <span className="sidebar-skill-ns">{s.ns}</span>
              <span className="sidebar-skill-count">{s.count}</span>
            </div>
          ))
        )}
      </div>

    </aside>
  );
}
