import { useState, useEffect, useRef } from 'react';
import { adminApi } from '../services/adminApi';
import {
  UploadCloud, FileText, CheckCircle, XCircle, Clock, AlertTriangle,
  FolderArchive, Sparkles, RefreshCw, Check, X, ArrowRight, Database,
  FileSpreadsheet, FileCode, Image as ImageIcon, Filter, Tag
} from 'lucide-react';

export default function SmartUploadView() {
  const [stagedRecords, setStagedRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState('');
  const [uploadError, setUploadError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [statusFilter, setStatusFilter] = useState('ALL'); // 'ALL' | 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED'
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const fileInputRef = useRef(null);

  const fetchStagedRecords = async () => {
    setLoading(true);
    try {
      const data = await adminApi.getStagedUploads();
      setStagedRecords(data || []);
    } catch (err) {
      console.error('Failed to fetch staged uploads', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStagedRecords();
  }, []);

  const handleFiles = async (files) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setUploadError('');
    setUploadSuccess('');

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    try {
      const res = await adminApi.smartUpload(formData);
      setUploadSuccess(`Successfully processed ${res.count || files.length} file(s). Auto-classified and staged for review.`);
      fetchStagedRecords();
    } catch (err) {
      setUploadError(err.message || 'File upload and classification failed');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleApprove = async (recordId) => {
    setActionLoadingId(recordId);
    try {
      await adminApi.approveStagedUpload(recordId);
      fetchStagedRecords();
    } catch (err) {
      alert('Approval failed: ' + err.message);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleReject = async (recordId) => {
    const reason = prompt('Please enter a rejection reason (optional):') ?? '';
    setActionLoadingId(recordId);
    try {
      await adminApi.rejectStagedUpload(recordId, reason);
      fetchStagedRecords();
    } catch (err) {
      alert('Rejection failed: ' + err.message);
    } finally {
      setActionLoadingId(null);
    }
  };

  const getFileIcon = (filename = '') => {
    const ext = filename.split('.').pop().toLowerCase();
    if (ext === 'zip') return <FolderArchive size={20} color="#f08518" />;
    if (['xlsx', 'xls', 'csv'].includes(ext)) return <FileSpreadsheet size={20} color="#10b981" />;
    if (['png', 'jpg', 'jpeg', 'webp'].includes(ext)) return <ImageIcon size={20} color="#6366f1" />;
    return <FileText size={20} color="#38bdf8" />;
  };

  const getCategoryColor = (cat = '') => {
    const c = cat.toLowerCase();
    if (c.includes('fee')) return { bg: 'rgba(239,68,68,0.12)', text: '#fca5a5', border: 'rgba(239,68,68,0.3)' };
    if (c.includes('faculty')) return { bg: 'rgba(16,185,129,0.12)', text: '#6ee7b7', border: 'rgba(16,185,129,0.3)' };
    if (c.includes('course')) return { bg: 'rgba(99,102,241,0.12)', text: '#a5b4fc', border: 'rgba(99,102,241,0.3)' };
    if (c.includes('placement')) return { bg: 'rgba(240,133,24,0.12)', text: '#fdba74', border: 'rgba(240,133,24,0.3)' };
    if (c.includes('admission')) return { bg: 'rgba(14,165,233,0.12)', text: '#7dd3fc', border: 'rgba(14,165,233,0.3)' };
    if (c.includes('event')) return { bg: 'rgba(236,72,153,0.12)', text: '#f472b6', border: 'rgba(236,72,153,0.3)' };
    return { bg: 'rgba(148,163,184,0.12)', text: '#cbd5e1', border: 'rgba(148,163,184,0.3)' };
  };

  const filteredRecords = stagedRecords.filter(r => {
    if (statusFilter === 'ALL') return true;
    return r.status === statusFilter;
  });

  const pendingCount = stagedRecords.filter(r => r.status === 'PENDING_REVIEW').length;

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#fff' }}>Smart Upload & Auto-Classification</h1>
            <span style={{
              background: 'rgba(240,133,24,0.15)', color: '#f08518', border: '1px solid rgba(240,133,24,0.35)',
              padding: '2px 8px', borderRadius: 12, fontSize: '0.75rem', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4
            }}>
              <Sparkles size={12} /> AI Classification
            </span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Upload syllabus, fee structures, faculty rosters, or batch ZIPs. AI extracts and classifies documents before RAG indexing.
          </p>
        </div>
        <button className="btn-secondary" onClick={fetchStagedRecords} disabled={loading} style={{ gap: 8 }}>
          <RefreshCw size={15} className={loading ? 'spin' : ''} />
          Refresh Queue
        </button>
      </div>

      {/* Drag and Drop Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{
          border: `2px dashed ${dragActive ? '#f08518' : 'rgba(240,133,24,0.35)'}`,
          background: dragActive ? 'rgba(240,133,24,0.08)' : 'rgba(11,15,35,0.6)',
          borderRadius: 12,
          padding: '36px 24px',
          textAlign: 'center',
          cursor: 'pointer',
          marginBottom: 28,
          transition: 'all 0.2s ease',
          boxShadow: dragActive ? '0 0 25px rgba(240,133,24,0.2)' : 'none'
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.jpg,.jpeg,.png,.webp,.zip"
          style={{ display: 'none' }}
          onChange={(e) => handleFiles(e.target.files)}
        />
        <div style={{
          width: 56, height: 56, borderRadius: '50%',
          background: 'linear-gradient(135deg, rgba(240,133,24,0.2), rgba(240,133,24,0.05))',
          border: '1px solid rgba(240,133,24,0.4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 16px'
        }}>
          <UploadCloud size={28} color="#f08518" />
        </div>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: 6 }}>
          {uploading ? 'Analyzing & Classifying Content...' : 'Drag & Drop Documents or Institutional ZIP Archives'}
        </h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', maxWidth: 520, margin: '0 auto 14px' }}>
          Supports <strong>PDF, DOCX, XLSX, CSV, Images, & ZIP</strong>. Files are classified into Fees, Faculty, Courses, Placements, Admissions, Events, or General Knowledge.
        </p>
        <button
          type="button"
          className="btn-primary"
          disabled={uploading}
          style={{ padding: '8px 20px', fontSize: '0.85rem', pointerEvents: 'none' }}
        >
          {uploading ? 'Processing Multi-Format Ingestion...' : 'Browse Local Files'}
        </button>
      </div>

      {uploadSuccess && (
        <div style={{
          background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)',
          borderRadius: 8, padding: '12px 16px', marginBottom: 20, color: '#34d399',
          fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: 8
        }}>
          <CheckCircle size={16} />
          <span>{uploadSuccess}</span>
        </div>
      )}

      {uploadError && (
        <div style={{
          background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)',
          borderRadius: 8, padding: '12px 16px', marginBottom: 20, color: '#fca5a5',
          fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: 8
        }}>
          <AlertTriangle size={16} />
          <span>{uploadError}</span>
        </div>
      )}

      {/* Filter Tabs */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18, flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {[
            { id: 'ALL', label: `All Files (${stagedRecords.length})` },
            { id: 'PENDING_REVIEW', label: `Pending Review (${pendingCount})` },
            { id: 'APPROVED', label: 'Approved / Ingested' },
            { id: 'REJECTED', label: 'Rejected' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
              className={statusFilter === tab.id ? 'btn-primary' : 'btn-secondary'}
              style={{ padding: '6px 14px', fontSize: '0.8rem', borderRadius: 20 }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Review Queue Table / List */}
      {loading ? (
        <div style={{ padding: '48px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
          <RefreshCw size={28} className="spin" style={{ margin: '0 auto 12px', opacity: 0.6 }} />
          <div>Loading staged uploads...</div>
        </div>
      ) : filteredRecords.length === 0 ? (
        <div className="glass-card" style={{ padding: '48px 24px', textAlign: 'center' }}>
          <FileText size={36} style={{ margin: '0 auto 14px', opacity: 0.3, color: 'var(--text-dim)' }} />
          <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: 4 }}>No Staged Documents</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Upload institutional documents above to see auto-classification results and stage for RAG ingestion.
          </p>
        </div>
      ) : (
        <div className="glass-card" style={{ overflowX: 'auto', padding: 0 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid var(--border-subtle)' }}>
                <th style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--text-dim)' }}>Document</th>
                <th style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--text-dim)' }}>Extracted Category</th>
                <th style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--text-dim)' }}>Target Department / Course</th>
                <th style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--text-dim)' }}>Academic Year</th>
                <th style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--text-dim)' }}>Confidence</th>
                <th style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--text-dim)' }}>Status</th>
                <th style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--text-dim)', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredRecords.map(rec => {
                const catStyle = getCategoryColor(rec.detected_category);
                const isPending = rec.status === 'PENDING_REVIEW';
                const isActionLoading = actionLoadingId === rec.id;

                return (
                  <tr key={rec.id} style={{ borderBottom: '1px solid var(--border-subtle)', transition: 'background 0.15s ease' }}>
                    {/* Document */}
                    <td style={{ padding: '14px 18px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        {getFileIcon(rec.original_filename)}
                        <div>
                          <div style={{ fontWeight: 600, color: '#fff', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={rec.original_filename}>
                            {rec.original_filename}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                            {rec.file_size ? `${Math.round(rec.file_size / 1024)} KB` : ''} · {rec.file_type || 'file'}
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Extracted Category */}
                    <td style={{ padding: '14px 18px' }}>
                      <span style={{
                        background: catStyle.bg, color: catStyle.text, border: `1px solid ${catStyle.border}`,
                        padding: '3px 8px', borderRadius: 6, fontSize: '0.78rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 4
                      }}>
                        <Tag size={11} />
                        {rec.detected_category || 'General'}
                      </span>
                    </td>

                    {/* Target Course */}
                    <td style={{ padding: '14px 18px', color: 'var(--text-muted)' }}>
                      {rec.target_course || 'All Departments'}
                    </td>

                    {/* Academic Year */}
                    <td style={{ padding: '14px 18px', color: 'var(--text-muted)' }}>
                      {rec.academic_year || 'Current'}
                    </td>

                    {/* Confidence Score */}
                    <td style={{ padding: '14px 18px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 50, height: 6, background: 'rgba(255,255,255,0.1)', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{
                            width: `${Math.round((rec.confidence_score || 0.85) * 100)}%`,
                            height: '100%',
                            background: (rec.confidence_score || 0.85) > 0.8 ? '#10b981' : '#f59e0b',
                            borderRadius: 3
                          }} />
                        </div>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: (rec.confidence_score || 0.85) > 0.8 ? '#34d399' : '#fde68a' }}>
                          {Math.round((rec.confidence_score || 0.85) * 100)}%
                        </span>
                      </div>
                    </td>

                    {/* Status */}
                    <td style={{ padding: '14px 18px' }}>
                      {rec.status === 'PENDING_REVIEW' && (
                        <span style={{ color: '#f08518', fontSize: '0.78rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                          <Clock size={12} /> Pending Review
                        </span>
                      )}
                      {rec.status === 'APPROVED' && (
                        <span style={{ color: '#34d399', fontSize: '0.78rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                          <CheckCircle size={12} /> Ingested to RAG
                        </span>
                      )}
                      {rec.status === 'REJECTED' && (
                        <span style={{ color: '#f87171', fontSize: '0.78rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                          <XCircle size={12} /> Rejected
                        </span>
                      )}
                    </td>

                    {/* Actions */}
                    <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                      {isPending ? (
                        <div style={{ display: 'inline-flex', gap: 8 }}>
                          <button
                            className="btn-secondary"
                            onClick={() => handleReject(rec.id)}
                            disabled={isActionLoading}
                            style={{ padding: '5px 10px', fontSize: '0.75rem', color: '#ef4444', borderColor: 'rgba(239,68,68,0.3)' }}
                            title="Reject and discard"
                          >
                            <X size={13} />
                            Reject
                          </button>
                          <button
                            className="btn-primary"
                            onClick={() => handleApprove(rec.id)}
                            disabled={isActionLoading}
                            style={{ padding: '5px 12px', fontSize: '0.75rem', gap: 4 }}
                            title="Approve and write to RAG Knowledge Store"
                          >
                            <Check size={13} />
                            Approve & Ingest
                          </button>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>Completed</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
