import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { AlertTriangle, Scan, CheckCircle, XCircle } from 'lucide-react';

const STATUSES = ['ALL','UNRESOLVED','RESOLVED_A','RESOLVED_B','SUPERSEDED','DISMISSED'];

function DiffBlock({ labelA, valueA, labelB, valueB }) {
  return (
    <div style={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:10,marginTop:10 }}>
      {[[labelA, valueA, '#6366f1'], [labelB, valueB, '#f08518']].map(([label, val, color]) => (
        <div key={label} style={{ background:'rgba(255,255,255,0.03)',border:`1px solid rgba(${color==='#6366f1'?'99,102,241':'240,133,24'},0.25)`,borderRadius:8,padding:'10px 14px' }}>
          <div style={{ fontSize:'0.7rem',fontWeight:700,color,marginBottom:6,textTransform:'uppercase' }}>{label}</div>
          <div style={{ fontSize:'0.85rem',color:'var(--text-main)' }}>{val}</div>
        </div>
      ))}
    </div>
  );
}

export default function ConflictsView() {
  const [conflicts, setConflicts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [scanning, setScanning] = useState(false);
  const [expanded, setExpanded] = useState(null);

  const load = () => {
    setLoading(true);
    const params = statusFilter !== 'ALL' ? { status_filter: statusFilter } : {};
    adminApi.getConflicts(params).then(setConflicts).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [statusFilter]);

  const handleScan = async () => {
    setScanning(true);
    await adminApi.scanConflicts();
    load();
    setScanning(false);
  };

  const handleResolve = async (id, resolution) => {
    const notes = prompt('Resolution notes (optional):') || '';
    await adminApi.resolveConflict(id, { resolution_status: resolution, resolution_notes: notes });
    load();
  };

  return (
    <div>
      <div style={{ display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:22 }}>
        <div>
          <h1 style={{ fontSize:'1.4rem',fontWeight:800,marginBottom:4 }}>Knowledge Conflicts</h1>
          <p style={{ color:'var(--text-muted)',fontSize:'0.85rem' }}>Source discrepancies between website, database, and documents</p>
        </div>
        <div style={{ display:'flex',gap:10 }}>
          <select className="input-field" style={{ width:180 }} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <button className="btn-secondary" onClick={handleScan} disabled={scanning}>
            <Scan size={15} /> {scanning ? 'Scanning...' : 'Scan Now'}
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign:'center',padding:60,color:'var(--text-muted)' }}>
          <AlertTriangle size={28} style={{ opacity:0.4,marginBottom:10 }} /><div>Loading conflicts...</div>
        </div>
      ) : conflicts.length === 0 ? (
        <div className="glass-card" style={{ padding:40,textAlign:'center' }}>
          <CheckCircle size={32} color="#10b981" style={{ marginBottom:12 }} />
          <div style={{ fontWeight:700,marginBottom:6 }}>No conflicts found</div>
          <div style={{ color:'var(--text-muted)',fontSize:'0.875rem' }}>Run a scan to check for new discrepancies</div>
        </div>
      ) : (
        <div style={{ display:'flex',flexDirection:'column',gap:14 }}>
          {conflicts.map(c => (
            <div key={c.id} className="glass-card" style={{
              padding:20,
              borderLeft: c.resolution_status === 'UNRESOLVED' ? '3px solid #ef4444' : '3px solid #10b981'
            }}>
              <div style={{ display:'flex',alignItems:'flex-start',justifyContent:'space-between',gap:12,marginBottom:10 }}>
                <div style={{ flex:1 }}>
                  <div style={{ fontWeight:700,fontSize:'1rem',marginBottom:4 }}>{c.topic}</div>
                  <div style={{ fontSize:'0.8rem',color:'var(--text-dim)' }}>
                    Detected: {c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}
                    {c.resolved_at && ` · Resolved: ${new Date(c.resolved_at).toLocaleDateString()}`}
                  </div>
                </div>
                <span className={`badge ${c.resolution_status === 'UNRESOLVED' ? 'badge-danger' : 'badge-healthy'}`}>
                  {c.resolution_status}
                </span>
              </div>

              <div style={{ fontSize:'0.875rem',color:'var(--text-muted)',marginBottom:8 }}>
                <strong>Discrepancy:</strong> {c.discrepancy}
              </div>

              <button
                onClick={() => setExpanded(expanded === c.id ? null : c.id)}
                style={{ background:'none',border:'none',color:'#f08518',cursor:'pointer',fontSize:'0.8rem',padding:'4px 0',fontFamily:'var(--font-sans)' }}
              >
                {expanded === c.id ? '▲ Hide details' : '▼ Show source comparison'}
              </button>

              {expanded === c.id && (
                <DiffBlock
                  labelA={c.source_a}
                  valueA={c.value_a}
                  labelB={c.source_b}
                  valueB={c.value_b}
                />
              )}

              {c.resolution_status === 'UNRESOLVED' && (
                <div style={{ display:'flex',gap:8,marginTop:14,flexWrap:'wrap' }}>
                  {[
                    { label:'Accept Source A', val:'RESOLVED_A', color:'#6366f1' },
                    { label:'Accept Source B', val:'RESOLVED_B', color:'#f08518' },
                    { label:'Mark Superseded', val:'SUPERSEDED', color:'#10b981' },
                    { label:'Dismiss', val:'DISMISSED', color:'#64748b' },
                  ].map(({ label, val, color }) => (
                    <button key={val} onClick={() => handleResolve(c.id, val)} style={{
                      padding:'6px 14px', borderRadius:6, border:`1px solid ${color}40`, cursor:'pointer',
                      background:`${color}18`, color, fontSize:'0.8rem', fontWeight:600, fontFamily:'var(--font-sans)'
                    }}>{label}</button>
                  ))}
                </div>
              )}

              {c.resolution_notes && (
                <div style={{ marginTop:10,fontSize:'0.78rem',color:'var(--text-dim)',borderTop:'1px solid var(--border-subtle)',paddingTop:8 }}>
                  Resolution notes: {c.resolution_notes}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
