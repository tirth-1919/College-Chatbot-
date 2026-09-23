import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { useAdminAuth } from '../context/AdminAuthContext';
import {
  GitMerge, CheckCircle, XCircle, Clock, RefreshCw, AlertCircle,
  Check, X, Plus, FileText
} from 'lucide-react';

const ENTITY_TYPES = ['FEES', 'FACULTY', 'COURSES', 'DEPARTMENT', 'CALENDAR', 'EVENT', 'KNOWLEDGE'];

export default function ChangeRequestsView() {
  const { user } = useAdminAuth();
  const isSuperAdmin = user?.role === 'SUPER_ADMIN';

  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('ALL');
  const [showCreate, setShowCreate] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [reviewNotes, setReviewNotes] = useState({});
  const [successMsg, setSuccessMsg] = useState('');

  // Create form
  const [form, setForm] = useState({
    entity_type: 'FEES', action: 'UPDATE',
    entity_id: '', reason: '',
    new_value_json: '{\n  "key": "value"\n}',
  });

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await adminApi.listChangeRequests(filter);
      setRequests(data || []);
    } catch (err) {
      setError(err.message || 'Failed to load change requests');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filter]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError('');
    let new_value;
    try {
      new_value = form.new_value_json.trim() ? JSON.parse(form.new_value_json) : null;
    } catch {
      setError('New value must be valid JSON');
      return;
    }
    try {
      await adminApi.createChangeRequest({
        entity_type: form.entity_type,
        action: form.action,
        entity_id: form.entity_id || null,
        reason: form.reason || null,
        new_value,
      });
      setShowCreate(false);
      setSuccessMsg('Change request submitted for Super Admin approval.');
      setTimeout(() => setSuccessMsg(''), 4000);
      load();
    } catch (err) {
      setError(err.message || 'Failed to create change request');
    }
  };

  const review = async (id, decision) => {
    setActionLoadingId(id);
    setError('');
    try {
      await (decision === 'approve'
        ? adminApi.approveChangeRequest(id, reviewNotes[id] || null)
        : adminApi.rejectChangeRequest(id, reviewNotes[id] || null));
      setSuccessMsg(`Change request ${decision}d.`);
      setTimeout(() => setSuccessMsg(''), 4000);
      load();
    } catch (err) {
      setError(err.message || `Failed to ${decision} change request`);
    } finally {
      setActionLoadingId(null);
    }
  };

  const statusBadge = (s) => {
    const map = {
      PENDING: { bg: 'rgba(240,133,24,0.15)', color: '#f08518', Icon: Clock },
      APPROVED: { bg: 'rgba(16,185,129,0.15)', color: '#34d399', Icon: CheckCircle },
      REJECTED: { bg: 'rgba(239,68,68,0.15)', color: '#f87171', Icon: XCircle },
    };
    const m = map[s] || { bg: 'rgba(255,255,255,0.06)', color: '#9ca3af', Icon: Clock };
    return (
      <span className="badge" style={{ background: m.bg, color: m.color, display: 'inline-flex', alignItems: 'center', gap: 5 }}>
        <m.Icon size={12} /> {s}
      </span>
    );
  };

  const pendingCount = requests.filter(r => r.status === 'PENDING').length;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#fff' }}>Change Requests</h1>
            {pendingCount > 0 && (
              <span style={{ background: '#ef4444', color: '#fff', fontSize: '0.75rem', fontWeight: 700, padding: '2px 8px', borderRadius: 9999 }}>
                {pendingCount} Pending
              </span>
            )}
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            {isSuperAdmin
              ? 'Review college admin requests. Approved changes are applied to production data.'
              : 'Protected data changes require Super Admin approval before they update production.'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {!isSuperAdmin && (
            <button className="btn-primary" onClick={() => setShowCreate(v => !v)} style={{ gap: 8 }}>
              <Plus size={15} /> New Change Request
            </button>
          )}
          <button className="btn-secondary" onClick={load} disabled={loading} style={{ gap: 8 }}>
            <RefreshCw size={15} className={loading ? 'spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {successMsg && (
        <div style={{ background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: 8, padding: '12px 16px', marginBottom: 20, color: '#34d399', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: 8 }}>
          <CheckCircle size={16} /> <span>{successMsg}</span>
        </div>
      )}
      {error && (
        <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8, padding: '12px 16px', marginBottom: 20, color: '#fca5a5', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: 8 }}>
          <AlertCircle size={16} /> <span>{error}</span>
        </div>
      )}

      {/* Create form (College Admin only) */}
      {showCreate && (
        <div className="glass-card" style={{ padding: 24, marginBottom: 24 }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f08518', marginBottom: 16 }}>New Change Request</h3>
          <form onSubmit={handleCreate} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 6 }}>Entity Type *</label>
              <select className="input-field" value={form.entity_type}
                onChange={e => setForm({ ...form, entity_type: e.target.value })}>
                {ENTITY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 6 }}>Action *</label>
              <select className="input-field" value={form.action}
                onChange={e => setForm({ ...form, action: e.target.value })}>
                <option value="CREATE">CREATE</option>
                <option value="UPDATE">UPDATE</option>
                <option value="DELETE">DELETE</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 6 }}>Entity ID (for UPDATE / DELETE)</label>
              <input className="input-field" value={form.entity_id}
                onChange={e => setForm({ ...form, entity_id: e.target.value })}
                placeholder="Existing record ID" />
            </div>
            <div style={{ gridColumn: 'span 3' }}>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 6 }}>Proposed New Value (JSON)</label>
              <textarea className="input-field" rows={4} style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}
                value={form.new_value_json}
                onChange={e => setForm({ ...form, new_value_json: e.target.value })} />
            </div>
            <div style={{ gridColumn: 'span 3' }}>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 6 }}>Reason for Change</label>
              <input className="input-field" value={form.reason}
                onChange={e => setForm({ ...form, reason: e.target.value })}
                placeholder="e.g. BCA fee revised for academic year 2026-27" />
            </div>
            <div style={{ gridColumn: 'span 3', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button type="button" className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
              <button type="submit" className="btn-primary">Submit Request</button>
            </div>
          </form>
        </div>
      )}

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {['ALL', 'PENDING', 'APPROVED', 'REJECTED'].map(t => (
          <button key={t} onClick={() => setFilter(t)}
            className={filter === t ? 'btn-primary' : 'btn-secondary'}
            style={{ padding: '6px 14px', fontSize: '0.8rem', borderRadius: 20 }}>
            {t}
          </button>
        ))}
      </div>

      {/* List */}
      {loading ? (
        <div style={{ padding: '48px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
          <RefreshCw size={28} className="spin" style={{ margin: '0 auto 12px', opacity: 0.6 }} />
          <div>Loading change requests...</div>
        </div>
      ) : requests.length === 0 ? (
        <div className="glass-card" style={{ padding: '48px 24px', textAlign: 'center' }}>
          <GitMerge size={40} style={{ margin: '0 auto 16px', opacity: 0.3, color: 'var(--text-dim)' }} />
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 6 }}>No Change Requests</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            No change requests found in this category.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {requests.map(cr => (
            <div key={cr.id} className="glass-card" style={{
              padding: '18px 22px',
              borderLeft: `4px solid ${cr.status === 'PENDING' ? '#f08518' : cr.status === 'APPROVED' ? '#10b981' : '#ef4444'}`
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                    <FileText size={16} color="#f08518" />
                    <strong style={{ color: '#fff', fontSize: '0.95rem' }}>{cr.action} · {cr.entity_type}</strong>
                    {isSuperAdmin && cr.college_name && (
                      <span className="badge" style={{ fontSize: '0.72rem' }}>{cr.college_name}</span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Requested: {cr.created_at ? new Date(cr.created_at).toLocaleString() : '—'}
                  </div>
                </div>
                {statusBadge(cr.status)}
              </div>

              {cr.reason && (
                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: 10 }}>
                  <strong style={{ color: 'var(--text-dim)' }}>Reason:</strong> {cr.reason}
                </div>
              )}
              {cr.new_value && (
                <pre style={{
                  marginTop: 10, padding: 12, background: 'rgba(0,0,0,0.3)', borderRadius: 6,
                  fontSize: '0.75rem', overflowX: 'auto', color: '#9ca3af', fontFamily: 'var(--font-mono)'
                }}>
                  {JSON.stringify(cr.new_value, null, 2)}
                </pre>
              )}
              {cr.review_notes && (
                <div style={{
                  marginTop: 10, fontSize: '0.8rem', padding: '8px 12px', borderRadius: 6,
                  background: cr.status === 'REJECTED' ? 'rgba(239,68,68,0.08)' : 'rgba(16,185,129,0.08)',
                  color: cr.status === 'REJECTED' ? '#fca5a5' : '#34d399'
                }}>
                  <strong>Review Notes:</strong> {cr.review_notes}
                </div>
              )}

              {isSuperAdmin && cr.status === 'PENDING' && (
                <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--border-subtle)' }}>
                  <input
                    className="input-field"
                    placeholder="Review notes (optional)"
                    value={reviewNotes[cr.id] || ''}
                    onChange={e => setReviewNotes({ ...reviewNotes, [cr.id]: e.target.value })}
                    style={{ fontSize: '0.82rem', marginBottom: 10 }}
                  />
                  <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                    <button className="btn-secondary" disabled={actionLoadingId === cr.id}
                      onClick={() => review(cr.id, 'reject')}
                      style={{ gap: 6, color: '#ef4444', borderColor: 'rgba(239,68,68,0.3)', fontSize: '0.8rem', padding: '6px 14px' }}>
                      <X size={14} /> Reject
                    </button>
                    <button className="btn-primary" disabled={actionLoadingId === cr.id}
                      onClick={() => review(cr.id, 'approve')}
                      style={{ gap: 6, fontSize: '0.8rem', padding: '6px 14px' }}>
                      <Check size={14} /> Approve & Apply
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
