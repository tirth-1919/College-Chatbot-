import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { Cpu, CheckCircle, XCircle, AlertTriangle, RefreshCw, Zap, TrendingUp, Activity, BarChart, KeyRound, FlaskConical, RotateCw, Trash2, Play } from 'lucide-react';

function StateIndicator({ state }) {
  if (!state) return <span className="badge badge-neutral">UNKNOWN</span>;
  const s = String(state).toUpperCase();
  if (s === 'HEALTHY' || s === 'AVAILABLE') return <span className="badge badge-healthy"><CheckCircle size={11} />{s}</span>;
  if (s === 'OPEN' || s === 'CIRCUIT_OPEN' || s === 'UNREACHABLE' || s === 'QUOTA_EXHAUSTED' || s === 'RATE_LIMITED')
    return <span className="badge badge-danger"><XCircle size={11} />{s.replace('_', ' ')}</span>;
  if (s === 'DISABLED' || s === 'API_KEY_MISSING' || s === 'NOT_CONFIGURED')
    return <span className="badge badge-neutral"><XCircle size={11} />{s.replace('_', ' ')}</span>;
  return <span className="badge badge-warning"><AlertTriangle size={11} />{s.replace('_', ' ')}</span>;
}

function ApiKeyIndicator({ status, source }) {
  const s = String(status || 'UNKNOWN').toUpperCase();
  const color = s === 'CONFIGURED' ? '#34d399' : s === 'NOT_REQUIRED' ? '#818cf8' : '#f87171';
  return (
    <span style={{ display:'inline-flex',alignItems:'center',gap:5,fontSize:'0.72rem',fontFamily:'var(--font-mono)',color }}>
      <span style={{ width:7,height:7,borderRadius:9999,background:color,display:'inline-block' }} />
      API Key: {s}{s === 'CONFIGURED' ? ' (********)' : ''}
      <span style={{ color:'var(--text-dim)' }}>· source: {source || '—'}</span>
    </span>
  );
}

function QuotaMeter({ used, limit, source, quotaStatus, usageLabel }) {
  // Never render a percentage for UNKNOWN quota — local counters are NOT provider quota
  if (quotaStatus === 'UNKNOWN' || usageLabel !== 'PROVIDER QUOTA' || !limit) {
    return (
      <div>
        <div style={{ display:'flex',justifyContent:'space-between',fontSize:'0.75rem',marginBottom:4 }}>
          <span style={{ color:'var(--text-dim)' }}>Usage: {used != null ? used.toLocaleString() : '—'}</span>
          <span style={{ color:'var(--text-dim)',fontSize:'0.7rem' }}>{usageLabel || source}</span>
        </div>
        <div style={{ fontSize:'0.75rem',fontWeight:600,color:'#9ca3af' }}>
          Provider quota: {quotaStatus || 'UNKNOWN'}
        </div>
      </div>
    );
  }
  const pct = limit > 0 ? Math.min((used / limit) * 100, 100) : 0;
  const color = pct > 85 ? '#ef4444' : pct > 60 ? '#f59e0b' : '#10b981';
  return (
    <div>
      <div style={{ display:'flex',justifyContent:'space-between',fontSize:'0.75rem',marginBottom:4 }}>
        <span style={{ color:'var(--text-dim)' }}>{used.toLocaleString()} / {limit.toLocaleString()}</span>
        <span style={{ color:'var(--text-dim)',fontSize:'0.7rem' }}>{usageLabel || source}</span>
      </div>
      <div style={{ height:6,background:'rgba(255,255,255,0.1)',borderRadius:9999,overflow:'hidden' }}>
        <div style={{ height:'100%',width:`${pct}%`,background:color,borderRadius:9999,transition:'width 0.5s ease' }} />
      </div>
      <div style={{ fontSize:'0.7rem',color,marginTop:3,fontWeight:600 }}>{pct.toFixed(1)}% used</div>
    </div>
  );
}

export default function AiControlView() {
  const [providers, setProviders] = useState([]);
  const [quotas, setQuotas] = useState([]);
  const [usage, setUsage] = useState([]);
  const [failoverEvents, setFailoverEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('providers');

  const load = async () => {
    setLoading(true);
    try {
      const [p, q, u, f] = await Promise.all([
        adminApi.getAiProviders(),
        adminApi.getQuotas(),
        adminApi.getUsageLogs(),
        adminApi.getFailoverEvents()
      ]);
      setProviders(p); setQuotas(q); setUsage(u); setFailoverEvents(f);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  // Automatic non-aggressive refresh of runtime/quota state (30s)
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const [p, q, u, f] = await Promise.all([
          adminApi.getAiProviders(), adminApi.getQuotas(), adminApi.getUsageLogs(), adminApi.getFailoverEvents()
        ]);
        setProviders(p); setQuotas(q); setUsage(u); setFailoverEvents(f);
      } catch (e) { /* silent — next tick retries */ }
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleToggle = async (modelId, cur) => {
    await adminApi.toggleModel(modelId, !cur); load();
  };

  const handleCbReset = async (modelId) => {
    await adminApi.resetCircuitBreaker(modelId); load();
  };

  // ------------------- Multi-credential management -------------------
  const [credentials, setCredentials] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [credMsg, setCredMsg] = useState(null);
  const [form, setForm] = useState({
    provider_name: 'gemini', api_key: '', label: '', priority: 2,
    is_enabled: true, free_tier_status: 'UNKNOWN',
  });

  const loadCredentials = async () => {
    try { setCredentials(await adminApi.getCredentials()); } catch (e) { /* silent */ }
  };
  useEffect(() => { loadCredentials(); }, []);

  const handleAddCredential = async (e) => {
    e.preventDefault();
    setCredMsg(null);
    try {
      await adminApi.addCredential(form);
      // clear the secret from frontend state immediately — never keep it around
      setForm({ provider_name: form.provider_name, api_key: '', label: '', priority: 2, is_enabled: true, free_tier_status: 'UNKNOWN' });
      setShowAddForm(false);
      setCredMsg({ ok: true, text: 'API key saved. It is live immediately — no restart required.' });
      loadCredentials();
    } catch (err) {
      setCredMsg({ ok: false, text: err?.message || 'Failed to save credential' });
    }
  };

  const credAction = async (fn, okText) => {
    setCredMsg(null);
    try {
      const res = await fn();
      setCredMsg({ ok: true, text: res?.result ? `Test result: ${res.result}${res.consumes_quota ? ' (consumed a small amount of provider quota)' : ''}` : okText });
      loadCredentials();
    } catch (err) {
      setCredMsg({ ok: false, text: err?.message || 'Action failed' });
    }
  };

  const TABS = [
    { key: 'providers', label: 'Providers & Models', icon: Cpu },
    { key: 'credentials', label: 'API Keys', icon: KeyRound },
    { key: 'quotas', label: 'Quotas', icon: BarChart },
    { key: 'usage', label: 'Usage Logs', icon: Activity },
  ];

  return (
    <div>
      <div style={{ display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:22 }}>
        <div>
          <h1 style={{ fontSize:'1.4rem',fontWeight:800,marginBottom:4 }}>AI Provider Control</h1>
          <p style={{ color:'var(--text-muted)',fontSize:'0.85rem' }}>Multi-provider registry, circuit breakers, quotas, and usage telemetry</p>
        </div>
        <button className="btn-secondary" onClick={load}><RefreshCw size={15} /> Refresh</button>
      </div>

      {/* Tab bar */}
      <div style={{ display:'flex',gap:4,marginBottom:22,background:'rgba(255,255,255,0.04)',borderRadius:10,padding:4,width:'fit-content' }}>
        {TABS.map(({ key, label, icon: Icon }) => (
          <button key={key} onClick={() => setActiveTab(key)} style={{
            padding:'8px 18px', borderRadius:8, border:'none', cursor:'pointer', fontFamily:'var(--font-sans)',
            background: activeTab===key ? 'rgba(240,133,24,0.15)' : 'transparent',
            color: activeTab===key ? '#f08518' : 'var(--text-muted)',
            fontWeight: activeTab===key ? 600 : 400,
            display:'flex',alignItems:'center',gap:8,fontSize:'0.875rem',
            borderBottom: activeTab===key ? '2px solid #f08518' : '2px solid transparent'
          }}><Icon size={15} />{label}</button>
        ))}
      </div>

      {loading ? (
        <div style={{ textAlign:'center',padding:60,color:'var(--text-muted)' }}><Cpu size={28} style={{ opacity:0.4,marginBottom:10 }} /><div>Loading AI control panel...</div></div>
      ) : activeTab === 'providers' ? (
        <div style={{ display:'flex',flexDirection:'column',gap:16 }}>
          {providers.map(p => (
            <div key={p.id} className="glass-card" style={{ padding:20 }}>
              <div style={{ display:'flex',alignItems:'center',gap:12,marginBottom:16 }}>
                <div style={{ width:40,height:40,borderRadius:10,background:'rgba(99,102,241,0.15)',border:'1px solid rgba(99,102,241,0.3)',display:'flex',alignItems:'center',justifyContent:'center' }}>
                  <Cpu size={18} color="#818cf8" />
                </div>
                <div style={{ flex:1 }}>
                  <div style={{ fontWeight:700,fontSize:'1rem' }}>{p.display_name}</div>
                  <div style={{ fontSize:'0.75rem',color:'var(--text-dim)',fontFamily:'var(--font-mono)' }}>{p.provider_name} · Priority: {p.priority}</div>
                  <div style={{ marginTop:6 }}><ApiKeyIndicator status={p.api_key_status} source={p.api_key_source} /></div>
                </div>
                <span className={`badge ${p.is_enabled ? 'badge-healthy' : 'badge-neutral'}`}>
                  {p.is_enabled ? 'ENABLED' : 'DISABLED'}
                </span>
              </div>

              {/* Models table */}
              <div style={{ marginTop:8 }}>
                {p.models.map(m => (
                  <div key={m.id} style={{
                    display:'flex',alignItems:'center',flexWrap:'wrap',gap:10,padding:'12px 14px',
                    borderRadius:8,background:'rgba(255,255,255,0.03)',
                    border:'1px solid var(--border-subtle)',marginBottom:8
                  }}>
                    <div style={{ flex:1,minWidth:180 }}>
                      <div style={{ fontWeight:600,fontSize:'0.9rem' }}>{m.display_name}</div>
                      <div style={{ fontFamily:'var(--font-mono)',fontSize:'0.75rem',color:'var(--text-dim)',marginTop:2 }}>{m.model_identifier}</div>
                    </div>

                    <StateIndicator state={m.runtime_state} />

                    {/* Runtime detail: quota / cooldown / failover */}
                    <div style={{ fontSize:'0.72rem',color:'var(--text-dim)',fontFamily:'var(--font-mono)',minWidth:200 }}>
                      <div>Quota: {m.quota_status || 'UNKNOWN'}</div>
                      <div>Cooldown: {m.cooldown_active && m.cooldown_until ? `ACTIVE until ${new Date(m.cooldown_until).toLocaleTimeString()}` : '—'}</div>
                      <div>Failovers: {m.failover_count || 0} · 429s: {m.rate_limit_429_count}</div>
                      {m.last_error_message && <div style={{ color:'#f87171',maxWidth:260,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap' }} title={m.last_error_message}>Last: {m.last_error_type || 'ERROR'}</div>}
                    </div>

                    <div style={{ display:'flex',gap:6,flexWrap:'wrap' }}>
                      {m.capabilities.vision && <span className="badge badge-ait" style={{ fontSize:'0.65rem' }}>Vision</span>}
                      {m.capabilities.streaming && <span className="badge badge-neutral" style={{ fontSize:'0.65rem' }}>Stream</span>}
                      {m.capabilities.documents && <span className="badge badge-neutral" style={{ fontSize:'0.65rem' }}>Docs</span>}
                    </div>

                    <div style={{ textAlign:'right',fontSize:'0.78rem',color:'var(--text-dim)' }}>
                      <div>P95: {m.p95_latency_ms || m.avg_latency_ms || 0}ms</div>
                      <div>Fail: {m.requests_failed}/{m.requests_total}</div>
                    </div>

                    <div style={{ display:'flex',gap:8 }}>
                      {m.health_status !== 'HEALTHY' && (
                        <button className="btn-secondary" style={{ padding:'5px 12px',fontSize:'0.78rem' }} onClick={() => handleCbReset(m.id)}>
                          <Zap size={13} /> Reset CB
                        </button>
                      )}
                      <button
                        onClick={() => handleToggle(m.id, m.is_enabled)}
                        style={{
                          padding:'5px 14px', borderRadius:6, border:'none', cursor:'pointer',
                          background: m.is_enabled ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)',
                          color: m.is_enabled ? '#f87171' : '#34d399',
                          fontWeight:600, fontSize:'0.78rem', fontFamily:'var(--font-sans)'
                        }}
                      >
                        {m.is_enabled ? 'Disable' : 'Enable'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : activeTab === 'credentials' ? (
        <div style={{ display:'flex',flexDirection:'column',gap:16 }}>
          <div style={{ display:'flex',justifyContent:'space-between',alignItems:'center' }}>
            <div style={{ fontSize:'0.85rem',color:'var(--text-muted)' }}>
              Multiple keys per provider with automatic rotation. Keys are encrypted at rest and never displayed after saving.
            </div>
            <button className="btn-secondary" onClick={() => setShowAddForm(s => !s)}><KeyRound size={15} /> Add API Key</button>
          </div>

          {credMsg && (
            <div style={{ padding:'10px 14px',borderRadius:8,fontSize:'0.85rem',background:credMsg.ok ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',color:credMsg.ok ? '#34d399' : '#f87171' }}>
              {credMsg.text}
            </div>
          )}

          {showAddForm && (
            <form className="glass-card" style={{ padding:20,display:'flex',flexWrap:'wrap',gap:12,alignItems:'flex-end' }} onSubmit={handleAddCredential}>
              <label style={{ display:'flex',flexDirection:'column',gap:4,fontSize:'0.78rem',color:'var(--text-dim)' }}>
                Provider
                <select value={form.provider_name} onChange={e => setForm({ ...form, provider_name: e.target.value })}
                  style={{ padding:'8px 10px',borderRadius:6,background:'rgba(255,255,255,0.05)',border:'1px solid var(--border-subtle)',color:'var(--text-muted)',minWidth:130 }}>
                  {['gemini','groq','openrouter','openai','anthropic','ollama'].map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </label>
              <label style={{ display:'flex',flexDirection:'column',gap:4,fontSize:'0.78rem',color:'var(--text-dim)' }}>
                API Key
                <input type="password" required value={form.api_key} onChange={e => setForm({ ...form, api_key: e.target.value })}
                  placeholder="Paste key — never shown again"
                  style={{ padding:'8px 10px',borderRadius:6,background:'rgba(255,255,255,0.05)',border:'1px solid var(--border-subtle)',color:'var(--text-muted)',minWidth:220 }} />
              </label>
              <label style={{ display:'flex',flexDirection:'column',gap:4,fontSize:'0.78rem',color:'var(--text-dim)' }}>
                Label
                <input value={form.label} onChange={e => setForm({ ...form, label: e.target.value })} placeholder="Gemini Production Key 2"
                  style={{ padding:'8px 10px',borderRadius:6,background:'rgba(255,255,255,0.05)',border:'1px solid var(--border-subtle)',color:'var(--text-muted)',minWidth:180 }} />
              </label>
              <label style={{ display:'flex',flexDirection:'column',gap:4,fontSize:'0.78rem',color:'var(--text-dim)' }}>
                Priority
                <input type="number" min="1" value={form.priority} onChange={e => setForm({ ...form, priority: parseInt(e.target.value || '1', 10) })}
                  style={{ padding:'8px 10px',borderRadius:6,background:'rgba(255,255,255,0.05)',border:'1px solid var(--border-subtle)',color:'var(--text-muted)',width:80 }} />
              </label>
              <label style={{ display:'flex',flexDirection:'column',gap:4,fontSize:'0.78rem',color:'var(--text-dim)' }}>
                Free Tier
                <select value={form.free_tier_status} onChange={e => setForm({ ...form, free_tier_status: e.target.value })}
                  style={{ padding:'8px 10px',borderRadius:6,background:'rgba(255,255,255,0.05)',border:'1px solid var(--border-subtle)',color:'var(--text-muted)',minWidth:150 }}>
                  {['UNKNOWN','FREE_TIER_ELIGIBLE','PAID','NOT_APPLICABLE'].map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </label>
              <button className="btn-secondary" type="submit"><CheckCircle size={15} /> Save API Key</button>
            </form>
          )}

          {credentials.length === 0 ? (
            <div className="glass-card" style={{ padding:24,color:'var(--text-muted)',fontSize:'0.85rem' }}>
              No managed credentials yet. The system falls back to environment-configured keys.
            </div>
          ) : credentials.map(c => (
            <div key={c.id} className="glass-card" style={{ padding:18,display:'flex',flexWrap:'wrap',gap:14,alignItems:'center' }}>
              <div style={{ flex:1,minWidth:200 }}>
                <div style={{ fontWeight:700,fontSize:'0.9rem' }}>{c.label || '(unlabelled)'}</div>
                <div style={{ fontFamily:'var(--font-mono)',fontSize:'0.78rem',color:'var(--text-dim)',marginTop:2 }}>
                  {c.provider_name} · {c.masked_key} · Priority: {c.priority} · Free: {c.free_tier_status}
                </div>
              </div>
              <StateIndicator state={c.runtime?.runtime_state} />
              <div style={{ fontSize:'0.72rem',color:'var(--text-dim)',fontFamily:'var(--font-mono)',minWidth:220 }}>
                <div>Quota: {c.quota_remaining} — {c.quota_reason}</div>
                <div>Cooldown: {c.runtime?.cooldown_active && c.runtime?.cooldown_until ? `ACTIVE until ${new Date(c.runtime.cooldown_until).toLocaleTimeString()}` : '—'}</div>
                <div>OK: {c.runtime?.requests_success || 0} · Fail: {c.runtime?.requests_failed || 0} · 429: {c.runtime?.rate_limit_429_count || 0}</div>
                {c.runtime?.failure_type && <div style={{ color:'#f87171' }}>Last failure: {c.runtime.failure_type}</div>}
              </div>
              <div style={{ display:'flex',gap:6,flexWrap:'wrap' }}>
                <button className="btn-secondary" style={{ padding:'5px 10px',fontSize:'0.75rem' }} onClick={() => credAction(() => adminApi.testCredential(c.id))}><FlaskConical size={13} /> Test</button>
                <button className="btn-secondary" style={{ padding:'5px 10px',fontSize:'0.75rem' }} onClick={() => credAction(() => adminApi.recheckCredential(c.id), 'Recheck scheduled — next request will re-probe this key')}><Play size={13} /> Recheck</button>
                <button className="btn-secondary" style={{ padding:'5px 10px',fontSize:'0.75rem' }} onClick={() => credAction(() => adminApi.rotateCredential(c.id), 'Key moved to lowest priority — next key tried first')}><RotateCw size={13} /> Rotate</button>
                <button className="btn-secondary" style={{ padding:'5px 10px',fontSize:'0.75rem' }} onClick={() => credAction(() => adminApi.updateCredential(c.id, { is_enabled: !c.is_enabled }), c.is_enabled ? 'Key disabled — live immediately' : 'Key enabled — live immediately')}>
                  {c.is_enabled ? 'Disable' : 'Enable'}
                </button>
                <button className="btn-secondary" style={{ padding:'5px 10px',fontSize:'0.75rem',color:'#f87171' }}
                  onClick={() => { if (window.confirm('Delete this API key?')) credAction(() => adminApi.deleteCredential(c.id), 'Key deleted — live immediately'); }}>
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : activeTab === 'quotas' ? (
        <div style={{ display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))',gap:16 }}>
          {quotas.map(q => (
            <div key={q.id} className="glass-card" style={{ padding:20 }}>
              <div style={{ fontWeight:700,fontSize:'0.9rem',marginBottom:4 }}>{q.model_name}</div>
              <div style={{ fontSize:'0.75rem',color:'var(--text-dim)',marginBottom:10,fontFamily:'var(--font-mono)' }}>{q.model_identifier} · {q.quota_type}</div>
              <div style={{ marginBottom:10,display:'flex',gap:6,flexWrap:'wrap' }}>
                <StateIndicator state={q.quota_status} />
                {q.runtime_state && <StateIndicator state={q.runtime_state} />}
              </div>
              <div style={{ fontSize:'0.72rem',color:'var(--text-dim)',marginBottom:8,fontFamily:'var(--font-mono)' }}>
                Usage basis: {q.usage_label || q.source}
              </div>
              <QuotaMeter used={q.used} limit={q.limit} source={q.source} quotaStatus={q.quota_status} usageLabel={q.usage_label} />
              <div style={{ marginTop:8,fontSize:'0.72rem',color:'var(--text-dim)' }}>
                Reset: {q.reset_time ? new Date(q.reset_time).toLocaleString() : 'UNKNOWN'}
                {q.cooldown_active && q.cooldown_until ? ` · Cooldown ACTIVE until ${new Date(q.cooldown_until).toLocaleTimeString()}` : ''}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr><th>Time</th><th>Provider</th><th>Model</th><th>Tokens</th><th>Latency</th><th>Status</th><th>Failover</th></tr>
            </thead>
            <tbody>
              {usage.map(l => (
                <tr key={l.id}>
                  <td style={{ fontSize:'0.78rem',color:'var(--text-dim)',fontFamily:'var(--font-mono)' }}>{l.timestamp ? new Date(l.timestamp).toLocaleTimeString() : '—'}</td>
                  <td style={{ fontWeight:600 }}>{l.provider_name}</td>
                  <td style={{ fontFamily:'var(--font-mono)',fontSize:'0.78rem',color:'var(--text-muted)' }}>{l.model_identifier}</td>
                  <td style={{ color:'var(--text-muted)',fontSize:'0.85rem' }}>{l.total_tokens > 0 ? l.total_tokens.toLocaleString() : '—'}</td>
                  <td style={{ color:'var(--text-muted)',fontSize:'0.85rem' }}>{l.latency_ms > 0 ? `${Math.round(l.latency_ms)}ms` : '—'}</td>
                  <td>
                    {l.provider_name === 'FINAL'
                      ? <span className="badge badge-danger" style={{ fontSize:'0.7rem' }}><XCircle size={10} />{l.model_identifier}</span>
                      : l.success
                        ? <span className="badge badge-healthy" style={{ fontSize:'0.7rem' }}><CheckCircle size={10} />OK</span>
                        : <span className="badge badge-danger" style={{ fontSize:'0.7rem' }}><XCircle size={10} />{l.error_type || 'FAIL'}</span>}
                  </td>
                  <td>
                    {l.provider_name === 'FINAL'
                      ? <span style={{ color:'#f87171',fontSize:'0.8rem' }}>Decision chain ended</span>
                      : l.failover_occurred && l.fallback_from_model
                        ? <span className="badge badge-warning" style={{ fontSize:'0.7rem' }}>{l.fallback_from_model} → {l.model_identifier}</span>
                        : l.failover_occurred
                          ? <span className="badge badge-warning" style={{ fontSize:'0.7rem' }}>Failover</span>
                          : <span style={{ color:'var(--text-dim)',fontSize:'0.8rem' }}>—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
