import { useEffect, useState } from 'react';
import { adminApi } from '../services/adminApi';

const card = { background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: 10, padding: 16 };
export default function LearningView() {
  const [summary, setSummary] = useState(null); const [data, setData] = useState({ items: [], total: 0 });
  const [status, setStatus] = useState('ALL'); const [search, setSearch] = useState(''); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const load = () => Promise.all([adminApi.getLearningSummary(), adminApi.getLearningCandidates({ status, search, page: 1, per_page: 50, sort: 'priority' })]).then(([s, d]) => { setSummary(s); setData(d); }).catch(e => setError(e.message));
  useEffect(load, [status]);
  const review = async (candidate, action) => {
    setBusy(true); setError(''); try { if (action === 'approve') await adminApi.approveLearningCandidate(candidate.id); else await adminApi.rejectLearningCandidate(candidate.id, window.prompt('Rejection reason (required):') || ''); await load(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  return <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 22 }}><div><h1 style={{ color: '#fff' }}>Learning Dashboard</h1><p style={{ color: 'var(--text-muted)' }}>Review captured questions without bypassing institutional approval.</p></div><button className="btn-secondary" onClick={load}>Refresh</button></div>
      {error && <div style={{ ...card, color: '#fca5a5', marginBottom: 16 }}>{error}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 12, marginBottom: 22 }}>{[['Total', 'total'], ['Pending', 'pending'], ['Approved', 'approved'], ['Rejected', 'rejected'], ['Duplicates', 'duplicates'], ['Negative feedback', 'negative_feedback']].map(([label, key]) => <div key={key} style={card}><div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{label}</div><strong style={{ fontSize: 24, color: '#f08518' }}>{summary?.[key] ?? '—'}</strong></div>)}</div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}><input className="input-field" placeholder="Search questions or answers" value={search} onChange={e => setSearch(e.target.value)} onKeyDown={e => e.key === 'Enter' && load()} /><select className="input-field" value={status} onChange={e => setStatus(e.target.value)}><option>ALL</option><option>PENDING_REVIEW</option><option>APPROVED</option><option>REJECTED</option><option>DUPLICATE</option><option>MERGED</option></select></div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>{data.items.map(c => <div key={c.id} style={{ ...card, borderLeft: `3px solid ${c.priority?.priority === 'HIGH' ? '#f08518' : '#64748b'}` }}><div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><strong style={{ color: '#fff' }}>{c.question}</strong><span className="badge">{c.status}</span></div><p style={{ color: 'var(--text-muted)', fontSize: 13 }}>{c.generated_answer || 'No generated answer'} </p><div style={{ fontSize: 12, color: 'var(--text-dim)' }}>Occurrences: {c.occurrence_count} · {c.answer_source || 'unknown'} · {c.priority?.reason}</div>{c.status === 'PENDING_REVIEW' && <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}><button disabled={busy} className="btn-secondary" onClick={() => review(c, 'reject')}>Reject</button><button disabled={busy} className="btn-primary" onClick={() => review(c, 'approve')}>Approve for ChangeRequest</button></div>}</div>)}</div>
    </div>;
}         
