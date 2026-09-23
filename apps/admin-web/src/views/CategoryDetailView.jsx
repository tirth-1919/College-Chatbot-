import { useState, useEffect, useCallback } from 'react';
import { adminApi } from '../services/adminApi';
import {
  Plus, Edit2, Trash2, Search, Copy, Power, CheckCircle, AlertCircle,
  ArrowLeft, Download, X, Save, Eye,
} from 'lucide-react';

const SOURCE_TYPES = ['ADMIN_VERIFIED', 'AIT_OFFICIAL', 'GTU_OFFICIAL', 'OTHER_VERIFIED'];
const RECORD_STATUSES = ['DRAFT', 'ACTIVE', 'INACTIVE', 'ARCHIVED'];
const PAGE_SIZE = 25;

// ---------- Category-specific form schemas (extensible: add a schema for any future key) ----------
const CATEGORY_SCHEMAS = {
  scholarships: {
    label: 'Scholarship', sections: [
      { title: 'Basic Information', fields: [{ n: 'Scholarship Name *', k: 'name', req: true }, { n: 'Scholarship Type *', k: 'type', req: true }, { n: 'Academic Year *', k: 'academic_year', req: true }, { n: 'Description', k: 'description', type: 'textarea' }] },
      { title: 'Eligibility', fields: [{ n: 'Applicable Course', k: 'course' }, { n: 'Applicable Category', k: 'category' }, { n: 'Minimum Percentage', k: 'min_percentage' }, { n: 'Eligibility Criteria', k: 'eligibility', type: 'textarea' }] },
      { title: 'Benefit', fields: [{ n: 'Benefit Type', k: 'benefit_type' }, { n: 'Amount', k: 'amount' }, { n: 'Percentage', k: 'percentage' }, { n: 'Maximum Benefit', k: 'max_benefit' }] },
      { title: 'Application', fields: [{ n: 'Application Required', k: 'application_required' }, { n: 'Application Process', k: 'process', type: 'textarea' }, { n: 'Required Documents', k: 'documents' }, { n: 'Application Start Date', k: 'start_date', type: 'date' }, { n: 'Application Deadline', k: 'deadline', type: 'date' }] },
    ],
  },
  fees: {
    label: 'Fee Record', sections: [
      { title: 'Basic Information', fields: [{ n: 'Title *', k: 'name', req: true }, { n: 'Academic Year *', k: 'academic_year', req: true }, { n: 'Fee Type', k: 'fee_type' }, { n: 'Description', k: 'description', type: 'textarea' }] },
      { title: 'Fee Amounts', fields: [{ n: 'Applicable Course', k: 'course' }, { n: 'Amount', k: 'amount' }, { n: 'Installment', k: 'installment' }, { n: 'Admission Fee', k: 'admission_fee' }, { n: 'Tuition Fee', k: 'tuition_fee' }, { n: 'Exam Fee', k: 'exam_fee' }, { n: 'Other Fee', k: 'other_fee' }] },
      { title: 'Policy', fields: [{ n: 'Refund Policy', k: 'refund_policy', type: 'textarea' }] },
    ],
  },
  faculty: {
    label: 'Faculty Record', sections: [
      { title: 'Basic Information', fields: [{ n: 'Full Name *', k: 'name', req: true }, { n: 'Designation', k: 'designation' }, { n: 'Department', k: 'department' }, { n: 'Qualification', k: 'qualification' }, { n: 'Specialization', k: 'specialization' }, { n: 'Subjects', k: 'subjects' }, { n: 'Profile URL', k: 'profile' }] },
    ],
  },
};

const getSchema = (key) => CATEGORY_SCHEMAS[key] || null;

function emptyRecord(schema) {
  const meta = {};
  if (schema) schema.sections.forEach(s => s.fields.forEach(f => { meta[f.k] = ''; }));
  return {
    title: '', field_name: '', value: '', description: '', course: '',
    academic_year: '', source_type: 'ADMIN_VERIFIED', source_url: '',
    source_title: '', verified: false, status: 'DRAFT', metadata: meta,
  };
}

function RecordModal({ schema, record, onSave, onClose }) {
  const [form, setForm] = useState(record ? JSON.parse(JSON.stringify(record)) : emptyRecord(schema));
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const setField = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const setMeta = (k, v) => setForm(f => ({ ...f, metadata: { ...f.metadata, [k]: v } }));

  const handleSave = async () => {
    setError('');
    if (!form.title?.trim()) { setError('Title is required'); return; }
    setSaving(true);
    try { await onSave(form); }
    catch (err) { setError(err.message); }
    finally { setSaving(false); }
  };

  const labelStyle = { fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: 6, textTransform: 'uppercase' };
  const input = (val, onChange, type = 'text') =>
    type === 'textarea'
      ? <textarea className="input-field" style={{ minHeight: 70, resize: 'vertical' }} value={val || ''} onChange={onChange} />
      : <input className="input-field" type={type} value={val || ''} onChange={onChange} />;

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div className="glass-card" style={{ width: 640, maxHeight: '88vh', overflow: 'auto', padding: 28 }}>
        <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 20 }}>
          {record ? `Edit ${schema?.label || 'Record'}` : `Add ${schema?.label || 'Record'}`}
        </div>
        {error && <div style={{ color: '#fca5a5', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 6, padding: '8px 12px', marginBottom: 14, fontSize: '0.85rem' }}>{error}</div>}

        {/* General fields */}
        <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#f08518', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>General</div>
        <div style={{ marginBottom: 14 }}>
          <label style={labelStyle}>Title *</label>
          {input(form.title, e => setField('title', e.target.value))}
        </div>

        {/* Category-specific structured sections */}
        {schema && schema.sections.map(section => (
          <div key={section.title} style={{ marginBottom: 18 }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#f08518', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{section.title}</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12 }}>
              {section.fields.map(f => {
                // map well-known schema keys onto top-level record fields
                const isTop = ['title', 'academic_year', 'course', 'description'].includes(f.k) && f.k !== 'name' && f.k !== 'type';
                const val = f.k === 'name' ? form.title : (isTop ? form[f.k] : form.metadata[f.k]);
                const onChange = e => {
                  if (f.k === 'name') setField('title', e.target.value);
                  else if (isTop) setField(f.k, e.target.value);
                  else setMeta(f.k, e.target.value);
                };
                return (
                  <div key={f.k} style={{ marginBottom: 8 }}>
                    <label style={labelStyle}>{f.n}</label>
                    {input(val, onChange, f.type)}
                  </div>
                );
              })}
            </div>
          </div>
        ))}

        {/* Generic (schema-less) fields */}
        {!schema && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
              <div><label style={labelStyle}>Field / Label</label>{input(form.field_name, e => setField('field_name', e.target.value))}</div>
              <div><label style={labelStyle}>Value / Summary</label>{input(form.value, e => setField('value', e.target.value))}</div>
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={labelStyle}>Details (JSON)</label>
              <textarea className="input-field" style={{ fontFamily: 'var(--font-mono)', minHeight: 110, resize: 'vertical', fontSize: '0.8rem' }}
                value={typeof form.metadata === 'string' ? form.metadata : JSON.stringify(form.metadata || {}, null, 2)}
                onChange={e => setForm(f => ({ ...f, metadata: e.target.value }))}
              />
            </div>
          </>
        )}

        {/* Common: course / year / source / verification / status */}
        <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#f08518', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Source & Verification</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 14 }}>
          <div><label style={labelStyle}>Course</label>{input(form.course, e => setField('course', e.target.value))}</div>
          <div><label style={labelStyle}>Academic Year</label>{input(form.academic_year, e => setField('academic_year', e.target.value), 'text')}</div>
          <div>
            <label style={labelStyle}>Source Type *</label>
            <select className="input-field" value={form.source_type} onChange={e => setField('source_type', e.target.value)}>
              {SOURCE_TYPES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div><label style={labelStyle}>Source URL</label>{input(form.source_url, e => setField('source_url', e.target.value))}</div>
          <div><label style={labelStyle}>Source Title</label>{input(form.source_title, e => setField('source_title', e.target.value))}</div>
          <div>
            <label style={labelStyle}>Verification</label>
            <select className="input-field" value={form.verified ? 'yes' : 'no'} onChange={e => setField('verified', e.target.value === 'yes')}>
              <option value="no">⚠ Needs Verification</option>
              <option value="yes">✓ Verified</option>
            </select>
          </div>
          <div>
            <label style={labelStyle}>Status</label>
            <select className="input-field" value={form.status} onChange={e => setField('status', e.target.value)}>
              {RECORD_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
          <button className="btn-secondary" style={{ flex: 1 }} onClick={onClose}><X size={14} /> Cancel</button>
          <button className="btn-primary" style={{ flex: 1, justifyContent: 'center' }} disabled={saving} onClick={handleSave}>
            <Save size={14} /> {saving ? 'Saving...' : `Save ${schema?.label || 'Record'}`}
          </button>
        </div>
      </div>
    </div>
  );
}

function RecordDetailModal({ record, categoryName, onAction, onClose }) {
  const rows = [
    ['Title', record.title], ['Course', record.course], ['Academic Year', record.academic_year],
    ['Field', record.field_name], ['Value', record.value], ['Description', record.description],
    ['Source Type', record.source_type], ['Source URL', record.source_url],
    ['Verified', record.verified ? '✓ Yes' : '⚠ Needs Verification'],
    ['Verified By', record.verified_by], ['Verified At', record.verified_at],
    ['Valid From', record.valid_from], ['Valid Until', record.valid_until],
    ['Status', record.status],
    ...Object.entries(record.metadata || {}),
  ].filter(([, v]) => v !== null && v !== undefined && v !== '');

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }} onClick={onClose}>
      <div className="glass-card" style={{ width: 560, maxHeight: '85vh', overflow: 'auto', padding: 28 }} onClick={e => e.stopPropagation()}>
        <div style={{ fontWeight: 800, fontSize: '1.05rem', marginBottom: 4, textTransform: 'uppercase', color: '#f08518' }}>{categoryName} Details</div>
        <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: '8px 16px', margin: '16px 0', fontSize: '0.88rem' }}>
          {rows.map(([k, v]) => (
            <div key={k} style={{ display: 'contents' }}>
              <div style={{ color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.8rem', textTransform: 'capitalize' }}>{k.replace(/_/g, ' ')}</div>
              <div style={{ wordBreak: 'break-word' }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button className="btn-secondary" onClick={() => onAction('edit', record)}><Edit2 size={13} /> Edit</button>
          <button className="btn-secondary" onClick={() => onAction('duplicate', record)}><Copy size={13} /> Duplicate</button>
          <button className="btn-secondary" onClick={() => onAction('toggle', record)}><Power size={13} /> {record.status === 'ACTIVE' ? 'Disable' : 'Enable'}</button>
          <button className="btn-danger" onClick={() => onAction('delete', record)}><Trash2 size={13} /> Delete</button>
          <button className="btn-secondary" style={{ marginLeft: 'auto' }} onClick={onClose}><X size={13} /> Close</button>
        </div>
      </div>
    </div>
  );
}

export default function CategoryDetailView({ category, onBack }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [search, setSearch] = useState('');
  const [course, setCourse] = useState('');
  const [year, setYear] = useState('');
  const [sourceType, setSourceType] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [viewing, setViewing] = useState(null);
  const [saving, setSaving] = useState(false);

  const schema = getSchema(category.key);
  const addLabel = schema ? `Add ${schema.label}` : 'Add Data';

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const params = { skip: page * PAGE_SIZE, limit: PAGE_SIZE };
      if (search) params.search = search;
      if (course) params.course = course;
      if (year) params.academic_year = year;
      if (sourceType) params.source_type = sourceType;
      if (status) params.record_status = status;
      const res = await adminApi.getKnowledgeRecords(category.id, params);
      setData(res);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }, [category.id, page, search, course, year, sourceType, status]);

  useEffect(() => { load(); }, [load]);

  const flash = (msg) => { setNotice(msg); setTimeout(() => setNotice(''), 4000); };

  const handleSave = async (form) => {
    setSaving(true);
    try {
      let meta = form.metadata;
      if (!schema && typeof meta === 'string') {
        try { meta = JSON.parse(meta || '{}'); }
        catch { throw new Error('Details must be valid JSON'); }
      }
      const payload = { ...form, metadata: meta };
      if (editing) {
        await adminApi.updateKnowledgeRecord(editing.id, payload);
        flash('Updated successfully.');
      } else {
        await adminApi.createKnowledgeRecord(category.id, payload);
        flash('Record created successfully.');
      }
      setShowModal(false); setEditing(null); load();
    } finally { setSaving(false); }
  };

  const handleAction = async (action, rec) => {
    try {
      if (action === 'edit') { setEditing(rec); setViewing(null); setShowModal(true); return; }
      if (action === 'duplicate') {
        const res = await adminApi.duplicateKnowledgeRecord(rec.id);
        flash(res.message || 'Record duplicated successfully. The new record is currently Draft.');
      }
      if (action === 'toggle') {
        if (rec.status === 'ACTIVE') { await adminApi.disableKnowledgeRecord(rec.id); flash('Record disabled.'); }
        else { await adminApi.enableKnowledgeRecord(rec.id); flash('Record enabled.'); }
      }
      if (action === 'delete') {
        if (rec.verified && !confirm('This record is VERIFIED. Are you sure you want to permanently delete it?')) return;
        if (!confirm('Are you sure you want to delete this record?')) return;
        await adminApi.deleteKnowledgeRecord(rec.id);
        flash('Record deleted successfully.');
        setViewing(null);
      }
      load();
    } catch (err) { alert(err.message); }
  };

  const handleExport = async () => {
    try {
      const res = await adminApi.exportKnowledgeRecords(category.id);
      const blob = new Blob([JSON.stringify(res, null, 2)], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `${category.key}-records.json`;
      a.click();
      flash('Export downloaded.');
    } catch (err) { alert(err.message); }
  };

  const total = data?.total || 0;
  const records = data?.items || [];
  const options = data?.filter_options || { courses: [], academic_years: [] };
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const labelStyle = { fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' };

  const verBadge = (r) => r.verified
    ? <span style={{ color: '#34d399', fontSize: '0.78rem' }}>✓ Verified</span>
    : r.status === 'DRAFT'
      ? <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>Draft</span>
      : <span style={{ color: '#fbbf24', fontSize: '0.78rem' }}>⚠ Needs Verification</span>;

  return (
    <div>
      {/* Breadcrumb + header */}
      <div style={{ marginBottom: 20 }}>
        <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 6, padding: 0, marginBottom: 10, fontFamily: 'var(--font-sans)' }}>
          <ArrowLeft size={13} /> Knowledge Database / Categories
        </button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: 4 }}>{category.icon} {category.name.toUpperCase()}</h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{category.description || `${category.name} records`}</p>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn-primary" onClick={() => { setEditing(null); setShowModal(true); }}><Plus size={16} /> {addLabel}</button>
            <button className="btn-secondary" onClick={handleExport}><Download size={15} /> Export</button>
          </div>
        </div>
      </div>

      {notice && <div style={{ color: '#34d399', background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: 6, padding: '10px 14px', marginBottom: 16, fontSize: '0.85rem' }}>{notice}</div>}
      {error && <div style={{ color: '#fca5a5', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 6, padding: '10px 14px', marginBottom: 16, fontSize: '0.85rem' }}>{error}</div>}

      {/* Filters */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
          <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)', pointerEvents: 'none' }} />
          <input className="input-field" placeholder={`Search ${category.name.toLowerCase()} records...`} style={{ paddingLeft: 38 }} value={search} onChange={e => { setPage(0); setSearch(e.target.value); }} />
        </div>
        <select className="input-field" style={{ width: 150 }} value={course} onChange={e => { setPage(0); setCourse(e.target.value); }}>
          <option value="">Course: All</option>
          {options.courses.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select className="input-field" style={{ width: 150 }} value={year} onChange={e => { setPage(0); setYear(e.target.value); }}>
          <option value="">Year: All</option>
          {options.academic_years.map(y => <option key={y} value={y}>{y}</option>)}
        </select>
        <select className="input-field" style={{ width: 160 }} value={sourceType} onChange={e => { setPage(0); setSourceType(e.target.value); }}>
          <option value="">Source: All</option>
          {SOURCE_TYPES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select className="input-field" style={{ width: 140 }} value={status} onChange={e => { setPage(0); setStatus(e.target.value); }}>
          <option value="">Status: All</option>
          {RECORD_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {/* Content */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>Loading records...</div>
      ) : records.length === 0 ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
          <div style={{ fontSize: '2.2rem', marginBottom: 10 }}>{category.icon}</div>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>No {category.name.toLowerCase()} records have been added yet.</div>
          <div style={{ fontSize: '0.85rem', marginBottom: 16 }}>Add the first record to make it available to the chatbot.</div>
          <button className="btn-primary" onClick={() => { setEditing(null); setShowModal(true); }}><Plus size={16} /> {addLabel}</button>
        </div>
      ) : (
        <>
          <div className="data-table-container" style={{ overflowX: 'auto' }}>
            <table className="data-table" style={{ minWidth: 760 }}>
              <thead>
                <tr>
                  <th>#</th><th>Title</th><th>Course</th><th>Academic Year</th>
                  <th>Value / Summary</th><th>Source</th><th>Verification</th><th>Status</th><th>Updated</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r, i) => (
                  <tr key={r.id} onClick={() => setViewing(r)} style={{ cursor: 'pointer' }}>
                    <td style={{ color: 'var(--text-dim)' }}>{page * PAGE_SIZE + i + 1}</td>
                    <td style={{ fontWeight: 600, maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.title}</td>
                    <td>{r.course || '—'}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{r.academic_year || '—'}</td>
                    <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>{r.value || '—'}</td>
                    <td><span className="badge badge-ait" style={{ fontSize: '0.7rem' }}>{r.source_type}</span></td>
                    <td>{verBadge(r)}</td>
                    <td><span style={{ fontSize: '0.78rem', color: r.status === 'ACTIVE' ? '#34d399' : 'var(--text-muted)' }}>{r.status}</span></td>
                    <td style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>{r.updated_at ? new Date(r.updated_at).toLocaleDateString() : '—'}</td>
                    <td onClick={e => e.stopPropagation()}>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="btn-secondary" style={{ padding: '5px 10px' }} title="View" onClick={() => setViewing(r)}><Eye size={13} /></button>
                        <button className="btn-secondary" style={{ padding: '5px 10px' }} title="Edit" onClick={() => { setEditing(r); setShowModal(true); }}><Edit2 size={13} /></button>
                        <button className="btn-secondary" style={{ padding: '5px 10px' }} title="Duplicate" onClick={() => handleAction('duplicate', r)}><Copy size={13} /></button>
                        <button className="btn-secondary" style={{ padding: '5px 10px' }} title={r.status === 'ACTIVE' ? 'Disable' : 'Enable'} onClick={() => handleAction('toggle', r)}><Power size={13} /></button>
                        <button className="btn-danger" style={{ padding: '5px 10px' }} title="Delete" onClick={() => handleAction('delete', r)}><Trash2 size={13} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16, flexWrap: 'wrap', gap: 10 }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
              Showing {total === 0 ? 0 : page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} disabled={page === 0} onClick={() => setPage(p => p - 1)}>Previous</button>
              <span style={{ padding: '6px 12px', fontSize: '0.8rem', color: '#f08518', fontWeight: 700 }}>{page + 1} / {totalPages}</span>
              <button className="btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} disabled={page + 1 >= totalPages} onClick={() => setPage(p => p + 1)}>Next</button>
            </div>
          </div>
        </>
      )}

      {(showModal || editing) && (
        <RecordModal
          schema={schema}
          record={editing ? { ...editing, metadata: editing.metadata || {} } : null}
          onSave={handleSave}
          onClose={() => { setShowModal(false); setEditing(null); }}
        />
      )}

      {viewing && (
        <RecordDetailModal
          record={viewing}
          categoryName={category.name}
          onAction={handleAction}
          onClose={() => setViewing(null)}
        />
      )}
    </div>
  );
}
