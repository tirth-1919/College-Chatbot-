import { useState, useEffect, useRef } from 'react';
import { adminApi } from '../services/adminApi';
import { Image as ImageIcon, Check, X, RefreshCw, Eye, Trash2, Shield } from 'lucide-react';

const CATEGORIES = ['all','campus','building','classroom','laboratory','library','sports','events','faculty','facilities','other'];

export default function ImagesView() {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState('all');
  const [syncing, setSyncing] = useState(false);
  const [preview, setPreview] = useState(null);

  const load = () => {
    setLoading(true);
    const params = {};
    if (category !== 'all') params.category = category;
    adminApi.getImages(params).then(setImages).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [category]);

  const handleSync = async () => {
    setSyncing(true);
    try { await adminApi.syncImages(); load(); } finally { setSyncing(false); }
  };

  const handleToggleVerify = async (id) => {
    await adminApi.toggleImageVerification(id); load();
  };

  const handleDelete = async (id) => {
    if (!confirm('Remove this image from the official repository?')) return;
    await adminApi.deleteImage(id); load();
  };

  return (
    <div>
      {preview && (
        <div style={{ position:'fixed',inset:0,background:'rgba(0,0,0,0.85)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:2000 }}
             onClick={() => setPreview(null)}>
          <div onClick={e => e.stopPropagation()} style={{ maxWidth:780,width:'90vw' }}>
            <img src={preview.image_url} alt={preview.title} style={{ width:'100%',borderRadius:12,maxHeight:'70vh',objectFit:'contain' }} onError={e => e.target.src='https://via.placeholder.com/600x400?text=AIT+Image'} />
            <div style={{ background:'rgba(10,15,35,0.95)',borderRadius:'0 0 12px 12px',padding:'14px 18px' }}>
              <div style={{ fontWeight:700,marginBottom:4 }}>{preview.title}</div>
              <div style={{ display:'flex',gap:12,fontSize:'0.78rem',color:'var(--text-muted)',flexWrap:'wrap' }}>
                <span>Category: {preview.category}</span>
                <span>Source: <a href={preview.source_url} target="_blank" rel="noopener noreferrer" style={{ color:'#f08518' }}>{preview.source_domain}</a></span>
                <span>Hash: {preview.content_hash?.slice(0,12)}…</span>
              </div>
            </div>
          </div>
        </div>
      )}

      <div style={{ display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:22 }}>
        <div>
          <h1 style={{ fontSize:'1.4rem',fontWeight:800,marginBottom:4 }}>Official Image Library</h1>
          <p style={{ color:'var(--text-muted)',fontSize:'0.85rem' }}>{images.length} images · college campus media with full provenance tracking</p>
        </div>
        <div style={{ display:'flex',gap:10 }}>
          <select className="input-field" style={{ width:180 }} value={category} onChange={e => setCategory(e.target.value)}>
            {CATEGORIES.map(c => <option key={c} value={c}>{c === 'all' ? 'All Categories' : c}</option>)}
          </select>
          <button className="btn-primary" onClick={handleSync} disabled={syncing}>
            <RefreshCw size={15} /> {syncing ? 'Syncing...' : 'Sync Images'}
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign:'center',padding:60,color:'var(--text-muted)' }}>
          <ImageIcon size={28} style={{ opacity:0.4,marginBottom:10 }} /><div>Loading image library...</div>
        </div>
      ) : (
        <div style={{ display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(220px,1fr))',gap:16 }}>
          {images.map(img => (
            <div key={img.id} className="glass-card" style={{ overflow:'hidden' }}>
              <div style={{ position:'relative',paddingTop:'65%',background:'rgba(10,14,28,0.6)',cursor:'pointer' }}
                   onClick={() => setPreview(img)}>
                <img
                  src={img.thumbnail_url || img.image_url}
                  alt={img.title}
                  onError={e => { e.target.onerror=null; e.target.src='https://via.placeholder.com/300x200?text=AIT'; }}
                  style={{ position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover' }}
                />
                <div style={{ position:'absolute',top:8,right:8,display:'flex',gap:6 }}>
                  <span className={`badge ${img.verified ? 'badge-healthy' : 'badge-warning'}`} style={{ fontSize:'0.65rem' }}>
                    {img.verified ? <><Shield size={9} /> VERIFIED</> : 'PENDING'}
                  </span>
                </div>
              </div>
              <div style={{ padding:'12px 14px' }}>
                <div style={{ fontWeight:600,fontSize:'0.85rem',marginBottom:4,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap' }}>{img.title}</div>
                <div style={{ fontSize:'0.72rem',color:'var(--text-dim)',marginBottom:10 }}>
                  {img.category} · {img.source_domain}
                </div>
                <div style={{ display:'flex',gap:6 }}>
                  <button className="btn-secondary" style={{ flex:1,padding:'5px 8px',fontSize:'0.75rem',justifyContent:'center' }}
                          onClick={() => setPreview(img)}>
                    <Eye size={13} />
                  </button>
                  <button
                    onClick={() => handleToggleVerify(img.id)}
                    style={{
                      flex:1, padding:'5px 8px', borderRadius:6, border:'none', cursor:'pointer', fontSize:'0.75rem',
                      fontFamily:'var(--font-sans)', display:'flex', alignItems:'center', justifyContent:'center', gap:4,
                      background: img.verified ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)',
                      color: img.verified ? '#f87171' : '#34d399'
                    }}
                  >
                    {img.verified ? <X size={13} /> : <Check size={13} />}
                    {img.verified ? 'Unverify' : 'Verify'}
                  </button>
                  <button className="btn-danger" style={{ padding:'5px 10px' }} onClick={() => handleDelete(img.id)}>
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
