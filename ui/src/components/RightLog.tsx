import { useEffect, useRef, useState } from 'react';
import { TranscriptEntry, HistoryItem, ActivityEvent, ActivityEventType } from '../hooks/useVoice';

// ── Formatters ────────────────────────────────────────────────────────────────

function fmtTime(d: Date) {
  return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function fmtHistTime(iso: string) {
  try {
    return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch { return iso; }
}

// ── Session entries ───────────────────────────────────────────────────────────

const ROLE_LABEL: Record<TranscriptEntry['role'], string> = {
  user:      'você',
  assistant: 'jarvis',
  system:    'sistema',
};

function MessageEntry({ entry }: { entry: TranscriptEntry }) {
  return (
    <div className={`msg ${entry.role}`}>
      <div className="msg-meta">
        <span className="msg-dot" />
        <span className="msg-role">{ROLE_LABEL[entry.role]}</span>
        <span className="msg-time">{fmtTime(entry.ts)}</span>
      </div>
      <div className="msg-body">{entry.text}</div>
    </div>
  );
}

// ── Activity Feed ─────────────────────────────────────────────────────────────

const ACTIVITY_ICON: Partial<Record<ActivityEventType, string>> = {
  jarvis_command: '→',
  thinking:   '◌',
  planning:   '◈',
  compiling:  '◎',
  executing:  '▷',
  skill_start:'◉',
  skill_done: '◉',
  skill_fail: '◉',
  blocked:    '◈',
  responding: '◌',
  user:       '▸',
  assistant:  '▹',
};

const ACTIVITY_COLOR: Partial<Record<ActivityEventType, string>> = {
  jarvis_command: 'var(--cyan)',
  thinking:   'var(--amber)',
  planning:   'var(--amber)',
  compiling:  'var(--amber)',
  executing:  'var(--cyan)',
  skill_start:'var(--cyan)',
  skill_done: 'var(--mint)',
  skill_fail: 'var(--rose)',
  blocked:    'var(--rose)',
  responding: 'var(--violet)',
  user:       'var(--t2)',
  assistant:  'var(--violet)',
};

function ActivityEntry({ event }: { event: ActivityEvent }) {
  const icon  = ACTIVITY_ICON[event.type]  ?? '·';
  const color = ACTIVITY_COLOR[event.type] ?? 'var(--t3)';

  return (
    <div className={`activity-entry activity-${event.type}`}>
      <span className="activity-icon" style={{ color }}>{icon}</span>
      <span className="activity-label">{event.label}</span>
      <span className="activity-time">{fmtTime(event.ts)}</span>
    </div>
  );
}

// ── History entries ───────────────────────────────────────────────────────────

const STATUS_LABEL: Record<string, string> = {
  done:    'concluído',
  failed:  'falhou',
  blocked: 'bloqueado',
};

function HistoryEntry({ item }: { item: HistoryItem }) {
  return (
    <div className={`hist-entry ${item.status}`}>
      <div className="hist-meta">
        <span className={`hist-dot ${item.status}`} />
        <span className="hist-action">{item.action}</span>
        <span className="hist-status-label">{STATUS_LABEL[item.status] ?? item.status}</span>
        <span className="hist-time">{fmtHistTime(item.ts)}</span>
      </div>
      {item.output && (
        <div className="hist-output">{item.output}</div>
      )}
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({ text = 'nenhuma conversa' }: { text?: string }) {
  return (
    <div className="log-empty">
      <div className="log-empty-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <span className="log-empty-text">{text}</span>
    </div>
  );
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function IconChat() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function IconActivity() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}

function IconHistory() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="12 8 12 12 14 14" />
      <path d="M3.05 11a9 9 0 1 0 .5-3.5" />
      <polyline points="3 4 3 11 10 11" />
    </svg>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

type Tab = 'session' | 'activity' | 'history';

interface Props {
  entries: TranscriptEntry[];
  activityFeed: ActivityEvent[];
  historyItems: HistoryItem[];
  onRefreshHistory: () => void;
}

export function RightLog({ entries, activityFeed, historyItems, onRefreshHistory }: Props) {
  const [tab, setTab] = useState<Tab>('activity');
  const bottomRef      = useRef<HTMLDivElement>(null);
  const activityRef    = useRef<HTMLDivElement>(null);

  // Auto-scroll session
  useEffect(() => {
    if (tab === 'session') {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [entries, tab]);

  // Auto-scroll activity feed para o fim quando chega novos eventos
  useEffect(() => {
    if (tab === 'activity' && activityRef.current) {
      activityRef.current.scrollTop = activityRef.current.scrollHeight;
    }
  }, [activityFeed, tab]);

  // Quando chega evento novo, muda tab automaticamente para activity (se estiver em session)
  const prevActivityLen = useRef(activityFeed.length);
  useEffect(() => {
    if (activityFeed.length > prevActivityLen.current && tab === 'session') {
      // não faz switch automático — usuário pode estar lendo a sessão
    }
    prevActivityLen.current = activityFeed.length;
  }, [activityFeed.length, tab]);

  const handleTabChange = (t: Tab) => {
    setTab(t);
    if (t === 'history') onRefreshHistory();
  };

  const activityCount = activityFeed.length > 0 ? `${activityFeed.length}` : '—';
  const sessionCount  = entries.length      > 0 ? `${entries.length} msg` : '—';

  // Badge de "ao vivo" na aba execução quando há eventos recentes (últimos 3s)
  const lastActivity = activityFeed[activityFeed.length - 1];
  const isLive = lastActivity && (Date.now() - lastActivity.ts.getTime()) < 3500;

  return (
    <aside className="log-panel">
      {/* Tabs */}
      <div className="log-tabs">
        <button
          className={`log-tab ${tab === 'activity' ? 'active' : ''}`}
          onClick={() => handleTabChange('activity')}
        >
          <IconActivity />
          execução
          {isLive && <span className="log-tab-live" />}
        </button>
        <button
          className={`log-tab ${tab === 'session' ? 'active' : ''}`}
          onClick={() => handleTabChange('session')}
        >
          <IconChat />
          sessão
        </button>
        <button
          className={`log-tab ${tab === 'history' ? 'active' : ''}`}
          onClick={() => handleTabChange('history')}
        >
          <IconHistory />
          histórico
        </button>
        <span className="log-tab-count">
          {tab === 'activity' ? activityCount : tab === 'session' ? sessionCount : (historyItems.length > 0 ? `${historyItems.length}` : '—')}
        </span>
      </div>

      {/* Content */}
      <div
        className="log-scroll"
        ref={tab === 'activity' ? activityRef : undefined}
      >
        {tab === 'activity' ? (
          activityFeed.length === 0
            ? <EmptyState text="aguardando execução" />
            : activityFeed.map(e => <ActivityEntry key={e.id} event={e} />)
        ) : tab === 'session' ? (
          entries.length === 0
            ? <EmptyState />
            : entries.map(e => <MessageEntry key={e.id} entry={e} />)
        ) : (
          historyItems.length === 0
            ? <EmptyState text="nenhum histórico" />
            : historyItems.map((item, i) => <HistoryEntry key={i} item={item} />)
        )}
        <div ref={bottomRef} />
      </div>
    </aside>
  );
}
