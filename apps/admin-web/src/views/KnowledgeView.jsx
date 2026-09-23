import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { Plus, Edit2, RotateCcw, Trash2, Search, BookOpen, AlertCircle } from 'lucide-react';

const CATEGORIES = ['all','program','department','faculty','facility','fee','contact','placement','event','policy'];

function EntityModal({ entity, onSave, onClose }) {
  const [form, setForm] = useState({
    name: entity?.name || '',
    category: entity?.category || 'program',
    code: entity?.code || '',
    details: entity?.details ? JSON.stringify(entity.details, null, 2) : '{}',
    source_url: entity?.source_url || '',
    status: 'PUBLISHED'
  });
  const [error, setError] = useState('');

  const handleSave = async () => {
    try {
      const details = JSON.parse(form.details);
      await onSave({ ...form, details });
      onClose();
    } catch (err) {
      setError(err.message.includes('JSON') ? 'Details must be valid JSON' : err.message);
    }
  };

  return (
    <div style={{ position:'fixed',inset:0,background:'rgba(0,0,0,0.7)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:1000 }}>
      <div className="glass-card" style={{ width:560,maxHeight:'80vh',overflow:'auto',padding:28 }}>
        <div style={{ fontWeight:700,fontSize:'1.1rem',marginBottom:20 }}>{entity ? 'Edit Knowledge Entity' : 'New Knowledge Entity'}</div>
        {error && <div style={{ color:'#fca5a5',background:'rgba(239,68,68,0.1)',border:'1px solid rgba(239,68,68,0.3)',borderRadius:6,padding:'8px 12px',marginBottom:14,fontSize:'0.85rem' }}>{error}</div>}
        {[
          { label:'Name', field:'name', type:'text' },
          { label:'Source URL', field:'source_url', type:'text' },
          { label:'Code (optional)', field:'code', type:'text' },
        ].map(({ label, field, type }) => (
          <div key={field} style={{ marginBottom:14 }}>
            <label style={{ fontSize:'0.75rem',fontWeight:600,color:'var(--text-muted)',display:'block',marginBottom:6,textTransform:'uppercase' }}>{label}</label>
            <input className="input-field" type={type} value={form[field]} onChange={e => setForm(f => ({...f,[field]:e.target.value}))} />
          </div>
        ))}
        <div style={{ marginBottom:14 }}>
          <label style={{ fontSize:'0.75rem',fontWeight:600,color:'var(--text-muted)',display:'block',marginBottom:6,textTransform:'uppercase' }}>Category</label>
          <select className="input-field" value={form.category} onChange={e => setForm(f => ({...f,category:e.target.value}))}>
            {CATEGORIES.filter(c => c!=='all').map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div style={{ marginBottom:20 }}>
          <label style={{ fontSize:'0.75rem',fontWeight:600,color:'var(--text-muted)',display:'block',marginBottom:6,textTransform:'uppercase' }}>Details (JSON)</label>
          <textarea
            className="input-field"
            style={{ fontFamily:'var(--font-mono)',minHeight:150,resize:'vertical',fontSize:'0.8rem' }}
            value={form.details}
            onChange={e => setForm(f => ({...f,details:e.target.value}))}
          />
        </div>
        <div style={{ display:'flex',gap:10 }}>
          <button className="btn-secondary" style={{ flex:1 }} onClick={onClose}>Cancel</button>
          <button className="btn-primary" style={{ flex:1,justifyContent:'center' }} onClick={handleSave}>Save Entity</button>
        </div>
      </div>
    </div>
  );
}

export default function KnowledgeView() {
  const [entities, setEntities] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');
  const [editingEntity, setEditingEntity] = useState(null);
  const [showNew, setShowNew] = useState(false);
  const [expandedId, setExpandedId] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const params = {};
      if (search) params.search = search;
      if (category !== 'all') params.category = category;
      const res = await adminApi.getEntities(params);
      setEntities(res.items); setTotal(res.total);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [search, category]);

  const handleSave = async (form) => {
    if (editingEntity) await adminApi.updateEntity(editingEntity.id, form);
    else await adminApi.createEntity(form);
    load();
  };

  const handleDelete = async (id) => {
    if (!confirm('Permanently delete this knowledge entity?')) return;
    await adminApi.deleteEntity(id); load();
  };

  const handleRollback = async (entity) => {
    const ver = prompt('Enter version number to restore:');
    if (!ver) return;
    await adminApi.rollbackEntity(entity.id, { target_version_number: parseInt(ver), reason: 'Admin manual rollback' });
    load();
  };

  return (
    <div>
      <div style={{ display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:22 }}>
        <div>
          <h1 style={{ fontSize:'1.4rem',fontWeight:800,marginBottom:4 }}>AIT Knowledge Entities</h1>
          <p style={{ color:'var(--text-muted)',fontSize:'0.85rem' }}>{total} authoritative records · Verified institutional facts</p>
        </div>
        <button className="btn-primary" onClick={() => { setEditingEntity(null); setShowNew(true); }}>
          <Plus size={16} /> Add Entity
        </button>
      </div>

      {/* Filters */}
      <div style={{ display:'flex',gap:12,marginBottom:20 }}>
        <div style={{ position:'relative',flex:1,maxWidth:340 }}>
          <Search size={15} style={{ position:'absolute',left:12,top:'50%',transform:'translateY(-50%)',color:'var(--text-dim)',pointerEvents:'none' }} />
          <input className="input-field" placeholder="Search entities..." style={{ paddingLeft:38 }} value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <select className="input-field" style={{ width:180 }} value={category} onChange={e => setCategory(e.target.value)}>
          {CATEGORIES.map(c => <option key={c} value={c}>{c === 'all' ? 'All Categories' : c}</option>)}
        </select>
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ textAlign:'center',padding:60,color:'var(--text-muted)' }}><BookOpen size={28} style={{ opacity:0.4,marginBottom:10 }} /><div>Loading entities...</div></div>
      ) : (
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Category</th>
                <th>Code</th>
                <th>Versions</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {entities.map(e => (
                <>
                  <tr key={e.id} onClick={() => setExpandedId(expandedId === e.id ? null : e.id)} style={{ cursor:'pointer' }}>
                    <td style={{ fontWeight:600 }}>{e.name}</td>
                    <td><span className="badge badge-ait">{e.category}</span></td>
                    <td style={{ fontFamily:'var(--font-mono)',fontSize:'0.8rem',color:'var(--text-muted)' }}>{e.code || '—'}</td>
                    <td><span style={{ color:'var(--text-muted)',fontSize:'0.85rem' }}>{e.version_count}v</span></td>
                    <td style={{ color:'var(--text-dim)',fontSize:'0.8rem' }}>{e.updated_at ? new Date(e.updated_at).toLocaleDateString() : '—'}</td>
                    <td>
                      <div style={{ display:'flex',gap:6 }} onClick={ev => ev.stopPropagation()}>
                        <button className="btn-secondary" style={{ padding:'5px 10px',fontSize:'0.78rem' }} onClick={() => { setEditingEntity(e); setShowNew(true); }}>
                          <Edit2 size={13} />
                        </button>
                        <button className="btn-secondary" style={{ padding:'5px 10px',fontSize:'0.78rem' }} onClick={() => handleRollback(e)} title="Rollback">
                          <RotateCcw size={13} />
                        </button>
                        <button className="btn-danger" style={{ padding:'5px 10px' }} onClick={() => handleDelete(e.id)}>
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expandedId === e.id && (
                    <tr key={`${e.id}-detail`}>
                      <td colSpan={6} style={{ background:'rgba(10,14,28,0.5)' }}>
                        <div style={{ padding:'12px 16px' }}>
                          <div style={{ fontFamily:'var(--font-mono)',fontSize:'0.8rem',color:'#94a3b8',whiteSpace:'pre-wrap',maxHeight:200,overflow:'auto' }}>
                            {JSON.stringify(e.details, null, 2)}
                          </div>
                          <div style={{ marginTop:10,fontSize:'0.75rem',color:'var(--text-dim)' }}>
                            Source: <a href={e.source_url} target="_blank" rel="noopener noreferrer" style={{ color:'#f08518' }}>{e.source_url}</a>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(showNew || editingEntity) && (
        <EntityModal
          entity={editingEntity}
          onSave={handleSave}
          onClose={() => { setShowNew(false); setEditingEntity(null); }}
        />
      )}
    </div>
  );
}
