import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { FileText, Upload, Trash2, ChevronDown } from 'lucide-react';

export default function DocumentsView() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [chunks, setChunks] = useState({});
  const fileRef = { current: null };

  const load = () => {
    setLoading(true);
    adminApi.getDocuments().then(setDocs).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    try {
      await adminApi.uploadDocument(file);
      load();
    } catch (err) {
      alert(err.message);
    } finally { setUploading(false); e.target.value = ''; }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this document and all its chunks?')) return;
    await adminApi.deleteDocument(id); load();
  };

  const loadChunks = async (id) => {
    if (chunks[id]) { setChunks(c => { const n={...c}; delete n[id]; return n; }); return; }
    const res = await adminApi.getDocumentChunks(id);
    setChunks(c => ({ ...c, [id]: res }));
  };

  return (
    <div>
      <div style={{ display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:22 }}>
        <div>
          <h1 style={{ fontSize:'1.4rem',fontWeight:800,marginBottom:4 }}>Document Management</h1>
          <p style={{ color:'var(--text-muted)',fontSize:'0.85rem' }}>RAG-indexed files · Automatic chunking and vector embedding</p>
        </div>
        <div>
          <input type="file" accept=".pdf,.doc,.docx,.txt,.md" onChange={handleUpload} style={{ display:'none' }} id="doc-upload" />
          <button className="btn-primary" onClick={() => document.getElementById('doc-upload').click()} disabled={uploading}>
            <Upload size={15} /> {uploading ? 'Uploading...' : 'Upload Document'}
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign:'center',padding:60,color:'var(--text-muted)' }}>
          <FileText size={28} style={{ opacity:0.4,marginBottom:10 }} /><div>Loading documents...</div>
        </div>
      ) : docs.length === 0 ? (
        <div className="glass-card" style={{ padding:48,textAlign:'center' }}>
          <Upload size={32} color="#f08518" style={{ marginBottom:12,opacity:0.6 }} />
          <div style={{ fontWeight:700,marginBottom:8 }}>No documents uploaded</div>
          <div style={{ color:'var(--text-muted)',fontSize:'0.875rem',marginBottom:20 }}>Upload PDFs, DOCXs, or text files to enable document-grounded responses</div>
          <label htmlFor="doc-upload" className="btn-primary" style={{ cursor:'pointer',display:'inline-flex',gap:8,padding:'10px 20px' }}>
            <Upload size={16} /> Upload Document
          </label>
        </div>
      ) : (
        <div style={{ display:'flex',flexDirection:'column',gap:12 }}>
          {docs.map(d => (
            <div key={d.id} className="glass-card" style={{ padding:18 }}>
              <div style={{ display:'flex',alignItems:'center',gap:14 }}>
                <div style={{ width:40,height:40,borderRadius:8,background:'rgba(99,102,241,0.12)',border:'1px solid rgba(99,102,241,0.25)',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0 }}>
                  <FileText size={18} color="#818cf8" />
                </div>
                <div style={{ flex:1 }}>
                  <div style={{ fontWeight:600,marginBottom:3 }}>{d.original_filename}</div>
                  <div style={{ display:'flex',gap:16,fontSize:'0.78rem',color:'var(--text-dim)',flexWrap:'wrap' }}>
                    <span>{(d.file_size_bytes/1024).toFixed(0)} KB</span>
                    <span>{d.chunk_count} chunks</span>
                    <span style={{ fontFamily:'var(--font-mono)' }}>{d.content_type}</span>
                    <span>{d.created_at ? new Date(d.created_at).toLocaleDateString() : '—'}</span>
                  </div>
                </div>
                <div style={{ display:'flex',gap:8,alignItems:'center' }}>
                  {d.chunk_count > 0 && (
                    <button className="btn-secondary" style={{ fontSize:'0.78rem',padding:'6px 12px' }} onClick={() => loadChunks(d.id)}>
                      <ChevronDown size={13} style={{ transform: chunks[d.id] ? 'rotate(180deg)' : 'none',transition:'transform 0.2s' }} />
                      {chunks[d.id] ? 'Hide' : 'Chunks'}
                    </button>
                  )}
                  <span className={`badge ${d.indexed ? 'badge-healthy' : 'badge-warning'}`} style={{ fontSize:'0.7rem' }}>
                    {d.indexed ? 'INDEXED' : 'PENDING'}
                  </span>
                  <button className="btn-danger" style={{ padding:'6px 12px' }} onClick={() => handleDelete(d.id)}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {chunks[d.id] && (
                <div style={{ marginTop:16,borderTop:'1px solid var(--border-subtle)',paddingTop:14 }}>
                  <div style={{ fontSize:'0.78rem',fontWeight:600,color:'var(--text-muted)',marginBottom:10 }}>
                    {chunks[d.id].length} CHUNKS
                  </div>
                  <div style={{ maxHeight:280,overflow:'auto',display:'flex',flexDirection:'column',gap:8 }}>
                    {chunks[d.id].map(c => (
                      <div key={c.id} style={{ padding:'10px 14px',borderRadius:8,background:'rgba(10,14,28,0.5)',border:'1px solid var(--border-subtle)' }}>
                        <div style={{ display:'flex',gap:12,marginBottom:6,fontSize:'0.72rem',color:'var(--text-dim)' }}>
                          <span>Chunk {c.chunk_index}</span>
                          <span>{c.chunk_size} chars</span>
                          {c.page_number && <span>Page {c.page_number}</span>}
                        </div>
                        <div style={{ fontSize:'0.82rem',color:'var(--text-muted)',lineHeight:1.5 }}>
                          {c.content_preview}
                        </div>
                      </div>
                    ))}
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
