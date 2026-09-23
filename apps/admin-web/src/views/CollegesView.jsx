import { useState, useEffect, useCallback } from 'react';
import { adminApi } from '../services/adminApi';
import {
  Building2, Globe, CheckCircle, XCircle, Clock, Search, RefreshCw,
  Eye, Ban, PlayCircle, Users, ExternalLink,
} from 'lucide-react';

/**
 * SUPER_ADMIN "All Colleges" page (§15-§17, §31, §35).
 * Fully database-driven: no college names/codes are hard-coded here.
 */
export default function CollegesView() {
  const [colleges, setColleges] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [details, setDetails] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [notice, setNotice] = useState('');
  const [confirmAction, setConfirmAction] = useState(null); // { college, action }

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [list, s] = await Promise.all([
        adminApi.listColleges(),
        adminApi.getCollegeStats().catch(() => null),
      ]);
      setColleges(list || []);
      setStats(s);
    } catch (err) {
      setError(err.message || 'Failed to fetch colleges');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const changeStatus = async (college, status) => {
    setActionLoading(true);
    try {
      await adminApi.updateCollege(college.id, { status });
      setNotice(`${college.name} set to ${status}.`);
      setTimeout(() => setNotice(''), 4000);
      fetchAll();
    } catch (err) {
      alert('Status update failed: ' + err.message);
    } finally {
      setActionLoading(false);
      setConfirmAction(null);
    }
  };

  // §6/§25: navigate to the dedicated details page using the database ID.
  const openDetails = (college) => {
    window.history.pushState({}, '', `/super-admin/colleges/${college.id}`);
    window.dispatchEvent(new PopStateEvent('popstate'));
  };

  const filtered = colleges.filter(c => {
    if (filter !== 'ALL' && (c.status || '').toUpperCase() !== filter) return false;
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      c.name?.toLowerCase().includes(q) ||
      c.code?.toLowerCase().includes(q) ||
      c.slug?.toLowerCase().includes(q) ||
      c.official_website?.toLowerCase().includes(q) ||
      c.city?.toLowerCase().includes(q)
    );
  });

  const statusBadge = (status) => {
    const s = (status || '').toUpperCase();
    const map = {
      ACTIVE: { color: '#34d399', icon: CheckCircle, label: 'ACTIVE' },
      PENDING: { color: '#f08518', icon: Clock, label: 'PENDING' },
      SUSPENDED: { color: '#f87171', icon: Ban, label: 'SUSPENDED' },
      REJECTED: { color: '#f87171', icon: XCircle, label: 'REJECTED' },
    };
    const cfg = map[s] || { color: '#818cf8', icon: Clock, label: s || 'UNKNOWN' };
    const Icon = cfg.icon;
    return (
      <span className="badge" style={{
        background: `${cfg.color}22`, color: cfg.color,
        border: `1px solid ${cfg.color}55`, display: 'inline-flex', alignItems: 'center', gap: 5,
      }}>
        <Icon size={12} /> {cfg.label}
      </span>
    );
  };

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 14 }}>
        <div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#fff' }}>All Colleges</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Every college tenant on the platform — list is loaded dynamically from the database
          </p>
        </div>
        <button className="btn-secondary" onClick={fetchAll} disabled={loading} style={{ gap: 8 }}>
          <RefreshCw size={15} className={loading ? 'spin' : ''} /> Refresh
        </button>
      </div>

      {notice && (
        <div style={{ background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: 8, padding: '12px 16px', marginBottom: 20, color: '#34d399', fontSize: '0.875rem' }}>
          {notice}
        </div>
      )}

      {/* Stats summary (§16/§34) — counts come from the API, not the UI */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 14, marginBottom: 24 }}>
          {Object.entries(stats).map(([k, v]) => (
            <div key={k} className="glass-card" style={{ padding: '14px 18px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase' }}>{k}</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: k === 'ACTIVE' ? '#34d399' : k === 'TOTAL' ? '#f08518' : '#e2e8f0' }}>{v}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filters + search (§31/§35) */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {['ALL', 'ACTIVE', 'PENDING', 'SUSPENDED', 'REJECTED'].map(t => (
            <button key={t} onClick={() => setFilter(t)}
              className={filter === t ? 'btn-primary' : 'btn-secondary'}
              style={{ padding: '6px 14px', fontSize: '0.8rem', borderRadius: 20 }}>
              {t === 'ALL' ? 'All Colleges' : t}
            </button>
          ))}
        </div>
        <div style={{ position: 'relative', width: 280 }}>
          <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
          <input className="input-field" placeholder="Search colleges..." value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)} style={{ paddingLeft: 34, fontSize: '0.82rem' }} />
        </div>
      </div>

      {error && <div className="glass-card" style={{ padding: 20, color: '#f871' }}>{error}</div>}

      {/* College list (§15) */}
      {loading ? (
        <div style={{ padding: '48px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
          <RefreshCw size={28} className="spin" style={{ margin: '0 auto 12px', opacity: 0.6 }} />
          <div>Loading colleges...</div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="glass-card" style={{ padding: '48px 24px', textAlign: 'center' }}>
          <Building2 size={40} style={{ margin: '0 auto 16px', opacity: 0.3, color: 'var(--text-dim)' }} />
          <h3 style={{ fontWeight: 600, marginBottom: 6 }}>No Colleges Found</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            {searchQuery ? 'No results matched your search.' : 'No colleges registered yet.'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {filtered.map((c, i) => (
            <div key={c.id} className="glass-card" style={{
              padding: '18px 22px',
              borderLeft: `4px solid ${c.status === 'ACTIVE' ? '#10b981' : c.status === 'PENDING' ? '#f08518' : '#ef4444'}`,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                    <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem', fontWeight: 700 }}>{i + 1}.</span>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>{c.name}</h3>
                    <span style={{
                      background: 'rgba(240,133,24,0.12)', border: '1px solid rgba(240,133,24,0.3)',
                      color: '#f08518', borderRadius: 4, padding: '2px 8px', fontSize: '0.75rem', fontWeight: 700,
                    }}>{c.code}</span>
                    {statusBadge(c.status)}
                  </div>
                  <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {c.city && <span>{c.city}, {c.state || ''} {c.country || ''}</span>}
                    {c.created_at && <span>Created: {new Date(c.created_at).toLocaleDateString()}</span>}
                    {c.official_website && (
                      <a href={c.official_website} target="_blank" rel="noreferrer"
                        style={{ color: '#f08518', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                        <Globe size={12} /> {c.official_website}
                      </a>
                    )}
                    {c.university_affiliation && <span>Affiliation: {c.university_affiliation}</span>}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                  <button className="btn-secondary" onClick={() => openDetails(c)} style={{ fontSize: '0.78rem', padding: '6px 12px', gap: 6 }}>
                    <Eye size={13} /> View Details
                  </button>
                  {c.status === 'ACTIVE' ? (
                    <button className="btn-secondary" disabled={actionLoading}
                      onClick={() => setConfirmAction({ college: c, action: 'SUSPENDED' })}
                      style={{ fontSize: '0.78rem', padding: '6px 12px', gap: 6, color: '#f871', borderColor: 'rgba(239,68,68,0.3)' }}>
                      <Ban size={13} /> Suspend
                    </button>
                  ) : (
                    <button className="btn-secondary" disabled={actionLoading}
                      onClick={() => setConfirmAction({ college: c, action: 'ACTIVE' })}
                      style={{ fontSize: '0.78rem', padding: '6px 12px', gap: 6, color: '#34d399', borderColor: 'rgba(16,185,129,0.3)' }}>
                      <PlayCircle size={13} /> Reactivate
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Suspend / Reactivate confirmation dialog (§23/§24) */}
      {confirmAction && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 20 }}
          onClick={() => setConfirmAction(null)}>
          <div className="glass-card" style={{ width: '100%', maxWidth: 460, padding: 26 }} onClick={e => e.stopPropagation()}>
            <h3 style={{ fontWeight: 800, color: '#fff', marginBottom: 10 }}>
              {confirmAction.action === 'SUSPENDED' ? 'Suspend' : 'Reactivate'} {confirmAction.college.name}?
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 18 }}>
              {confirmAction.action === 'SUSPENDED'
                ? 'This will prevent normal college access according to the existing suspension policy.'
                : 'The college will regain normal platform access.'}
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button className="btn-secondary" onClick={() => setConfirmAction(null)}>Cancel</button>
              <button className="btn-primary" disabled={actionLoading}
                onClick={() => changeStatus(confirmAction.college, confirmAction.action)}>
                {confirmAction.action === 'SUSPENDED' ? 'Suspend' : 'Reactivate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
