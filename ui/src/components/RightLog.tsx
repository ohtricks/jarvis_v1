import { useEffect, useRef } from 'react';
import { TranscriptEntry } from '../hooks/useVoice';

function fmtTime(d: Date) {
  return d.toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

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

function EmptyState() {
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
      <span className="log-empty-text">nenhuma conversa</span>
    </div>
  );
}

interface Props {
  entries: TranscriptEntry[];
}

export function RightLog({ entries }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  return (
    <aside className="log-panel">
      <div className="log-header">
        <span className="log-header-title">sessão</span>
        <span className="log-header-count">
          {entries.length > 0 ? `${entries.length} msg` : '—'}
        </span>
      </div>

      <div className="log-scroll">
        {entries.length === 0 ? (
          <EmptyState />
        ) : (
          entries.map(e => <MessageEntry key={e.id} entry={e} />)
        )}
        <div ref={bottomRef} />
      </div>
    </aside>
  );
}
