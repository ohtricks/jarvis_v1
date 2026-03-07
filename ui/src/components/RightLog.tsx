import { useEffect, useRef, useState } from 'react';
import { TranscriptEntry, HistoryItem } from '../hooks/useVoice';

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

type Tab = 'session' | 'history';

interface Props {
  entries: TranscriptEntry[];
  historyItems: HistoryItem[];
  onRefreshHistory: () => void;
}

export function RightLog({ entries, historyItems, onRefreshHistory }: Props) {
  const [tab, setTab] = useState<Tab>('session');
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll quando novas mensagens chegam na aba sessão
  useEffect(() => {
    if (tab === 'session') {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [entries, tab]);

  const handleTabChange = (t: Tab) => {
    setTab(t);
    if (t === 'history') onRefreshHistory();
  };

  const count = tab === 'session'
    ? (entries.length > 0 ? `${entries.length} msg` : '—')
    : (historyItems.length > 0 ? `${historyItems.length}` : '—');

  return (
    <aside className="log-panel">
      {/* Tabs */}
      <div className="log-tabs">
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
        <span className="log-tab-count">{count}</span>
      </div>

      {/* Content */}
      <div className="log-scroll">
        {tab === 'session' ? (
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
