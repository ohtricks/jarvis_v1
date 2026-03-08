import { useState, useEffect, useCallback, useRef } from 'react';

const API = 'http://127.0.0.1:8899';

// ── Types ─────────────────────────────────────────────────────────────────────

interface Account {
  alias: string;
  connected: boolean;
}

interface AccountsData {
  gmail: Account[];
  outlook: Account[];
}

type Provider = 'gmail' | 'outlook';

interface GmailFlowState {
  status: 'idle' | 'pending' | 'connected' | 'error';
  error?: string;
}

interface OutlookFlowState {
  status: 'idle' | 'pending' | 'connected' | 'error';
  user_code?: string;
  verification_url?: string;
  error?: string;
}

// ── API helpers ───────────────────────────────────────────────────────────────

async function fetchAccounts(): Promise<AccountsData> {
  const r = await fetch(`${API}/api/auth/accounts`);
  if (!r.ok) throw new Error('Falha ao carregar contas');
  return r.json();
}

async function disconnectAccount(provider: Provider, alias: string): Promise<void> {
  const r = await fetch(`${API}/api/auth/${provider}/${alias}`, { method: 'DELETE' });
  if (!r.ok) throw new Error('Falha ao desconectar');
}

// ── Gmail tab ─────────────────────────────────────────────────────────────────

function GmailTab({ accounts, onRefresh }: { accounts: Account[]; onRefresh: () => void }) {
  const [showForm, setShowForm] = useState(false);
  const [alias, setAlias] = useState('default');
  const [clientSecret, setClientSecret] = useState('');
  const [flow, setFlow] = useState<GmailFlowState>({ status: 'idle' });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback((norm: string) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${API}/api/auth/gmail/status/${norm}`);
        const data = await r.json();
        if (data.status === 'connected') {
          stopPolling();
          setFlow({ status: 'connected' });
          setShowForm(false);
          setClientSecret('');
          onRefresh();
        } else if (data.status === 'error') {
          stopPolling();
          setFlow({ status: 'error', error: data.error || 'Erro desconhecido' });
        }
      } catch {
        // rede instável, ignora
      }
    }, 3000);
  }, [stopPolling, onRefresh]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  async function handleConnect() {
    if (!clientSecret.trim()) return;
    const norm = (alias || 'default').toLowerCase();
    setFlow({ status: 'pending' });
    try {
      const r = await fetch(`${API}/api/auth/gmail/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alias: norm, client_secret: clientSecret }),
      });
      const data = await r.json();
      if (!r.ok) {
        setFlow({ status: 'error', error: data.detail || 'Erro ao iniciar autenticação' });
        return;
      }
      setFlow({ status: 'pending' });
      startPolling(norm);
    } catch (e: any) {
      setFlow({ status: 'error', error: e.message });
    }
  }

  async function handleDisconnect(acAlias: string) {
    try {
      await disconnectAccount('gmail', acAlias);
      onRefresh();
    } catch (e: any) {
      alert(e.message);
    }
  }

  return (
    <div className="st-provider-tab">
      <div className="st-section-title">
        <span className="st-provider-icon">✉</span>
        Gmail (Google)
      </div>

      {accounts.length === 0 && !showForm && (
        <p className="st-empty">Nenhuma conta Gmail conectada.</p>
      )}

      <ul className="st-account-list">
        {accounts.map(ac => (
          <li key={ac.alias} className="st-account-item">
            <span className="st-account-dot connected" />
            <span className="st-account-alias">{ac.alias}</span>
            <span className="st-account-badge">conectado</span>
            <button className="st-btn-ghost st-btn-danger" onClick={() => handleDisconnect(ac.alias)}>
              desconectar
            </button>
          </li>
        ))}
      </ul>

      {!showForm && (
        <button className="st-btn-add" onClick={() => { setShowForm(true); setFlow({ status: 'idle' }); }}>
          + Adicionar conta Gmail
        </button>
      )}

      {showForm && (
        <div className="st-form">
          <div className="st-form-header">
            <span>Nova conta Gmail</span>
            <button className="st-btn-icon" onClick={() => { setShowForm(false); stopPolling(); setFlow({ status: 'idle' }); }}>×</button>
          </div>

          <div className="st-instructions">
            <p>Você precisa de um <strong>OAuth Client ID</strong> do Google Cloud Console:</p>
            <ol>
              <li>Acesse <strong>console.cloud.google.com</strong></li>
              <li>APIs e Serviços → Biblioteca → habilite <strong>Gmail API</strong></li>
              <li>Credenciais → Criar → <strong>ID do cliente OAuth (Desktop app)</strong></li>
              <li>Baixe o JSON e cole o conteúdo abaixo</li>
            </ol>
          </div>

          <label className="st-label">Apelido da conta</label>
          <input
            className="st-input"
            value={alias}
            onChange={e => setAlias(e.target.value)}
            placeholder="ex: pessoal, empresa"
            disabled={flow.status === 'pending'}
          />

          <label className="st-label">Conteúdo do client_secret.json</label>
          <textarea
            className="st-textarea"
            value={clientSecret}
            onChange={e => setClientSecret(e.target.value)}
            placeholder={'{\n  "installed": {\n    "client_id": "...",\n    ...\n  }\n}'}
            disabled={flow.status === 'pending'}
            rows={6}
          />

          {flow.status === 'idle' && (
            <button className="st-btn-primary" onClick={handleConnect} disabled={!clientSecret.trim()}>
              Conectar Gmail
            </button>
          )}

          {flow.status === 'pending' && (
            <div className="st-status pending">
              <span className="st-spinner" />
              Navegador aberto para autenticação com o Google. Complete o login e volte aqui...
            </div>
          )}

          {flow.status === 'connected' && (
            <div className="st-status connected">✓ Gmail conectado com sucesso!</div>
          )}

          {flow.status === 'error' && (
            <div className="st-status error">
              <div>✗ Erro: {flow.error}</div>
              <button className="st-btn-ghost" onClick={() => setFlow({ status: 'idle' })}>Tentar novamente</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Outlook tab ───────────────────────────────────────────────────────────────

function OutlookTab({ accounts, onRefresh }: { accounts: Account[]; onRefresh: () => void }) {
  const [showForm, setShowForm] = useState(false);
  const [alias, setAlias] = useState('default');
  const [clientId, setClientId] = useState('');
  const [accountType, setAccountType] = useState<'personal' | 'org' | 'tenant'>('tenant');
  const [tenantId, setTenantId] = useState('');
  const [flow, setFlow] = useState<OutlookFlowState>({ status: 'idle' });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback((norm: string) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${API}/api/auth/outlook/poll/${norm}`);
        const data = await r.json();
        if (data.status === 'connected') {
          stopPolling();
          setFlow({ status: 'connected' });
          setShowForm(false);
          setClientId('');
          onRefresh();
        } else if (data.status === 'error') {
          stopPolling();
          setFlow({ status: 'error', error: data.error || 'Erro desconhecido' });
        }
        // 'pending' → continua polling
      } catch {
        // ignora erros de rede
      }
    }, 5000);
  }, [stopPolling, onRefresh]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  async function handleConnect() {
    if (!clientId.trim()) return;
    const norm = (alias || 'default').toLowerCase();
    setFlow({ status: 'pending' });
    try {
      const r = await fetch(`${API}/api/auth/outlook/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alias: norm, client_id: clientId.trim(), account_type: accountType, tenant_id: tenantId.trim() }),
      });
      const data = await r.json();
      if (!r.ok) {
        setFlow({ status: 'error', error: data.detail || 'Erro ao iniciar autenticação' });
        return;
      }
      setFlow({
        status: 'pending',
        user_code: data.user_code,
        verification_url: data.verification_url,
      });
      startPolling(norm);
    } catch (e: any) {
      setFlow({ status: 'error', error: e.message });
    }
  }

  async function handleDisconnect(acAlias: string) {
    try {
      await disconnectAccount('outlook', acAlias);
      onRefresh();
    } catch (e: any) {
      alert(e.message);
    }
  }

  function copyCode() {
    if (flow.user_code) navigator.clipboard.writeText(flow.user_code);
  }

  return (
    <div className="st-provider-tab">
      <div className="st-section-title">
        <span className="st-provider-icon">📨</span>
        Outlook (Microsoft 365 / Outlook.com)
      </div>

      {accounts.length === 0 && !showForm && (
        <p className="st-empty">Nenhuma conta Outlook conectada.</p>
      )}

      <ul className="st-account-list">
        {accounts.map(ac => (
          <li key={ac.alias} className="st-account-item">
            <span className="st-account-dot connected" />
            <span className="st-account-alias">{ac.alias}</span>
            <span className="st-account-badge">conectado</span>
            <button className="st-btn-ghost st-btn-danger" onClick={() => handleDisconnect(ac.alias)}>
              desconectar
            </button>
          </li>
        ))}
      </ul>

      {!showForm && (
        <button className="st-btn-add" onClick={() => { setShowForm(true); setFlow({ status: 'idle' }); }}>
          + Adicionar conta Outlook
        </button>
      )}

      {showForm && (
        <div className="st-form">
          <div className="st-form-header">
            <span>Nova conta Outlook</span>
            <button className="st-btn-icon" onClick={() => { setShowForm(false); stopPolling(); setFlow({ status: 'idle' }); }}>×</button>
          </div>

          <div className="st-instructions">
            <p>Você precisa de um app registrado no <strong>Azure Portal</strong>:</p>
            <ol>
              <li>Acesse <strong>portal.azure.com</strong></li>
              <li>Pesquise <strong>App registrations</strong> → New registration</li>
              <li>Em <strong>Authentication</strong> → Mobile and desktop → marque o redirect nativo</li>
              <li>Copie o <strong>Application (client) ID</strong> e o <strong>Directory (tenant) ID</strong></li>
            </ol>
          </div>

          <label className="st-label">Tipo de conta</label>
          <select
            className="st-input"
            value={accountType}
            onChange={e => setAccountType(e.target.value as 'personal' | 'org' | 'tenant')}
            disabled={flow.status === 'pending'}
          >
            <option value="tenant">Corporativo — tenant específico (padrão Azure)</option>
            <option value="personal">Pessoal (Outlook.com, Hotmail, Live)</option>
            <option value="org">Corporativo multi-tenant (Microsoft 365)</option>
          </select>

          {accountType === 'tenant' && (
            <>
              <label className="st-label">Directory (tenant) ID</label>
              <input
                className="st-input st-input-mono"
                value={tenantId}
                onChange={e => setTenantId(e.target.value)}
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                disabled={flow.status === 'pending'}
              />
            </>
          )}

          <label className="st-label">Apelido da conta</label>
          <input
            className="st-input"
            value={alias}
            onChange={e => setAlias(e.target.value)}
            placeholder="ex: pessoal, empresa"
            disabled={flow.status === 'pending'}
          />

          <label className="st-label">Application (client) ID</label>
          <input
            className="st-input st-input-mono"
            value={clientId}
            onChange={e => setClientId(e.target.value)}
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            disabled={flow.status === 'pending'}
          />

          {flow.status === 'idle' && (
            <button
              className="st-btn-primary"
              onClick={handleConnect}
              disabled={!clientId.trim() || (accountType === 'tenant' && !tenantId.trim())}
            >
              Conectar Outlook
            </button>
          )}

          {flow.status === 'pending' && flow.user_code && (
            <div className="st-device-flow">
              <div className="st-device-flow-title">Autenticação pendente</div>
              <p className="st-device-flow-desc">
                Abra o link abaixo e insira o código para autenticar:
              </p>
              <div className="st-device-code-row">
                <div className="st-device-code">{flow.user_code}</div>
                <button className="st-btn-ghost" onClick={copyCode} title="Copiar código">
                  copiar
                </button>
              </div>
              <a
                className="st-device-link"
                href={flow.verification_url}
                target="_blank"
                rel="noreferrer"
              >
                {flow.verification_url} ↗
              </a>
              <div className="st-status pending">
                <span className="st-spinner" />
                Aguardando autenticação... (verificando a cada 5s)
              </div>
            </div>
          )}

          {flow.status === 'pending' && !flow.user_code && (
            <div className="st-status pending">
              <span className="st-spinner" />
              Iniciando Device Code Flow...
            </div>
          )}

          {flow.status === 'connected' && (
            <div className="st-status connected">✓ Outlook conectado com sucesso!</div>
          )}

          {flow.status === 'error' && (
            <div className="st-status error">
              <div>✗ Erro: {flow.error}</div>
              <button className="st-btn-ghost" onClick={() => setFlow({ status: 'idle' })}>Tentar novamente</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main modal ────────────────────────────────────────────────────────────────

interface Props {
  onClose: () => void;
}

export function SettingsModal({ onClose }: Props) {
  const [tab, setTab] = useState<Provider>('gmail');
  const [accounts, setAccounts] = useState<AccountsData>({ gmail: [], outlook: [] });
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchAccounts();
      setAccounts(data);
    } catch {
      // silencia erros de rede
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // Fecha com Escape
  useEffect(() => {
    const fn = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', fn);
    return () => window.removeEventListener('keydown', fn);
  }, [onClose]);

  return (
    <div className="diff-overlay" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="st-modal" role="dialog" aria-modal="true" aria-label="Configurações">
        {/* Header */}
        <div className="diff-modal-header">
          <div className="diff-modal-title-row">
            <h2 className="diff-modal-title">Configurações · Contas</h2>
            <button className="diff-modal-close" onClick={onClose} aria-label="fechar">×</button>
          </div>
          <p className="diff-modal-summary">Gerencie as contas de email conectadas ao Jarvis</p>
        </div>

        {/* Tabs */}
        <div className="diff-tabs">
          <button
            className={`diff-tab ${tab === 'gmail' ? 'active' : ''}`}
            onClick={() => setTab('gmail')}
          >
            Gmail
            {accounts.gmail.length > 0 && (
              <span className="st-count-badge">{accounts.gmail.length}</span>
            )}
          </button>
          <button
            className={`diff-tab ${tab === 'outlook' ? 'active' : ''}`}
            onClick={() => setTab('outlook')}
          >
            Outlook
            {accounts.outlook.length > 0 && (
              <span className="st-count-badge">{accounts.outlook.length}</span>
            )}
          </button>
        </div>

        {/* Content */}
        <div className="diff-tab-content st-content">
          {loading ? (
            <div className="st-loading">
              <span className="st-spinner" /> Carregando contas...
            </div>
          ) : (
            <>
              {tab === 'gmail' && <GmailTab accounts={accounts.gmail} onRefresh={refresh} />}
              {tab === 'outlook' && <OutlookTab accounts={accounts.outlook} onRefresh={refresh} />}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
