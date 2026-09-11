import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { Lock, AlertTriangle, Shield, Search, Filter } from 'lucide-react';

const ACTION_COLORS = {
  CREATE: '#10b981', UPDATE: '#6366f1', DELETE: '#ef4444',
  LOGIN: '#f08518', LOGOUT: '#64748b',
  ROLE_CHANGE: '#f59e0b', DISABLE: '#ef4444', ENABLE: '#10b981',
  CIRCUIT_RESET: '#818cf8', SYNC: '#22d3ee', ROLLBACK: '#f97316',
};

function RiskBadge({ level }) {
  const map = { LOW:'badge-healthy', MEDIUM:'badge-warning', HIGH:'badge-danger', CRITICAL:'badge-danger' };
  return <span className={`badge ${map[level]||'badge-neutral'}`} style={{ fontSize:'0.7rem' }}>{level}</span>;
}

export default function AuditView() {
  const [logs, setLogs] = useState([]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('audit');
  const [search, setSearch] = useState('');

  useEffect(() => {
    setLoading(true);
    Promise.all([adminApi.getAuditLogs(), adminApi.getSecurityEvents()])
      .then(([l, e]) => { setLogs(l); setEvents(e); })
      .finally(() => setLoading(false));
  }, []);

  const filtered = logs.filter(l =>
    !search || l.action?.toLowerCase().includes(search.toLowerCase()) || l.admin_email?.toLowerCase().includes(search.toLowerCase()) || l.resource_type?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div style={{ marginBottom:22 }}>
        <h1 style={{ fontSize:'1.4rem',fontWeight:800,marginBottom:4 }}>Audit Trail & Security</h1>
        <p style={{ color:'var(--text-muted)',fontSize:'0.85rem' }}>Immutable admin audit log · Security event monitoring</p>
      </div>

      {/* Tabs */}
      <div style={{ display:'flex',gap:4,marginBottom:18,background:'rgba(255,255,255,0.04)',borderRadius:10,padding:4,width:'fit-content' }}>
        {[{ key:'audit', label:'Audit Log', icon:Lock },{ key:'security', label:'Security Events', icon:Shield }].map(({ key, label, icon: Icon }) => (
          <button key={key} onClick={() => setTab(key)} style={{
            padding:'8px 18px', borderRadius:8, border:'none', cursor:'pointer', fontFamily:'var(--font-sans)',
            background: tab===key ? 'rgba(240,133,24,0.15)' : 'transparent',
            color: tab===key ? '#f08518' : 'var(--text-muted)',
            fontWeight: tab===key ? 600 : 400,
            display:'flex', alignItems:'center', gap:8, fontSize:'0.875rem'
          }}><Icon size={15} />{label}</button>
        ))}
      </div>

      {tab === 'audit' && (
        <div style={{ position:'relative',maxWidth:400,marginBottom:16 }}>
          <Search size={15} style={{ position:'absolute',left:12,top:'50%',transform:'translateY(-50%)',color:'var(--text-dim)',pointerEvents:'none' }} />
          <input className="input-field" placeholder="Filter by action, admin, resource..." style={{ paddingLeft:38 }}
                 value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      )}

      {loading ? (
        <div style={{ textAlign:'center',padding:60,color:'var(--text-muted)' }}><Lock size={28} style={{ opacity:0.4,marginBottom:10 }} /><div>Loading audit trail...</div></div>
      ) : tab === 'audit' ? (
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr><th>Time</th><th>Admin</th><th>Action</th><th>Resource</th><th>Details</th><th>IP</th></tr>
            </thead>
            <tbody>
              {filtered.map(l => (
                <tr key={l.id}>
                  <td style={{ fontFamily:'var(--font-mono)',fontSize:'0.75rem',color:'var(--text-dim)',whiteSpace:'nowrap' }}>
                    {l.created_at ? new Date(l.created_at).toLocaleString() : '—'}
                  </td>
                  <td style={{ fontSize:'0.83rem' }}>{l.admin_email || '—'}</td>
                  <td>
                    <span style={{
                      padding:'2px 8px', borderRadius:4, fontSize:'0.72rem', fontWeight:700, fontFamily:'var(--font-mono)',
                      background:`${ACTION_COLORS[l.action]||'#64748b'}20`,
                      color: ACTION_COLORS[l.action] || '#64748b'
                    }}>{l.action}</span>
                  </td>
                  <td style={{ fontSize:'0.8rem',color:'var(--text-muted)' }}>
                    {l.resource_type}{l.resource_id ? ` #${String(l.resource_id).slice(0,8)}` : ''}
                  </td>
                  <td style={{ maxWidth:240,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',fontSize:'0.78rem',color:'var(--text-dim)' }}>
                    {l.details ? JSON.stringify(l.details) : '—'}
                  </td>
                  <td style={{ fontFamily:'var(--font-mono)',fontSize:'0.75rem',color:'var(--text-dim)' }}>{l.ip_address || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ display:'flex',flexDirection:'column',gap:12 }}>
          {events.map(ev => (
            <div key={ev.id} className="glass-card" style={{
              padding:18,
              borderLeft: ev.risk_level === 'HIGH' || ev.risk_level === 'CRITICAL' ? '3px solid #ef4444' :
                         ev.risk_level === 'MEDIUM' ? '3px solid #f59e0b' : '3px solid #10b981'
            }}>
              <div style={{ display:'flex',justifyContent:'space-between',alignItems:'flex-start',gap:12 }}>
                <div style={{ flex:1 }}>
                  <div style={{ display:'flex',gap:10,alignItems:'center',marginBottom:6 }}>
                    <span style={{ fontWeight:700 }}>{ev.event_type}</span>
                    <RiskBadge level={ev.risk_level} />
                    {ev.is_resolved && <span className="badge badge-healthy" style={{ fontSize:'0.7rem' }}>Resolved</span>}
                  </div>
                  <div style={{ fontSize:'0.85rem',color:'var(--text-muted)',marginBottom:6 }}>{ev.description}</div>
                  <div style={{ display:'flex',gap:16,fontSize:'0.78rem',color:'var(--text-dim)',flexWrap:'wrap' }}>
                    <span>{ev.created_at ? new Date(ev.created_at).toLocaleString() : '—'}</span>
                    {ev.ip_address && <span>IP: {ev.ip_address}</span>}
                    {ev.user_email && <span>User: {ev.user_email}</span>}
                  </div>
                </div>
              </div>
              {ev.resolution_notes && (
                <div style={{ marginTop:10,fontSize:'0.78rem',color:'#34d399',borderTop:'1px solid var(--border-subtle)',paddingTop:8 }}>
                  ✓ {ev.resolution_notes}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
