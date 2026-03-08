import { useState } from 'react';
import type { ModalPayload, DiffFileEntry, DiffSection, DiffInsight, DiffAction } from '../../hooks/useVoice';

// ─── helpers ────────────────────────────────────────────────────────────────

const STATUS_BADGE: Record<string, string> = {
  added:    'badge-mint',
  modified: 'badge-cyan',
  deleted:  'badge-rose',
};

const STATUS_CHAR: Record<string, string> = {
  added:    'A',
  modified: 'M',
  deleted:  'D',
};

const INSIGHT_ICONS: Record<string, string> = {
  ok:      '✓',
  info:    'ℹ',
  warning: '⚠',
  error:   '✗',
};

const INSIGHT_CLASS: Record<string, string> = {
  ok:      'insight-ok',
  info:    'insight-info',
  warning: 'insight-warning',
  error:   'insight-error',
};

const RISK_CLASS: Record<string, string> = {
  high:   'risk-high',
  medium: 'risk-medium',
  low:    'risk-low',
};

function DiffLine({ line }: { line: string }) {
  if (line.startsWith('+') && !line.startsWith('+++')) {
    return <div className="diff-line diff-line-add">{line}</div>;
  }
  if (line.startsWith('-') && !line.startsWith('---')) {
    return <div className="diff-line diff-line-del">{line}</div>;
  }
  if (line.startsWith('@@')) {
    return <div className="diff-line diff-line-hunk">{line}</div>;
  }
  if (line.startsWith('diff ') || line.startsWith('index ') || line.startsWith('---') || line.startsWith('+++')) {
    return <div className="diff-line diff-line-meta">{line}</div>;
  }
  return <div className="diff-line">{line}</div>;
}

function FilesTab({ files }: { files: DiffFileEntry[] }) {
  if (!files.length) return <p className="diff-empty">Nenhum arquivo alterado.</p>;
  return (
    <ul className="diff-file-list">
      {files.map(f => (
        <li key={f.file} className="diff-file-item">
          <span className={`diff-file-badge ${STATUS_BADGE[f.status] ?? 'badge-cyan'}`}>
            {STATUS_CHAR[f.status] ?? '?'}
          </span>
          <span className="diff-file-name">{f.file}</span>
          <span className="diff-file-stats">
            {f.additions > 0 && <span className="stat-add">+{f.additions}</span>}
            {f.deletions > 0 && <span className="stat-del">−{f.deletions}</span>}
          </span>
        </li>
      ))}
    </ul>
  );
}

function DiffTab({ sections }: { sections: DiffSection[] }) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  if (!sections.length) return <p className="diff-empty">Nenhum diff disponível.</p>;
  return (
    <div className="diff-sections">
      {sections.map(sec => {
        const key = sec.file;
        const isOpen = open[key] !== false; // default aberto
        return (
          <div key={key} className="diff-section">
            <button className="diff-section-header" onClick={() => setOpen(p => ({ ...p, [key]: !isOpen }))}>
              <span className={`diff-section-toggle ${isOpen ? 'open' : ''}`}>▶</span>
              <span className="diff-section-file">{sec.file}</span>
              {sec.truncated && <span className="diff-truncated-badge">truncado</span>}
            </button>
            {isOpen && (
              <pre className="diff-viewer">
                {sec.content.split('\n').map((line, i) => (
                  <DiffLine key={i} line={line} />
                ))}
              </pre>
            )}
          </div>
        );
      })}
    </div>
  );
}

function InsightsTab({ insights }: { insights: DiffInsight[] }) {
  if (!insights.length) return <p className="diff-empty">Nenhuma análise disponível.</p>;
  return (
    <ul className="diff-insights">
      {insights.map((ins, i) => (
        <li key={i} className={`diff-insight-item ${INSIGHT_CLASS[ins.level] ?? ''}`}>
          <span className="insight-icon">{INSIGHT_ICONS[ins.level] ?? '·'}</span>
          <span className="insight-message">{ins.message}</span>
        </li>
      ))}
    </ul>
  );
}

// ─── main component ──────────────────────────────────────────────────────────

interface Props {
  payload: ModalPayload;
  onClose: () => void;
  onAction: (command: string) => void;
}

type Tab = 'files' | 'diff' | 'insights';

export function GitDiffReviewModal({ payload, onClose, onAction }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('files');

  const data = payload.payload;
  const { title, summary, meta, sections, actions } = data;
  const riskClass = RISK_CLASS[meta.risk_level] ?? 'risk-low';

  const enabledActions  = actions.filter(a => a.enabled);
  const riskyActionIds  = new Set(enabledActions.filter(a => a.risk === 'risky').map(a => a.id));

  function handleAction(action: DiffAction) {
    onAction(action.command);
    onClose();
  }

  return (
    <div className="diff-overlay" onClick={onClose}>
      <div className="diff-modal" onClick={e => e.stopPropagation()}>

        {/* ── Header ── */}
        <div className="diff-modal-header">
          <div className="diff-modal-title-row">
            <h2 className="diff-modal-title">{title}</h2>
            <button className="diff-modal-close" onClick={onClose} aria-label="fechar">×</button>
          </div>
          <p className="diff-modal-summary">{summary}</p>

          <div className="diff-modal-meta">
            <span className="meta-pill">
              <span className="meta-label">arquivos</span>
              <span className="meta-value">{meta.total_files}</span>
            </span>
            <span className="meta-pill">
              <span className="meta-label stat-add">+{meta.additions}</span>
            </span>
            <span className="meta-pill">
              <span className="meta-label stat-del">−{meta.deletions}</span>
            </span>
            <span className={`risk-badge ${riskClass}`}>
              risco {meta.risk_level}
            </span>
          </div>
        </div>

        {/* ── Tabs ── */}
        <div className="diff-tabs">
          {(['files', 'diff', 'insights'] as Tab[]).map(tab => (
            <button
              key={tab}
              className={`diff-tab ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab === 'files'    ? `Arquivos (${sections.files.length})`    : null}
              {tab === 'diff'     ? `Diff (${sections.diff.length})`         : null}
              {tab === 'insights' ? `Análise (${sections.insights.length})`  : null}
            </button>
          ))}
        </div>

        {/* ── Tab Content ── */}
        <div className="diff-tab-content">
          {activeTab === 'files'    && <FilesTab    files={sections.files}       />}
          {activeTab === 'diff'     && <DiffTab     sections={sections.diff}     />}
          {activeTab === 'insights' && <InsightsTab insights={sections.insights} />}
        </div>

        {/* ── Actions ── */}
        {enabledActions.length > 0 && (
          <div className="diff-actions">
            {enabledActions.map(action => (
              <button
                key={action.id}
                className={`diff-action-btn ${riskyActionIds.has(action.id) ? 'risky' : ''}`}
                title={action.description}
                onClick={() => handleAction(action)}
              >
                {action.label}
              </button>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}
