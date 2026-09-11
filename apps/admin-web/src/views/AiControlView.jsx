import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { Cpu, CheckCircle, XCircle, AlertTriangle, RefreshCw, Zap, TrendingUp, Activity, BarChart } from 'lucide-react';

function StateIndicator({ state }) {
  if (state === 'HEALTHY') return <span className="badge badge-healthy"><CheckCircle size={11} />HEALTHY</span>;
  if (state === 'OPEN') return <span className="badge badge-danger"><XCircle size={11} />OPEN</span>;
  return <span className="badge badge-warning"><AlertTriangle size={11} />HALF-OPEN</span>;
}

function QuotaMeter({ used, limit, source }) {
  const pct = limit > 0 ? Math.min((used / limit) * 100, 100) : 0;
  const color = pct > 85 ? '#ef4444' : pct > 60 ? '#f59e0b' : '#10b981';
  return (
    <div>
      <div style={{ display:'flex',justifyContent:'space-between',fontSize:'0.75rem',marginBottom:4 }}>
        <span style={{ color:'var(--text-dim)' }}>{used.toLocaleString()} / {limit.toLocaleString()}</span>
        <span style={{ color:'var(--text-dim)',fontSize:'0.7rem' }}>{source}</span>
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
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('providers');

  const load = async () => {
    setLoading(true);
    try {
      const [p, q, u] = await Promise.all([
        adminApi.getAiProviders(),
        adminApi.getQuotas(),
        adminApi.getUsageLogs()
      ]);
      setProviders(p); setQuotas(q); setUsage(u);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleToggle = async (modelId, cur) => {
    await adminApi.toggleModel(modelId, !cur); load();
  };

  const handleCbReset = async (modelId) => {
    await adminApi.resetCircuitBreaker(modelId); load();
  };

  const TABS = [
    { key: 'providers', label: 'Providers & Models', icon: Cpu },
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

                    <StateIndicator state={m.health_status} />

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
      ) : activeTab === 'quotas' ? (
        <div style={{ display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))',gap:16 }}>
          {quotas.map(q => (
            <div key={q.id} className="glass-card" style={{ padding:20 }}>
              <div style={{ fontWeight:700,fontSize:'0.9rem',marginBottom:4 }}>{q.model_name}</div>
              <div style={{ fontSize:'0.75rem',color:'var(--text-dim)',marginBottom:14,fontFamily:'var(--font-mono)' }}>{q.model_identifier} · {q.quota_type}</div>
              <QuotaMeter used={q.used} limit={q.limit} source={q.source} />
              {q.reset_time && <div style={{ marginTop:8,fontSize:'0.72rem',color:'var(--text-dim)' }}>Resets: {new Date(q.reset_time).toLocaleString()}</div>}
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
                    {l.success
                      ? <span className="badge badge-healthy" style={{ fontSize:'0.7rem' }}><CheckCircle size={10} />OK</span>
                      : <span className="badge badge-danger" style={{ fontSize:'0.7rem' }}><XCircle size={10} />{l.error_type || 'FAIL'}</span>}
                  </td>
                  <td>
                    {l.failover_occurred
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
