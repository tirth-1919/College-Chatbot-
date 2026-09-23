import { useState, useEffect, useCallback } from 'react';
import { adminApi } from '../services/adminApi';
import {
  Building2, Globe, RefreshCw, Eye, Ban, PlayCircle, Users, BookOpen,
  FileText, GitMerge, MessageSquare, TrendingUp, Lock, Settings,
  CheckCircle, XCircle, Clock, ExternalLink, AlertTriangle, ArrowLeft, Search,
} from 'lucide-react';

/**
 * Reusable SUPER_ADMIN College Details page (§9-§21, §31, §33).
 *
 * ONE dynamic view for every college — AIT, RCTI, College C, ... The college is
 * always loaded from the backend using the database ID from the URL (§25/§27).
 * No college names, codes or conditionals are hard-coded here (§32/§33).
 */

const TABS = [
  { key: 'overview', label: 'College Overview' },
  { key: 'users', label: 'Admin & Users' },
  { key: 'knowledge', label: 'Knowledge' },
  { key: 'documents', label: 'Documents' },
  { key: 'website', label: 'Website' },
  { key: 'rag', label: 'RAG' },
  { key: 'change_requests', label: 'Change Requests' },
  { key: 'feedback', label: 'Feedback' },
  { key: 'gaps', label: 'Knowledge Gaps' },
  { key: 'analytics', label: 'Analytics' },
  { key: 'audit', label: 'Audit History' },
  { key: 'settings', label: 'Settings' },
];

function statusBadge(status) {
  const s = (status || '').toUpperCase();
  const color = s === 'ACTIVE' ? '#34d399' : s === 'PENDING' ? '#f08518' : '#f87171';
  const Icon = s === 'ACTIVE' ? CheckCircle : s === 'PENDING' ? Clock : Ban;
  return (
    <span className="badge" style={{
      background: `${color}22`, color, border: `1px solid ${color}55`,
      display: 'inline-flex', alignItems: 'center', gap: 5,
    }}>
      <Icon size={12} /> {s || 'UNKNOWN'}
    </span>
  );
}

function Field({ label, value, link }) {
  return (
    <div>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 2 }}>{label}</div>
      {value ? (
        link
          ? <a href={value} target="_blank" rel="noreferrer" style={{ color: '#f08518', fontSize: '0.85rem', display: 'inline-flex', gap: 4, alignItems: 'center' }}>{value} <ExternalLink size={11} /></a>
          : <div style={{ fontSize: '0.85rem', color: '#e2e8f0' }}>{value}</div>
      ) : <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>N/A</div>}
    </div>
  );
}

function EmptyState({ message }) {
  return (
    <div className="glass-card" style={{ padding: '32px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
      {message}
    </div>
  );
}

export default function CollegeDetailsView({ collegeId, onNavChange }) {
  const [college, setCollege] = useState(null);
  const [stats, setStats] = useState(null);
  const [tabData, setTabData] = useState({});
  const [tab, setTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [tabLoading, setTabLoading] = useState(false);
  const [error, setError] = useState('');
  const [notFound, setNotFound] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [notice, setNotice] = useState('');
  const [confirmAction, setConfirmAction] = useState(null);

  const backToColleges = () => {
    window.history.pushState({}, '', '/super-admin/colleges');
    window.dispatchEvent(new PopStateEvent('popstate'));
  };

  const fetchCore = useCallback(async () => {
    setLoading(true);
    setError('');
    setNotFound(false);
    try {
      const [c, s] = await Promise.all([
        adminApi.getCollege(collegeId),
        adminApi.getCollegeStatsFor(collegeId).catch(() => null),
      ]);
      setCollege(c);
      setStats(s);
    } catch (err) {
      if (String(err.message).includes('College not found') || String(err.message).includes('404')) {
        setNotFound(true);
      } else {
        setError(err.message || 'Unable to load college details.');
      }
    } finally {
      setLoading(false);
    }
  }, [collegeId]);

  useEffect(() => { fetchCore(); }, [fetchCore]);

  // Lazily fetch tab data only when the tab is opened (§40)
  const TAB_FETCHERS = {
    users: adminApi.getCollegeUsers,
    knowledge: adminApi.getCollegeKnowledge,
    documents: adminApi.getCollegeDocuments,
    website: adminApi.getCollegeWebsite,
    rag: adminApi.getCollegeRag,
    change_requests: adminApi.getCollegeChangeRequests,
    feedback: adminApi.getCollegeFeedback,
    gaps: adminApi.getCollegeGaps,
    analytics: adminApi.getCollegeAnalytics,
    audit: adminApi.getCollegeAudit,
  };

  useEffect(() => {
    const fetcher = TAB_FETCHERS[tab];
    if (!fetcher || tabData[tab]) return;
    let cancelled = false;
    setTabLoading(true);
    fetcher.call(adminApi, collegeId)
      .then(data => { if (!cancelled) setTabData(prev => ({ ...prev, [tab]: data })); })
      .catch(() => { if (!cancelled) setTabData(prev => ({ ...prev, [tab]: { error: true } })); })
      .finally(() => { if (!cancelled) setTabLoading(false); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, collegeId]);

  const doAction = async (college, newStatus) => {
    setActionLoading(true);
    try {
      await adminApi.updateCollege(college.id, { status: newStatus });
      setNotice(`${college.name} set to ${newStatus}.`);
      setTimeout(() => setNotice(''), 4000);
      fetchCore();
    } catch (err) {
      alert('Status update failed: ' + err.message);
    } finally {
      setActionLoading(false);
      setConfirmAction(null);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '64px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
        <RefreshCw size={28} className="spin" style={{ margin: '0 auto 12px', opacity: 0.6 }} />
        <div>Loading college details...</div>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="glass-card" style={{ padding: '48px 24px', textAlign: 'center' }}>
        <AlertTriangle size={40} style={{ margin: '0 auto 16px', opacity: 0.4, color: '#f87171' }} />
        <h2 style={{ fontWeight: 700, marginBottom: 8 }}>College not found</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 20 }}>
          The requested college does not exist.
        </p>
        <button className="btn-primary" onClick={backToColleges}>← Back to Colleges</button>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card" style={{ padding: '48px 24px', textAlign: 'center' }}>
        <AlertTriangle size={40} style={{ margin: '0 auto 16px', opacity: 0.4, color: '#f87171' }} />
        <h2 style={{ fontWeight: 700, marginBottom: 8 }}>Unable to load college details.</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 20 }}>{error}</p>
        <button className="btn-primary" onClick={fetchCore}>Retry</button>
      </div>
    );
  }

  const statCards = stats ? [
    { label: 'Users', value: stats.users, icon: Users },
    { label: 'Admins', value: stats.admins, icon: Users },
    { label: 'Knowledge Records', value: stats.knowledge, icon: BookOpen },
    { label: 'Documents', value: stats.documents, icon: FileText },
    { label: 'RAG Chunks', value: stats.rag_chunks, icon: FileText },
    { label: 'Pending Changes', value: stats.pending_changes, icon: GitMerge },
    { label: 'Knowledge Gaps', value: stats.knowledge_gaps, icon: AlertTriangle },
    { label: 'Feedback Reports', value: stats.feedback_reports, icon: MessageSquare },
  ] : [];

  const td = tabData[tab] || {};

  return (
    <div>
      {/* Back button (§26) */}
      <button className="btn-secondary" onClick={backToColleges}
        style={{ fontSize: '0.8rem', padding: '6px 14px', gap: 6, marginBottom: 18 }}>
        <ArrowLeft size={14} /> Back to Colleges
      </button>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap', marginBottom: 22 }}>
        <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
          {college.logo_url
            ? <img src={college.logo_url} alt={college.name} style={{ width: 52, height: 52, borderRadius: 12, objectFit: 'cover' }} />
            : <div style={{ width: 52, height: 52, borderRadius: 12, background: 'linear-gradient(135deg, #0b0a3e, #1a2345)', border: '1px solid rgba(240,133,24,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Building2 size={24} color="#f08518" />
            </div>}
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#fff' }}>{college.name}</h1>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 4, flexWrap: 'wrap' }}>
              <span style={{ background: 'rgba(240,133,24,0.12)', border: '1px solid rgba(240,133,24,0.3)', color: '#f08518', borderRadius: 4, padding: '2px 8px', fontSize: '0.75rem', fontWeight: 700 }}>Code: {college.code}</span>
              {statusBadge(college.status)}
              <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>Slug: {college.slug}</span>
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {college.official_website && (
            <a href={college.official_website} target="_blank" rel="noreferrer" className="btn-secondary"
              style={{ fontSize: '0.78rem', padding: '6px 12px', gap: 6, textDecoration: 'none' }}>
              <Globe size={13} /> Official Website
            </a>
          )}
          {college.status === 'ACTIVE' ? (
            <button className="btn-secondary" disabled={actionLoading} onClick={() => setConfirmAction('SUSPENDED')}
              style={{ fontSize: '0.78rem', padding: '6px 12px', gap: 6, color: '#f871', borderColor: 'rgba(239,68,68,0.3)' }}>
              <Ban size={13} /> Suspend
            </button>
          ) : college.status === 'SUSPENDED' ? (
            <button className="btn-secondary" disabled={actionLoading} onClick={() => setConfirmAction('ACTIVE')}
              style={{ fontSize: '0.78rem', padding: '6px 12px', gap: 6, color: '#34d399', borderColor: 'rgba(16,185,129,0.3)' }}>
              <PlayCircle size={13} /> Reactivate
            </button>
          ) : null}
        </div>
      </div>

      {notice && (
        <div style={{ background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: 8, padding: '12px 16px', marginBottom: 20, color: '#34d399', fontSize: '0.875rem' }}>
          {notice}
        </div>
      )}

      {/* Summary cards (§11) */}
      {statCards.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 12, marginBottom: 24 }}>
          {statCards.map(({ label, value, icon: Icon }) => (
            <div key={label} className="glass-card" style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 10 }}>
              <Icon size={18} style={{ color: '#f08518', flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff' }}>{value ?? '—'}</div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase' }}>{label}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs (§9) */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', borderBottom: '1px solid var(--border-subtle)', marginBottom: 20 }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            style={{
              background: tab === t.key ? 'rgba(240,133,24,0.14)' : 'transparent',
              color: tab === t.key ? '#f08518' : 'var(--text-muted)',
              border: 'none', borderBottom: `2px solid ${tab === t.key ? '#f08518' : 'transparent'}`,
              padding: '9px 14px', fontSize: '0.8rem', fontWeight: tab === t.key ? 700 : 400,
              cursor: 'pointer', fontFamily: 'var(--font-sans)',
            }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tabLoading ? (
        <div style={{ padding: '36px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          <RefreshCw size={22} className="spin" style={{ margin: '0 auto 10px', opacity: 0.6 }} />
          Loading...
        </div>
      ) : (
        <div>
          {/* ── Overview (§10) ── */}
          {tab === 'overview' && (
            <div className="glass-card" style={{ padding: 24 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 18 }}>
                <Field label="College Name" value={college.name} />
                <Field label="College Code" value={college.code} />
                <Field label="Slug" value={college.slug} />
                <div><div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 4 }}>Status</div>{statusBadge(college.status)}</div>
                <Field label="Official Website" value={college.official_website} link />
                <Field label="Official Email" value={college.official_email} />
                <Field label="Phone" value={college.phone} />
                <Field label="Address" value={college.address} />
                <Field label="City" value={college.city} />
                <Field label="State" value={college.state} />
                <Field label="Country" value={college.country} />
                <Field label="University / Affiliation" value={college.university_affiliation} />
                <Field label="Created Date" value={college.created_at ? new Date(college.created_at).toLocaleString() : null} />
                <Field label="Updated Date" value={college.updated_at ? new Date(college.updated_at).toLocaleString() : null} />
                <Field label="Registration Status" value={college.registration_status} />
                <Field label="Application ID" value={college.application_id} />
                <Field label="Assistant Name" value={college.assistant_name} />
                <Field label="Max Users" value={college.max_users} />
                <Field label="Max Documents" value={college.max_documents} />
              </div>
              {college.description && (
                <div style={{ marginTop: 18 }}>
                  <Field label="Description" value={college.description} />
                </div>
              )}
              {college.logo_url && (
                <div style={{ marginTop: 18 }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 6 }}>Logo</div>
                  <img src={college.logo_url} alt={college.name} style={{ maxHeight: 80, borderRadius: 8 }} />
                </div>
              )}
            </div>
          )}

          {/* ── Admin & Users (§12) ── */}
          {tab === 'users' && (
            td.error ? <EmptyState message="Unable to load users." /> :
              !td.users || td.users.length === 0 ? <EmptyState message="No users found for this college." /> : (
                <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
                  {td.users.map(u => (
                    <div key={u.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 20px', borderBottom: '1px solid var(--border-subtle)', flexWrap: 'wrap', gap: 8 }}>
                      <div>
                        <div style={{ fontWeight: 600, color: '#fff', fontSize: '0.9rem' }}>{u.full_name}</div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{u.email}</div>
                      </div>
                      <div style={{ display: 'flex', gap: 10, alignItems: 'center', fontSize: '0.78rem' }}>
                        <span className="badge" style={{ background: 'rgba(240,133,24,0.12)', color: '#f08518', border: '1px solid rgba(240,133,24,0.3)' }}>{u.role}</span>
                        <span className="badge" style={{ background: u.is_active ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)', color: u.is_active ? '#34d399' : '#f87171', border: `1px solid ${u.is_active ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}` }}>
                          {u.is_active ? 'ACTIVE' : 'INACTIVE'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )
          )}

          {/* ── Knowledge (§13) ── */}
          {tab === 'knowledge' && (
            td.error ? <EmptyState message="Unable to load knowledge." /> :
              !td.records || td.records.length === 0 ? <EmptyState message="No knowledge records found." /> : (
                <div>
                  {td.by_status && (
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
                      {Object.entries(td.by_status).map(([k, v]) => (
                        <div key={k} className="glass-card" style={{ padding: '10px 16px' }}>
                          <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontWeight: 700 }}>{k}</div>
                          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fff' }}>{v}</div>
                        </div>
                      ))}
                      {td.official > 0 && (
                        <div className="glass-card" style={{ padding: '10px 16px' }}>
                          <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontWeight: 700 }}>OFFICIAL / VERIFIED</div>
                          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#34d399' }}>{td.official}</div>
                        </div>
                      )}
                    </div>
                  )}
                  <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
                    {td.records.map(r => (
                      <div key={r.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 20px', borderBottom: '1px solid var(--border-subtle)', gap: 10, flexWrap: 'wrap' }}>
                        <div>
                          <div style={{ color: '#fff', fontSize: '0.88rem', fontWeight: 600 }}>{r.title}</div>
                          <div style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>{r.course || 'General'} · {r.source_type || 'UNKNOWN'}</div>
                        </div>
                        <span className="badge" style={{ alignSelf: 'center', background: 'rgba(240,133,24,0.12)', color: '#f08518', border: '1px solid rgba(240,133,24,0.3)' }}>{r.status}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )
          )}

          {/* ── Documents (§14) ── */}
          {tab === 'documents' && (
            td.error ? <EmptyState message="Unable to load documents." /> :
              !td.documents || td.documents.length === 0 ? <EmptyState message="No documents found." /> : (
                <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
                  {td.documents.map(d => (
                    <div key={d.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 20px', borderBottom: '1px solid var(--border-subtle)', gap: 10, flexWrap: 'wrap' }}>
                      <div>
                        <div style={{ color: '#fff', fontSize: '0.88rem', fontWeight: 600 }}>{d.title}</div>
                        <div style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>Type: {d.doc_type} · {d.created_at ? new Date(d.created_at).toLocaleDateString() : ''}</div>
                      </div>
                      <span className="badge" style={{ alignSelf: 'center', background: 'rgba(240,133,24,0.12)', color: '#f08518', border: '1px solid rgba(240,133,24,0.3)' }}>{d.visibility}</span>
                    </div>
                  ))}
                </div>
              )
          )}

          {/* ── Website (§15) ── */}
          {tab === 'website' && (
            td.error ? <EmptyState message="Unable to load website info." /> : (
              <div className="glass-card" style={{ padding: 24 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 18 }}>
                  <Field label="Official Website" value={td.official_website || college.official_website} link />
                  <Field label="Pages Discovered" value={td.pages_discovered} />
                  {td.last_sync && <Field label="Last Sync" value={td.last_sync.completed_at ? new Date(td.last_sync.completed_at).toLocaleString() : null} />}
                  {td.last_sync && <Field label="Sync Status" value={td.last_sync.status} />}
                  {td.last_sync && <Field label="Pages Processed" value={td.last_sync.pages_discovered} />}
                  {td.last_sync && <Field label="Pages Changed" value={td.last_sync.pages_changed} />}
                  {td.last_sync && <Field label="Pages Failed" value={td.last_sync.errors_count} />}
                </div>
                {!td.last_sync && <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: 14 }}>No website sync recorded yet.</p>}
              </div>
            )
          )}

          {/* ── RAG (§16) ── */}
          {tab === 'rag' && (
            td.error ? <EmptyState message="Unable to load RAG info." /> : (
              <div className="glass-card" style={{ padding: 24 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 18 }}>
                  <Field label="Documents" value={td.documents} />
                  <Field label="Chunks" value={td.chunks} />
                  <Field label="Embeddings" value={td.embeddings} />
                  <Field label="Index Status" value={td.index_status} />
                  <Field label="Failed Items" value={td.failed_items} />
                </div>
              </div>
            )
          )}

          {/* ── Change Requests (§17) ── */}
          {tab === 'change_requests' && (
            td.error ? <EmptyState message="Unable to load change requests." /> :
              !td.items || td.items.length === 0 ? <EmptyState message="No change requests found." /> : (
                <div>
                  {td.by_status && (
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
                      {['PENDING', 'APPROVED', 'REJECTED', 'CANCELLED', 'APPLIED'].map(k => (
                        <div key={k} className="glass-card" style={{ padding: '10px 16px' }}>
                          <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontWeight: 700 }}>{k}</div>
                          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fff' }}>{td.by_status[k] || 0}</div>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
                    {td.items.map(cr => (
                      <div key={cr.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 20px', borderBottom: '1px solid var(--border-subtle)', gap: 10, flexWrap: 'wrap' }}>
                        <div>
                          <div style={{ color: '#fff', fontSize: '0.88rem', fontWeight: 600 }}>{cr.title || `${cr.action} ${cr.entity_type}`}</div>
                          <div style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>{cr.created_at ? new Date(cr.created_at).toLocaleDateString() : ''}</div>
                        </div>
                        <span className="badge" style={{ alignSelf: 'center', background: 'rgba(240,133,24,0.12)', color: '#f08518', border: '1px solid rgba(240,133,24,0.3)' }}>{cr.status}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )
          )}

          {/* ── Feedback (§18) ── */}
          {tab === 'feedback' && (
            td.error ? <EmptyState message="Unable to load feedback." /> :
              (td.positive + td.negative + td.reports) === 0 ? <EmptyState message="No feedback found." /> : (
                <div>
                  <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
                    {[
                      ['POSITIVE', td.positive, '#34d399'],
                      ['NEGATIVE', td.negative, '#f87171'],
                      ['REPORTS', td.reports, '#f08518'],
                      ['UNRESOLVED', td.unresolved, '#fbbf24'],
                    ].map(([k, v, c]) => (
                      <div key={k} className="glass-card" style={{ padding: '10px 16px' }}>
                        <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontWeight: 700 }}>{k}</div>
                        <div style={{ fontSize: '1.2rem', fontWeight: 800, color: c }}>{v}</div>
                      </div>
                    ))}
                  </div>
                  {(td.items || []).length > 0 && (
                    <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
                      {td.items.filter(f => f.feedback_type !== 'POSITIVE').slice(0, 20).map(f => (
                        <div key={f.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 20px', borderBottom: '1px solid var(--border-subtle)', gap: 10, flexWrap: 'wrap' }}>
                          <div>
                            <div style={{ color: '#fff', fontSize: '0.85rem', fontWeight: 600 }}>{f.feedback_type} · {f.reason || 'no reason given'}</div>
                            {f.details && <div style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>{f.details}</div>}
                          </div>
                          <span className="badge" style={{ alignSelf: 'center', background: 'rgba(240,133,24,0.12)', color: '#f08518', border: '1px solid rgba(240,133,24,0.3)' }}>{f.status}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )
          )}

          {/* ── Knowledge Gaps (§19) ── */}
          {tab === 'gaps' && (
            td.error ? <EmptyState message="Unable to load knowledge gaps." /> :
              !td.items || td.items.length === 0 ? <EmptyState message="No knowledge gaps found." /> : (
                <div>
                  {td.by_status && (
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
                      {['OPEN', 'UNDER_REVIEW', 'IN_PROGRESS', 'RESOLVED'].map(k => (
                        <div key={k} className="glass-card" style={{ padding: '10px 16px' }}>
                          <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontWeight: 700 }}>{k.replace('_', ' ')}</div>
                          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fff' }}>{td.by_status[k] || 0}</div>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
                    {td.items.map(g => (
                      <div key={g.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 20px', borderBottom: '1px solid var(--border-subtle)', gap: 10, flexWrap: 'wrap' }}>
                        <div>
                          <div style={{ color: '#fff', fontSize: '0.85rem', fontWeight: 600 }}>{g.user_query}</div>
                          <div style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>Priority: {g.priority || 'Medium'} · {g.occurrence_count} occurrence(s)</div>
                        </div>
                        <span className="badge" style={{ alignSelf: 'center', background: 'rgba(240,133,24,0.12)', color: '#f08518', border: '1px solid rgba(240,133,24,0.3)' }}>{g.status}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )
          )}

          {/* ── Analytics (§20) ── */}
          {tab === 'analytics' && (
            td.error ? <EmptyState message="Unable to load analytics." /> : (
              <div className="glass-card" style={{ padding: 24 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 18 }}>
                  <Field label="Questions" value={td.questions} />
                  <Field label="Active Users" value={td.active_users} />
                  <Field label="Questions Today" value={td.questions_today} />
                  <Field label="Questions This Month" value={td.questions_this_month} />
                  <Field label="Feedback" value={td.feedback} />
                  <Field label="Unanswered Questions" value={td.unanswered_questions} />
                </div>
              </div>
            )
          )}

          {/* ── Audit History (§21) ── */}
          {tab === 'audit' && (
            td.error ? <EmptyState message="Unable to load audit history." /> :
              !td.items || td.items.length === 0 ? <EmptyState message="No audit events found for this college." /> : (
                <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
                  {td.items.map(a => (
                    <div key={a.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '11px 20px', borderBottom: '1px solid var(--border-subtle)', gap: 10, flexWrap: 'wrap', fontSize: '0.8rem' }}>
                      <div>
                        <div style={{ color: '#fff', fontWeight: 600 }}>{a.action}</div>
                        <div style={{ color: 'var(--text-dim)' }}>{a.resource}{a.trace_id ? ` · ${a.trace_id}` : ''}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ color: 'var(--text-muted)' }}>{a.created_at ? new Date(a.created_at).toLocaleString() : ''}</div>
                        <div style={{ color: a.status === 'SUCCESS' ? '#34d399' : '#f87171' }}>{a.status}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )
          )}

          {/* ── Settings (§22 — read-only view of what's already stored) ── */}
          {tab === 'settings' && (
            <div className="glass-card" style={{ padding: 24 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 18 }}>
                <Field label="Assistant Name" value={college.assistant_name} />
                <Field label="Welcome Message" value={college.welcome_message} />
                <Field label="Primary Color" value={college.primary_color} />
                <Field label="Secondary Color" value={college.secondary_color} />
                <Field label="Accent Color" value={college.accent_color} />
                <Field label="Timezone" value={college.timezone} />
                <Field label="Max Users" value={college.max_users} />
                <Field label="Max Documents" value={college.max_documents} />
                <Field label="Max Storage (MB)" value={college.max_storage_mb} />
                <Field label="Max AI Requests / Day" value={college.max_ai_requests_per_day} />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Suspend / Reactivate confirmation (§23/§24) */}
      {confirmAction && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 20 }}
          onClick={() => setConfirmAction(null)}>
          <div className="glass-card" style={{ width: '100%', maxWidth: 460, padding: 26 }} onClick={e => e.stopPropagation()}>
            <h3 style={{ fontWeight: 800, color: '#fff', marginBottom: 10 }}>
              {confirmAction === 'SUSPENDED' ? 'Suspend' : 'Reactivate'} {college.name}?
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 18 }}>
              {confirmAction === 'SUSPENDED'
                ? 'This will prevent normal college access according to the existing suspension policy.'
                : 'The college will regain normal platform access.'}
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button className="btn-secondary" onClick={() => setConfirmAction(null)}>Cancel</button>
              <button className="btn-primary" disabled={actionLoading} onClick={() => doAction(college, confirmAction)}>
                {confirmAction === 'SUSPENDED' ? 'Suspend' : 'Reactivate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
