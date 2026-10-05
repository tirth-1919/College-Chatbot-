import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { useAdminAuth } from '../context/AdminAuthContext';
import {
  Building2, CheckCircle, XCircle, Clock, AlertTriangle,
  HelpCircle, Eye, Check, X, Mail, Phone, Globe, MapPin,
  KeyRound, Copy, RefreshCw, Send, FileText, Search
} from 'lucide-react';

const normalizeRole = (role) => String(role || '').trim().toUpperCase().replace(/-/g, '_');
const normalizeStatus = (status) => String(status || '').trim().toUpperCase();
const isPendingSmartUpload = (record) => normalizeStatus(record?.status) === 'PENDING_REVIEW';

export default function ApprovalCenterView() {
  const { user } = useAdminAuth();
  const isSuperAdmin = normalizeRole(user?.role) === 'SUPER_ADMIN';

  const [colleges, setColleges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('ALL'); // 'ALL' | 'PENDING' | 'UNDER_REVIEW' | 'APPROVED' | 'REJECTED' | 'NEED_MORE_INFORMATION'
  const [activeSection, setActiveSection] = useState('applications');
  const [stagedUploads, setStagedUploads] = useState([]);
  const [smartUploadLoading, setSmartUploadLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Modals state
  const [selectedCollege, setSelectedCollege] = useState(null);
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [approveCredentialsModal, setApproveCredentialsModal] = useState(null); // { college, credentials }
  const [rejectModalCollege, setRejectModalCollege] = useState(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [requestInfoCollege, setRequestInfoCollege] = useState(null);
  const [requestInfoNotes, setRequestInfoNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState('');
  const [actionErrorMsg, setActionErrorMsg] = useState('');
  const [copiedPass, setCopiedPass] = useState(false);

  const fetchColleges = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await adminApi.listColleges();
      setColleges(data || []);
    } catch (err) {
      setError(err.message || 'Failed to fetch colleges');
    } finally {
      setLoading(false);
    }
  };

  const fetchStagedUploads = async () => {
    setSmartUploadLoading(true);
    try {
      const data = await adminApi.getStagedUploads();
      setStagedUploads(Array.isArray(data) ? data : data?.records || []);
    } catch (err) {
      console.error('Failed to fetch staged uploads', err);
    } finally {
      setSmartUploadLoading(false);
    }
  };

  useEffect(() => {
    fetchColleges();
    fetchStagedUploads();
  }, []);

  const handleApprove = async (college) => {
    if (!confirm(`Are you sure you want to approve "${college.name}"? This will activate the college and generate temporary admin credentials.`)) {
      return;
    }
    setActionLoading(true);
    try {
      const res = await adminApi.approveCollege(college.id);
      // Backend returns { message, college, credentials: { admin_email, temporary_password, ... } }
      const creds = res.admin_credentials || res.credentials || {};
      setApproveCredentialsModal({
        college: res.college,
        credentials: {
          email: creds.email || creds.admin_email,
          temporary_password: creds.temporary_password,
          must_change_password: true,
        },
        message: res.message
      });
      fetchColleges();
    } catch (err) {
      alert('Approval failed: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleSendCredentials = async (college) => {
    setActionLoading(true);
    try {
      const res = await adminApi.sendCredentialsCollege(college.id);
      const creds = res.admin_credentials || res.credentials || {};
      setApproveCredentialsModal({
        college: res.college,
        credentials: {
          email: creds.email || creds.admin_email,
          temporary_password: creds.temporary_password,
          must_change_password: true,
        },
        message: res.message
      });
    } catch (err) {
      alert('Failed to send credentials: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const submitReject = async () => {
    if (!rejectionReason.trim()) {
      alert('Please enter a rejection reason for the applicant.');
      return;
    }
    setActionLoading(true);
    try {
      await adminApi.rejectCollege(rejectModalCollege.id, rejectionReason);
      setRejectModalCollege(null);
      setRejectionReason('');
      setActionSuccessMsg('Application rejected.');
      setTimeout(() => setActionSuccessMsg(''), 4000);
      fetchColleges();
    } catch (err) {
      alert('Rejection failed: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const submitRequestInfo = async () => {
    if (!requestInfoNotes.trim()) {
      alert('Please enter the details / questions required from the institution.');
      return;
    }
    setActionLoading(true);
    try {
      await adminApi.requestInfoCollege(requestInfoCollege.id, requestInfoNotes);
      setRequestInfoCollege(null);
      setRequestInfoNotes('');
      setActionSuccessMsg('Information request dispatched.');
      setTimeout(() => setActionSuccessMsg(''), 4000);
      fetchColleges();
    } catch (err) {
      alert('Request info failed: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedPass(true);
    setTimeout(() => setCopiedPass(false), 2000);
  };

  const pendingCount = colleges.filter(c => c.status === 'PENDING' || c.status === 'UNDER_REVIEW').length;
  const pendingSmartUploadRecords = stagedUploads.filter(isPendingSmartUpload);
  const pendingSmartUploadCount = pendingSmartUploadRecords.length;

  const handleApproveSmartUpload = async (recordId) => {
    setActionLoading(true);
    setActionSuccessMsg('');
    setActionErrorMsg('');
    try {
      await adminApi.approveStagedUpload(recordId);
      setActionSuccessMsg('Smart Upload document approved and ingested.');
      setTimeout(() => setActionSuccessMsg(''), 4000);
      await fetchStagedUploads();
    } catch (err) {
      alert('Approval failed: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRejectSmartUpload = async (recordId) => {
    setActionLoading(true);
    setActionSuccessMsg('');
    setActionErrorMsg('');
    try {
      await adminApi.rejectStagedUpload(recordId);
      setActionSuccessMsg('Smart Upload document rejected.');
      setTimeout(() => setActionSuccessMsg(''), 4000);
      await fetchStagedUploads();
    } catch (err) {
      alert('Rejection failed: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleApproveAllSmartUploads = async () => {
    if (!isSuperAdmin) return;
    const pendingRecords = stagedUploads.filter(isPendingSmartUpload);
    if (!pendingRecords.length) return;

    setActionLoading(true);
    setActionSuccessMsg('');
    setActionErrorMsg('');
    let successCount = 0;
    let failCount = 0;
    const errorDetails = [];

    for (const record of pendingRecords) {
      try {
        await adminApi.approveStagedUpload(record.id);
        successCount += 1;
      } catch (err) {
        failCount += 1;
        errorDetails.push(err.message || `Record ${record.id} failed`);
      }
    }

    try {
      await fetchStagedUploads();
    } catch (err) {
      console.error('Failed to refresh staged uploads after bulk approval', err);
    } finally {
      setActionLoading(false);
    }

    if (failCount === 0) {
      setActionSuccessMsg(`${successCount} document${successCount === 1 ? '' : 's'} approved and ingested successfully.`);
      setTimeout(() => setActionSuccessMsg(''), 5000);
    } else if (successCount > 0) {
      setActionSuccessMsg(`${successCount} document${successCount === 1 ? '' : 's'} approved and ingested successfully. ${failCount} failed.`);
      setActionErrorMsg(`${failCount} document${failCount === 1 ? '' : 's'} failed to approve.`);
      setTimeout(() => {
        setActionSuccessMsg('');
        setActionErrorMsg('');
      }, 6000);
    } else {
      setActionErrorMsg(`Failed to approve ${failCount} document${failCount === 1 ? '' : 's'}. ${errorDetails[0] || ''}`);
      setTimeout(() => setActionErrorMsg(''), 6000);
    }
  };

  const filteredColleges = colleges.filter(c => {
    if (filter !== 'ALL' && c.status !== filter) return false;
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      c.name?.toLowerCase().includes(q) ||
      c.code?.toLowerCase().includes(q) ||
      c.application_id?.toLowerCase().includes(q) ||
      c.contact_email?.toLowerCase().includes(q) ||
      c.contact_person?.toLowerCase().includes(q)
    );
  });

  const getStatusBadge = (status) => {
    switch (status) {
      case 'PENDING':
        return <span className="badge" style={{ background: 'rgba(240,133,24,0.15)', color: '#f08518', border: '1px solid rgba(240,133,24,0.3)', display: 'inline-flex', alignItems: 'center', gap: 5 }}><Clock size={12} /> PENDING APPROVAL</span>;
      case 'UNDER_REVIEW':
        return <span className="badge" style={{ background: 'rgba(99,102,241,0.15)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.3)', display: 'inline-flex', alignItems: 'center', gap: 5 }}><Eye size={12} /> UNDER REVIEW</span>;
      case 'APPROVED':
      case 'ACTIVE':
        return <span className="badge" style={{ background: 'rgba(16,185,129,0.15)', color: '#34d399', border: '1px solid rgba(16,185,129,0.3)', display: 'inline-flex', alignItems: 'center', gap: 5 }}><CheckCircle size={12} /> APPROVED & ACTIVE</span>;
      case 'REJECTED':
        return <span className="badge" style={{ background: 'rgba(239,68,68,0.15)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)', display: 'inline-flex', alignItems: 'center', gap: 5 }}><XCircle size={12} /> REJECTED</span>;
      case 'NEED_MORE_INFORMATION':
        return <span className="badge" style={{ background: 'rgba(245,158,11,0.15)', color: '#fbbf24', border: '1px solid rgba(245,158,11,0.3)', display: 'inline-flex', alignItems: 'center', gap: 5 }}><AlertTriangle size={12} /> INFO REQUESTED</span>;
      default:
        return <span className="badge">{status}</span>;
    }
  };

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#fff' }}>Super Admin Approval Center</h1>
            {pendingCount > 0 && (
              <span style={{
                background: '#ef4444', color: '#fff', fontSize: '0.75rem',
                fontWeight: 700, padding: '2px 8px', borderRadius: 9999
              }}>
                {pendingCount} Pending
              </span>
            )}
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Verify institutional registrations, inspect credentials, and manage tenant provisioning
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <button className="btn-secondary" onClick={fetchColleges} disabled={loading} style={{ gap: 8 }}>
            <RefreshCw size={15} className={loading ? 'spin' : ''} />
            Refresh Applications
          </button>
        </div>
      </div>

      {actionSuccessMsg && (
        <div style={{
          background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)',
          borderRadius: 8, padding: '12px 16px', marginBottom: 20, color: '#34d399',
          fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: 8
        }}>
          <CheckCircle size={16} />
          <span>{actionSuccessMsg}</span>
        </div>
      )}

      {actionErrorMsg && (
        <div style={{
          background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)',
          borderRadius: 8, padding: '12px 16px', marginBottom: 20, color: '#f87171',
          fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: 8
        }}>
          <AlertTriangle size={16} />
          <span>{actionErrorMsg}</span>
        </div>
      )}

      {/* Approval source tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        <button className={activeSection === 'applications' ? 'btn-primary' : 'btn-secondary'} onClick={() => setActiveSection('applications')} style={{ padding: '7px 15px', fontSize: '0.82rem', borderRadius: 20 }}>
          College Applications
        </button>
        <button className={activeSection === 'smart_upload' ? 'btn-primary' : 'btn-secondary'} onClick={() => setActiveSection('smart_upload')} style={{ padding: '7px 15px', fontSize: '0.82rem', borderRadius: 20 }}>
          Smart Upload ({pendingSmartUploadCount})
        </button>
      </div>

      {activeSection === 'applications' ? <>
      {/* Filter Tabs & Search */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {[
            { id: 'ALL', label: 'All Applications' },
            { id: 'PENDING', label: 'Pending Approval' },
            { id: 'UNDER_REVIEW', label: 'Under Review' },
            { id: 'APPROVED', label: 'Active / Approved' },
            { id: 'NEED_MORE_INFORMATION', label: 'Info Requested' },
            { id: 'REJECTED', label: 'Rejected' },
          ].map(t => (
            <button
              key={t.id}
              onClick={() => setFilter(t.id)}
              className={filter === t.id ? 'btn-primary' : 'btn-secondary'}
              style={{ padding: '6px 14px', fontSize: '0.8rem', borderRadius: 20 }}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div style={{ position: 'relative', width: 280 }}>
          <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
          <input
            className="input-field"
            placeholder="Search by name, code, or email..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{ paddingLeft: 34, fontSize: '0.82rem' }}
          />
        </div>
      </div>

      {/* Applications List */}
      {loading ? (
        <div style={{ padding: '48px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
          <RefreshCw size={28} className="spin" style={{ margin: '0 auto 12px', opacity: 0.6 }} />
          <div>Loading institution registrations...</div>
        </div>
      ) : filteredColleges.length === 0 ? (
        <div className="glass-card" style={{ padding: '48px 24px', textAlign: 'center' }}>
          <Building2 size={40} style={{ margin: '0 auto 16px', opacity: 0.3, color: 'var(--text-dim)' }} />
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 6 }}>No Applications Found</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            {searchQuery ? 'No results matched your search term.' : 'There are currently no college registrations in this category.'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {filteredColleges.map(college => (
            <div
              key={college.id}
              className="glass-card"
              style={{
                padding: '20px 24px',
                borderLeft: `4px solid ${
                  college.status === 'PENDING' ? '#f08518' :
                  college.status === 'APPROVED' || college.status === 'ACTIVE' ? '#10b981' :
                  college.status === 'REJECTED' ? '#ef4444' : '#6366f1'
                }`,
                display: 'flex',
                flexDirection: 'column',
                gap: 14
              }}
            >
              {/* Card top row */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                    <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fff' }}>{college.name}</h3>
                    <span style={{
                      background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border-subtle)',
                      borderRadius: 4, padding: '2px 6px', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-dim)'
                    }}>
                      {college.code}
                    </span>
                    {college.application_id && (
                      <span style={{
                        background: 'rgba(240,133,24,0.1)', border: '1px solid rgba(240,133,24,0.3)',
                        borderRadius: 4, padding: '2px 6px', fontSize: '0.75rem', fontWeight: 600, color: '#f08518'
                      }}>
                        App ID: {college.application_id}
                      </span>
                    )}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      <Building2 size={14} color="var(--text-dim)" />
                      {college.city ? `${college.city}, ${college.state}` : college.state || 'India'}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      <Mail size={14} color="var(--text-dim)" />
                      {college.contact_person ? `${college.contact_person} (${college.contact_email || college.official_email})` : college.official_email}
                    </span>
                    {college.contact_phone && (
                      <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        <Phone size={14} color="var(--text-dim)" />
                        {college.contact_phone}
                      </span>
                    )}
                    {college.created_at && (
                      <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        <Clock size={14} color="var(--text-dim)" />
                        Submitted: {new Date(college.created_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>

                <div>
                  {getStatusBadge(college.status)}
                </div>
              </div>

              {/* Review notes or rejection reason if any */}
              {college.rejection_reason && (
                <div style={{
                  background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)',
                  borderRadius: 6, padding: '8px 12px', fontSize: '0.8rem', color: '#fca5a5'
                }}>
                  <strong>Rejection Reason:</strong> {college.rejection_reason}
                </div>
              )}
              {college.review_notes && college.status === 'NEED_MORE_INFORMATION' && (
                <div style={{
                  background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)',
                  borderRadius: 6, padding: '8px 12px', fontSize: '0.8rem', color: '#fde68a'
                }}>
                  <strong>Requested Information:</strong> {college.review_notes}
                </div>
              )}

              {/* Action buttons */}
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
                gap: 10, paddingTop: 10, borderTop: '1px solid var(--border-subtle)', flexWrap: 'wrap'
              }}>
                <button
                  className="btn-secondary"
                  onClick={() => { setSelectedCollege(college); setDetailsModalOpen(true); }}
                  style={{ fontSize: '0.8rem', padding: '6px 12px', gap: 6 }}
                >
                  <Eye size={14} />
                  View Details
                </button>

                {(college.status === 'PENDING' || college.status === 'UNDER_REVIEW' || college.status === 'NEED_MORE_INFORMATION') && (
                  <>
                    <button
                      className="btn-secondary"
                      onClick={() => { setRequestInfoCollege(college); setRequestInfoNotes(''); }}
                      style={{ fontSize: '0.8rem', padding: '6px 12px', gap: 6, color: '#f59e0b', borderColor: 'rgba(245,158,11,0.3)' }}
                    >
                      <HelpCircle size={14} />
                      Request Info
                    </button>

                    <button
                      className="btn-secondary"
                      onClick={() => { setRejectModalCollege(college); setRejectionReason(''); }}
                      style={{ fontSize: '0.8rem', padding: '6px 12px', gap: 6, color: '#ef4444', borderColor: 'rgba(239,68,68,0.3)' }}
                    >
                      <X size={14} />
                      Reject
                    </button>

                    <button
                      className="btn-primary"
                      onClick={() => handleApprove(college)}
                      disabled={actionLoading}
                      style={{ fontSize: '0.8rem', padding: '6px 16px', gap: 6 }}
                    >
                      <Check size={14} />
                      Approve & Provision
                    </button>
                  </>
                )}

                {(college.status === 'APPROVED' || college.status === 'ACTIVE') && (
                  <button
                    className="btn-secondary"
                    onClick={() => handleSendCredentials(college)}
                    disabled={actionLoading}
                    style={{ fontSize: '0.8rem', padding: '6px 12px', gap: 6, color: '#34d399', borderColor: 'rgba(16,185,129,0.3)' }}
                  >
                    <Send size={14} />
                    View / Resend Credentials
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      </> : (
        <div>
          {/* Smart Upload Section Header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 20,
            flexWrap: 'wrap',
            gap: 16
          }}>
            <div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fff', marginBottom: 4 }}>
                Smart Upload Review Queue
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                Review and approve documents extracted and classified by the Smart Upload ingestion pipeline
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              {isSuperAdmin && (
                <button
                  className="btn-primary"
                  onClick={handleApproveAllSmartUploads}
                  disabled={actionLoading || pendingSmartUploadCount === 0}
                  style={{ gap: 8 }}
                >
                  {actionLoading ? <RefreshCw size={15} className="spin" /> : <Check size={15} />}
                  Approve All &amp; Ingest ({pendingSmartUploadCount})
                </button>
              )}
              <button
                className="btn-secondary"
                onClick={fetchStagedUploads}
                disabled={smartUploadLoading || actionLoading}
                style={{ gap: 8 }}
              >
                <RefreshCw size={15} className={smartUploadLoading ? 'spin' : ''} />
                Refresh Queue
              </button>
            </div>
          </div>

          {smartUploadLoading ? (
            <div style={{ padding: '48px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
              <RefreshCw size={28} className="spin" style={{ margin: '0 auto 12px', opacity: 0.6 }} />
              <div>Loading Smart Upload review queue...</div>
            </div>
          ) : pendingSmartUploadCount === 0 ? (
            <div className="glass-card" style={{ padding: '48px 24px', textAlign: 'center' }}>
              <FileText size={40} style={{ margin: '0 auto 16px', opacity: 0.3, color: 'var(--text-dim)' }} />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 6 }}>No Smart Upload Records Found</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>There are currently no Smart Upload documents pending review.</p>
            </div>
          ) : (
            <div className="glass-card" style={{ overflowX: 'auto', padding: 0 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
                <thead><tr style={{ background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid var(--border-subtle)' }}>
                  {['Document', 'Extracted Category', 'Target Department / Course', 'Academic Year', 'Confidence', 'Status', 'Actions'].map(label => <th key={label} style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--text-dim)' }}>{label}</th>)}
                </tr></thead>
                <tbody>{pendingSmartUploadRecords.map(record => {
                  const confidence = Math.max(0, Math.min(1, Number(record.confidence_score ?? 0)));
                  return <tr key={record.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '14px 18px', color: '#fff', fontWeight: 600 }}>{record.filename || record.document_name || 'Unnamed document'}</td>
                    <td style={{ padding: '14px 18px', color: 'var(--text-muted)' }}>{(record.detected_category || 'general').replaceAll('_', ' ')}</td>
                    <td style={{ padding: '14px 18px', color: 'var(--text-muted)' }}>{record.course_department || 'All Programs'}</td>
                    <td style={{ padding: '14px 18px', color: 'var(--text-muted)' }}>{record.academic_year || 'Current'}</td>
                    <td style={{ padding: '14px 18px', color: confidence > 0.8 ? '#34d399' : '#fde68a', fontWeight: 700 }}>{Math.round(confidence * 100)}%</td>
                    <td style={{ padding: '14px 18px', color: '#f08518', fontWeight: 600 }}>{record.status}</td>
                    <td style={{ padding: '14px 18px', textAlign: 'right' }}><div style={{ display: 'inline-flex', gap: 8 }}>
                      <button className="btn-secondary" onClick={() => handleRejectSmartUpload(record.id)} disabled={actionLoading} style={{ padding: '5px 10px', fontSize: '0.75rem', color: '#ef4444', borderColor: 'rgba(239,68,68,0.3)' }}><X size={13} /> Reject</button>
                      <button className="btn-primary" onClick={() => handleApproveSmartUpload(record.id)} disabled={actionLoading} style={{ padding: '5px 12px', fontSize: '0.75rem', gap: 4 }}><Check size={13} /> Approve &amp; Ingest</button>
                    </div></td>
                  </tr>;
                })}</tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* VIEW DETAILS MODAL */}
      {detailsModalOpen && selectedCollege && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 20
        }}>
          <div className="glass-card" style={{ width: '100%', maxWidth: 640, maxHeight: '90vh', overflowY: 'auto', padding: 32 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
              <div>
                <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff' }}>{selectedCollege.name}</h2>
                <div style={{ color: 'var(--text-dim)', fontSize: '0.8rem', marginTop: 4 }}>
                  Code: {selectedCollege.code} | Application: {selectedCollege.application_id || 'N/A'}
                </div>
              </div>
              <button
                onClick={() => { setDetailsModalOpen(false); setSelectedCollege(null); }}
                style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20, fontSize: '0.85rem' }}>
              <div>
                <strong style={{ color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Status:</strong>
                {getStatusBadge(selectedCollege.status)}
              </div>
              <div>
                <strong style={{ color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Affiliation:</strong>
                <span>{selectedCollege.university_affiliation || 'Independent / Autonomous'}</span>
              </div>
              <div>
                <strong style={{ color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Official Email:</strong>
                <a href={`mailto:${selectedCollege.official_email}`} style={{ color: '#f08518' }}>{selectedCollege.official_email}</a>
              </div>
              <div>
                <strong style={{ color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Website:</strong>
                {selectedCollege.official_website ? (
                  <a href={selectedCollege.official_website} target="_blank" rel="noreferrer" style={{ color: '#f08518' }}>{selectedCollege.official_website}</a>
                ) : 'N/A'}
              </div>
              <div>
                <strong style={{ color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Contact Person:</strong>
                <span>{selectedCollege.contact_person || 'N/A'}</span>
              </div>
              <div>
                <strong style={{ color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Contact Phone:</strong>
                <span>{selectedCollege.contact_phone || 'N/A'}</span>
              </div>
            </div>

            <div style={{ marginBottom: 20, fontSize: '0.85rem' }}>
              <strong style={{ color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Campus Address:</strong>
              <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px 14px', borderRadius: 6, color: 'var(--text-primary)' }}>
                {selectedCollege.address || 'N/A'}, {selectedCollege.city || ''}, {selectedCollege.state || ''} - {selectedCollege.country || 'India'}
              </div>
            </div>

            {selectedCollege.description && (
              <div style={{ marginBottom: 20, fontSize: '0.85rem' }}>
                <strong style={{ color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Institutional Profile / Description:</strong>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px 14px', borderRadius: 6, color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
                  {selectedCollege.description}
                </div>
              </div>
            )}

            {selectedCollege.auth_document_path && (
              <div style={{ marginBottom: 20, fontSize: '0.85rem' }}>
                <strong style={{ color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Authorization Document:</strong>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '8px 12px', borderRadius: 6, color: 'var(--text-primary)' }}>
                  File Reference: {selectedCollege.auth_document_path}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 24, borderTop: '1px solid var(--border-subtle)', paddingTop: 16 }}>
              <button className="btn-secondary" onClick={() => { setDetailsModalOpen(false); setSelectedCollege(null); }}>
                Close
              </button>
              {(selectedCollege.status === 'PENDING' || selectedCollege.status === 'UNDER_REVIEW') && (
                <button className="btn-primary" onClick={() => { setDetailsModalOpen(false); handleApprove(selectedCollege); }}>
                  Approve Application
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* APPROVE & CREDENTIALS POPUP MODAL */}
      {approveCredentialsModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1100, padding: 20
        }}>
          <div className="glass-card" style={{ width: '100%', maxWidth: 520, padding: 32, border: '1px solid rgba(16,185,129,0.4)' }}>
            <div style={{ textAlign: 'center', marginBottom: 20 }}>
              <div style={{
                width: 60, height: 60, borderRadius: '50%', background: 'rgba(16,185,129,0.15)',
                border: '1px solid rgba(16,185,129,0.4)', display: 'flex', alignItems: 'center',
                justifyContent: 'center', margin: '0 auto 16px'
              }}>
                <CheckCircle size={30} color="#10b981" />
              </div>
              <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: '#fff', marginBottom: 6 }}>
                College Approved & Activated!
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                {approveCredentialsModal.message || 'The college is now active in the platform. A College Admin account has been provisioned.'}
              </p>
            </div>

            {/* Credentials Card */}
            <div style={{
              background: 'rgba(0,0,0,0.35)', border: '1px solid var(--border-subtle)',
              borderRadius: 8, padding: '16px 20px', marginBottom: 20
            }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#f08518', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>
                College Admin Provisioned Credentials
              </div>
              <div style={{ marginBottom: 10, display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Admin Email:</span>
                <strong style={{ color: '#fff' }}>{approveCredentialsModal.credentials?.email}</strong>
              </div>
              <div style={{ marginBottom: 10, display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)' }}>Temp Password:</span>
                <span style={{
                  fontFamily: 'monospace', fontSize: '0.95rem', fontWeight: 700,
                  color: '#34d399', background: 'rgba(16,185,129,0.1)', padding: '2px 8px', borderRadius: 4
                }}>
                  {approveCredentialsModal.credentials?.temporary_password || '********'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Policy Note:</span>
                <span style={{ color: '#f59e0b', fontSize: '0.8rem', fontWeight: 600 }}>
                  Forced password change on first login
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <button
                className="btn-secondary"
                style={{ flex: 1, justifyContent: 'center', gap: 8 }}
                onClick={() => copyToClipboard(
                  `College: ${approveCredentialsModal.college?.name}\nAdmin Login: ${approveCredentialsModal.credentials?.email}\nTemporary Password: ${approveCredentialsModal.credentials?.temporary_password}\nPortal: http://localhost:8001`
                )}
              >
                {copiedPass ? <Check size={16} color="#10b981" /> : <Copy size={16} />}
                {copiedPass ? 'Copied to Clipboard!' : 'Copy Credentials'}
              </button>
              <button
                className="btn-primary"
                style={{ flex: 1, justifyContent: 'center' }}
                onClick={() => setApproveCredentialsModal(null)}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* REJECT MODAL */}
      {rejectModalCollege && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 20
        }}>
          <div className="glass-card" style={{ width: '100%', maxWidth: 480, padding: 28 }}>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fff', marginBottom: 8 }}>
              Reject College Application
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 16 }}>
              Provide a clear reason for declining the registration of <strong>{rejectModalCollege.name}</strong>. The applicant will see this reason when querying application status.
            </p>
            <textarea
              className="input-field"
              rows={4}
              placeholder="e.g. Could not verify official educational accreditation from the state university board..."
              value={rejectionReason}
              onChange={e => setRejectionReason(e.target.value)}
              style={{ marginBottom: 18 }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button className="btn-secondary" onClick={() => setRejectModalCollege(null)} disabled={actionLoading}>
                Cancel
              </button>
              <button
                className="btn-primary"
                style={{ background: '#ef4444', borderColor: '#dc2626' }}
                onClick={submitReject}
                disabled={actionLoading}
              >
                {actionLoading ? 'Rejecting...' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* REQUEST INFO MODAL */}
      {requestInfoCollege && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 20
        }}>
          <div className="glass-card" style={{ width: '100%', maxWidth: 480, padding: 28 }}>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fff', marginBottom: 8 }}>
              Request Additional Information
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 16 }}>
              Specify the missing documentation or clarification required from <strong>{requestInfoCollege.name}</strong>.
            </p>
            <textarea
              className="input-field"
              rows={4}
              placeholder="e.g. Please provide your latest AICTE affiliation approval certificate and official registrar contact..."
              value={requestInfoNotes}
              onChange={e => setRequestInfoNotes(e.target.value)}
              style={{ marginBottom: 18 }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button className="btn-secondary" onClick={() => setRequestInfoCollege(null)} disabled={actionLoading}>
                Cancel
              </button>
              <button className="btn-primary" onClick={submitRequestInfo} disabled={actionLoading}>
                {actionLoading ? 'Sending Request...' : 'Send Information Request'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
