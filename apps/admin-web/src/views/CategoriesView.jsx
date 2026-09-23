import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { Plus, Edit2, Trash2, Search, Database, Eye, Power } from 'lucide-react';

function CategoryModal({ category, onSave, onClose }) {
  const [form, setForm] = useState({
    name: category?.name || '',
    key: category?.key || '',
    description: category?.description || '',
    icon: category?.icon || '📁',
    display_order: category?.display_order ?? 0,
    status: category?.status || 'ACTIVE',
  });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true); setError('');
    try { await onSave(form); onClose(); }
    catch (err) { setError(err.message); }
    finally { setSaving(false); }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div className="glass-card" style={{ width: 520, maxHeight: '85vh', overflow: 'auto', padding: 28 }}>
        <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 20 }}>{category ? 'Edit Category' : 'Add Category'}</div>
        {error && <div style={{ color: '#fca5a5', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 6, padding: '8px 12px', marginBottom: 14, fontSize: '0.85rem' }}>{error}</div>}
        {[
          { label: 'Category Name *', field: 'name' },
          { label: 'Category Key * (lowercase-with-hyphens)', field: 'key' },
          { label: 'Description', field: 'description' },
          { label: 'Icon (emoji)', field: 'icon' },
          { label: 'Display Order', field: 'display_order', type: 'number' },
        ].map(({ label, field, type }) => (
          <div key={field} style={{ marginBottom: 14 }}>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: 6, textTransform: 'uppercase' }}>{label}</label>
            <input
              className="input-field" type={type || 'text'} disabled={!!category && field === 'key'}
              value={form[field]} onChange={e => setForm(f => ({ ...f, [field]: type === 'number' ? parseInt(e.target.value || 0) : e.target.value }))}
            />
          </div>
        ))}
        <div style={{ marginBottom: 20 }}>
          <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: 6, textTransform: 'uppercase' }}>Status</label>
          <select className="input-field" value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))}>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Inactive</option>
          </select>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn-secondary" style={{ flex: 1 }} onClick={onClose}>Cancel</button>
          <button className="btn-primary" style={{ flex: 1, justifyContent: 'center' }} disabled={saving} onClick={handleSave}>
            {saving ? 'Saving...' : category ? 'Save Changes' : 'Create Category'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function CategoriesView({ onOpenCategory }) {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true); setError('');
    try {
      const res = await adminApi.getKnowledgeCategories(search ? { search } : {});
      setCategories(res.items);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [search]);

  const handleSave = async (form) => {
    setSaving(true);
    try {
      if (editing) await adminApi.updateKnowledgeCategory(editing.id, form);
      else await adminApi.createKnowledgeCategory(form);
      setShowModal(false); setEditing(null); load();
    } finally { setSaving(false); }
  };

  const toggleStatus = async (c) => {
    await adminApi.updateKnowledgeCategory(c.id, { status: c.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE' });
    load();
  };

  const handleDelete = async (c) => {
    if (c.record_count > 0) {
      alert(`This category contains ${c.record_count} record(s). Move or delete the records before deleting this category.`);
      return;
    }
    if (!confirm(`Are you sure you want to delete the category "${c.name}"?`)) return;
    try { await adminApi.deleteKnowledgeCategory(c.id); load(); }
    catch (err) { alert(err.message); }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 22, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: 4 }}>Knowledge Categories</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Organize chatbot knowledge into manageable categories</p>
        </div>
        <button className="btn-primary" onClick={() => { setEditing(null); setShowModal(true); }}>
          <Plus size={16} /> Add Category
        </button>
      </div>

      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: 340 }}>
          <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)', pointerEvents: 'none' }} />
          <input className="input-field" placeholder="Search categories..." style={{ paddingLeft: 38 }} value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      </div>

      {error && <div style={{ color: '#fca5a5', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 6, padding: '10px 14px', marginBottom: 16, fontSize: '0.85rem' }}>{error}</div>}

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}><Database size={28} style={{ opacity: 0.4, marginBottom: 10 }} /><div>Loading categories...</div></div>
      ) : categories.length === 0 ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
          <Database size={36} style={{ opacity: 0.3, marginBottom: 12 }} />
          <div style={{ fontWeight: 600, marginBottom: 4 }}>No categories found</div>
          <div style={{ fontSize: '0.85rem', marginBottom: 16 }}>Create your first category to start organizing knowledge.</div>
          <button className="btn-primary" onClick={() => { setEditing(null); setShowModal(true); }}><Plus size={16} /> Add Category</button>
        </div>
      ) : (
        <div className="data-table-container" style={{ overflowX: 'auto' }}>
          <table className="data-table" style={{ minWidth: 640 }}>
            <thead>
              <tr><th>#</th><th>Category</th><th>Key</th><th>Records</th><th>Status</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {categories.map((c, i) => (
                <tr key={c.id} onClick={() => onOpenCategory(c)} style={{ cursor: 'pointer' }}>
                  <td style={{ color: 'var(--text-dim)' }}>{i + 1}</td>
                  <td style={{ fontWeight: 600 }}>{c.icon} {c.name}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>{c.key}</td>
                  <td><span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{c.record_count}</span></td>
                  <td><span className="badge" style={{ background: c.status === 'ACTIVE' ? 'rgba(16,185,129,0.12)' : 'rgba(245,158,11,0.12)', color: c.status === 'ACTIVE' ? '#34d399' : '#fbbf24', border: `1px solid ${c.status === 'ACTIVE' ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}` }}>{c.status}</span></td>
                  <td onClick={e => e.stopPropagation()}>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button className="btn-secondary" style={{ padding: '5px 10px', fontSize: '0.78rem' }} title="Open" onClick={() => onOpenCategory(c)}><Eye size={13} /></button>
                      <button className="btn-secondary" style={{ padding: '5px 10px', fontSize: '0.78rem' }} title="Edit" onClick={() => { setEditing(c); setShowModal(true); }}><Edit2 size={13} /></button>
                      <button className="btn-secondary" style={{ padding: '5px 10px', fontSize: '0.78rem' }} title={c.status === 'ACTIVE' ? 'Disable' : 'Enable'} onClick={() => toggleStatus(c)}><Power size={13} /></button>
                      <button className="btn-danger" style={{ padding: '5px 10px' }} title="Delete" onClick={() => handleDelete(c)}><Trash2 size={13} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(showModal || editing) && (
        <CategoryModal
          category={editing}
          onSave={handleSave}
          onClose={() => { setShowModal(false); setEditing(null); }}
        />
      )}
    </div>
  );
}
