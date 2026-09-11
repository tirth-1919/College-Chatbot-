import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { Globe, RefreshCw, CheckCircle, Clock, Hash } from 'lucide-react';

export default function WebsiteView() {
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState(null);

  const load = () => {
    setLoading(true);
    adminApi.getSnapshots().then(setSnapshots).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleSync = async () => {
    setSyncing(true); setSyncResult(null);
    try {
      const res = await adminApi.syncWebsite();
      setSyncResult(res);
      load();
    } catch (err) {
      setSyncResult({ error: err.message });
    } finally { setSyncing(false); }
  };

  return (
    <div>
      <div style={{ display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:22 }}>
        <div>
          <h1 style={{ fontSize:'1.4rem',fontWeight:800,marginBottom:4 }}>Website Synchronization</h1>
          <p style={{ color:'var(--text-muted)',fontSize:'0.85rem' }}>Automated aitindia.in crawler · Change detection · Hash comparison</p>
        </div>
        <button className="btn-primary" onClick={handleSync} disabled={syncing}>
          <RefreshCw size={15} style={{ animation: syncing ? 'spin 1s linear infinite' : 'none' }} />
          {syncing ? 'Syncing...' : 'Sync Now'}
        </button>
      </div>

      {syncResult && (
        <div className="glass-card" style={{
          padding:16, marginBottom:20,
          background: syncResult.error ? 'rgba(239,68,68,0.08)' : 'rgba(16,185,129,0.08)',
          border: `1px solid ${syncResult.error ? 'rgba(239,68,68,0.3)' : 'rgba(16,185,129,0.25)'}`
        }}>
          {syncResult.error ? (
            <span style={{ color:'#fca5a5' }}>Sync error: {syncResult.error}</span>
          ) : (
            <div style={{ display:'flex',gap:24,flexWrap:'wrap',fontSize:'0.875rem' }}>
              <span style={{ color:'#34d399',fontWeight:700 }}>✓ Sync complete</span>
              {[
                ['Total Pages', syncResult.details?.total_pages],
                ['New', syncResult.details?.new_pages],
                ['Updated', syncResult.details?.updated_pages],
                ['Unchanged', syncResult.details?.unchanged_pages],
                ['New Conflicts', syncResult.new_conflicts_detected],
              ].map(([l, v]) => (
                <span key={l} style={{ color:'var(--text-muted)' }}>{l}: <strong style={{ color:'#f8fafc' }}>{v ?? 0}</strong></span>
              ))}
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign:'center',padding:60,color:'var(--text-muted)' }}><Globe size={28} style={{ opacity:0.4,marginBottom:10 }} /><div>Loading snapshots...</div></div>
      ) : (
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr><th>URL</th><th>Title</th><th>Hash</th><th>Status</th><th>Last Crawled</th></tr>
            </thead>
            <tbody>
              {snapshots.map(s => (
                <tr key={s.id}>
                  <td>
                    <a href={s.url} target="_blank" rel="noopener noreferrer"
                       style={{ color:'#f08518',fontSize:'0.8rem',textDecoration:'none',wordBreak:'break-all' }}>
                      {s.url}
                    </a>
                  </td>
                  <td style={{ fontSize:'0.85rem',maxWidth:200,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap' }}>{s.title}</td>
                  <td>
                    <span style={{ fontFamily:'var(--font-mono)',fontSize:'0.72rem',color:'var(--text-dim)' }}>
                      {s.content_hash?.slice(0,12)}…
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${s.status_code === 200 ? 'badge-healthy' : 'badge-danger'}`} style={{ fontSize:'0.7rem' }}>
                      HTTP {s.status_code}
                    </span>
                  </td>
                  <td style={{ color:'var(--text-dim)',fontSize:'0.8rem' }}>
                    {s.last_crawled_at ? new Date(s.last_crawled_at).toLocaleString() : '—'}
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
