import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { GitMerge, MessageSquare, CheckCircle, TrendingUp, Star, ThumbsUp, ThumbsDown } from 'lucide-react';

export default function GapsView() {
  const [gaps, setGaps] = useState([]);
  const [feedback, setFeedback] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('gaps');

  useEffect(() => {
    setLoading(true);
    Promise.all([adminApi.getKnowledgeGaps(), adminApi.getFeedback()])
      .then(([g, f]) => { setGaps(g); setFeedback(f); })
      .finally(() => setLoading(false));
  }, []);

  const resolveGap = async (id) => {
    await adminApi.resolveGap(id);
    setGaps(g => g.map(x => x.id === id ? { ...x, status:'RESOLVED' } : x));
  };

  const unresolvedGaps = gaps.filter(g => g.status !== 'RESOLVED');
  const ratingCounts = feedback.reduce((acc, f) => { acc[f.rating] = (acc[f.rating]||0)+1; return acc; }, {});

  return (
    <div>
      <div style={{ display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:22 }}>
        <div>
          <h1 style={{ fontSize:'1.4rem',fontWeight:800,marginBottom:4 }}>Gaps & User Feedback</h1>
          <p style={{ color:'var(--text-muted)',fontSize:'0.85rem' }}>{unresolvedGaps.length} unresolved gaps · {feedback.length} feedback items</p>
        </div>
      </div>

      {/* Summary stats */}
      <div style={{ display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(160px,1fr))',gap:14,marginBottom:22 }}>
        {[
          { label:'Open Gaps', val:unresolvedGaps.length, color:'#ef4444', icon:GitMerge },
          { label:'Total Feedback', val:feedback.length, color:'#6366f1', icon:MessageSquare },
          { label:'Avg Rating', val: feedback.length ? (feedback.reduce((s,f)=>s+(f.rating||0),0)/feedback.length).toFixed(1) : '—', color:'#f59e0b', icon:Star },
          { label:'Positive', val:feedback.filter(f=>f.rating>=4).length, color:'#10b981', icon:ThumbsUp },
          { label:'Negative', val:feedback.filter(f=>f.rating<=2).length, color:'#ef4444', icon:ThumbsDown },
        ].map(({ label, val, color, icon: Icon }) => (
          <div key={label} className="glass-card" style={{ padding:'14px 18px' }}>
            <div style={{ display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:6 }}>
              <span style={{ fontSize:'0.7rem',color:'var(--text-dim)',fontWeight:600,textTransform:'uppercase' }}>{label}</span>
              <Icon size={14} color={color} />
            </div>
            <div style={{ fontSize:'1.7rem',fontWeight:800,color }}>{val}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ display:'flex',gap:4,marginBottom:18,background:'rgba(255,255,255,0.04)',borderRadius:10,padding:4,width:'fit-content' }}>
        {[{ key:'gaps', label:'Knowledge Gaps', icon:GitMerge },{ key:'feedback', label:'User Feedback', icon:MessageSquare }].map(({ key, label, icon: Icon }) => (
          <button key={key} onClick={() => setTab(key)} style={{
            padding:'8px 18px', borderRadius:8, border:'none', cursor:'pointer', fontFamily:'var(--font-sans)',
            background: tab===key ? 'rgba(240,133,24,0.15)' : 'transparent',
            color: tab===key ? '#f08518' : 'var(--text-muted)',
            fontWeight: tab===key ? 600 : 400,
            display:'flex', alignItems:'center', gap:8, fontSize:'0.875rem'
          }}><Icon size={15} />{label}</button>
        ))}
      </div>

      {loading ? (
        <div style={{ textAlign:'center',padding:60,color:'var(--text-muted)' }}><div>Loading...</div></div>
      ) : tab === 'gaps' ? (
        <div style={{ display:'flex',flexDirection:'column',gap:12 }}>
          {gaps.length === 0 ? (
            <div className="glass-card" style={{ padding:40,textAlign:'center' }}>
              <CheckCircle size={32} color="#10b981" style={{ marginBottom:12 }} />
              <div style={{ fontWeight:700 }}>No knowledge gaps detected</div>
            </div>
          ) : gaps.map(g => (
            <div key={g.id} className="glass-card" style={{
              padding:18,
              borderLeft: g.status === 'RESOLVED' ? '3px solid #10b981' : '3px solid #ef4444'
            }}>
              <div style={{ display:'flex',alignItems:'flex-start',justifyContent:'space-between',gap:12 }}>
                <div style={{ flex:1 }}>
                  <div style={{ fontWeight:700,marginBottom:4 }}>{g.question}</div>
                  {g.ai_response_summary && (
                    <div style={{ fontSize:'0.82rem',color:'var(--text-muted)',marginBottom:6 }}>
                      AI said: "{g.ai_response_summary}"
                    </div>
                  )}
                  <div style={{ display:'flex',gap:14,fontSize:'0.78rem',color:'var(--text-dim)',flexWrap:'wrap' }}>
                    <span>Frequency: {g.frequency}x</span>
                    {g.category && <span>Category: {g.category}</span>}
                    <span>{g.created_at ? new Date(g.created_at).toLocaleDateString() : '—'}</span>
                  </div>
                </div>
                <div style={{ display:'flex',gap:8,alignItems:'center',flexShrink:0 }}>
                  <span className={`badge ${g.status==='RESOLVED' ? 'badge-healthy' : g.frequency > 5 ? 'badge-danger' : 'badge-warning'}`}>
                    {g.status}
                  </span>
                  {g.status !== 'RESOLVED' && (
                    <button className="btn-secondary" style={{ padding:'5px 12px',fontSize:'0.78rem' }} onClick={() => resolveGap(g.id)}>
                      <CheckCircle size={13} /> Resolve
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr><th>Date</th><th>Rating</th><th>Message</th><th>Session</th></tr>
            </thead>
            <tbody>
              {feedback.map(f => (
                <tr key={f.id}>
                  <td style={{ color:'var(--text-dim)',fontSize:'0.8rem' }}>{f.created_at ? new Date(f.created_at).toLocaleDateString() : '—'}</td>
                  <td>
                    <div style={{ display:'flex',gap:2 }}>
                      {[1,2,3,4,5].map(n => (
                        <Star key={n} size={13} fill={n <= (f.rating||0) ? '#f59e0b' : 'none'} color="#f59e0b" />
                      ))}
                    </div>
                  </td>
                  <td style={{ maxWidth:320,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',fontSize:'0.85rem',color:'var(--text-muted)' }}>
                    {f.message || <span style={{ color:'var(--text-dim)' }}>—</span>}
                  </td>
                  <td style={{ fontFamily:'var(--font-mono)',fontSize:'0.72rem',color:'var(--text-dim)' }}>
                    {f.conversation_id?.slice(0,8)}…
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
