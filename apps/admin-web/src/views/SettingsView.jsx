import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { Settings, Code2, Flag, Save, Database, Plus, RefreshCw } from 'lucide-react';

function PromptEditor({ prompts, onSave }) {
  const [selectedSlug, setSelectedSlug] = useState(prompts[0]?.prompt_slug || '');
  const [draftContent, setDraftContent] = useState('');
  const [changeNote, setChangeNote] = useState('');
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  const selectedPrompt = prompts.find(p => p.prompt_slug === selectedSlug);

  useEffect(() => {
    if (selectedPrompt) setDraftContent(selectedPrompt.active_content || '');
  }, [selectedSlug, prompts]);

  const handleSave = async () => {
    setSaving(true); setSuccess(false);
    try {
      await onSave(selectedSlug, { content: draftContent, change_note: changeNote || 'Admin edit' });
      setSuccess(true); setChangeNote('');
    } finally { setSaving(false); }
  };

  return (
    <div className="glass-card" style={{ padding:22 }}>
      <div style={{ display:'flex',gap:12,marginBottom:16,alignItems:'center' }}>
        <Code2 size={18} color="#6366f1" />
        <span style={{ fontWeight:700,fontSize:'1rem' }}>System Prompt Editor</span>
      </div>
      <div style={{ display:'flex',gap:12,marginBottom:16 }}>
        <select className="input-field" style={{ flex:1 }} value={selectedSlug} onChange={e => setSelectedSlug(e.target.value)}>
          {prompts.map(p => <option key={p.id} value={p.prompt_slug}>{p.prompt_slug} (v{p.active_version_number})</option>)}
        </select>
        <input className="input-field" placeholder="Change note..." style={{ flex:1 }} value={changeNote} onChange={e => setChangeNote(e.target.value)} />
        <button className="btn-primary" onClick={handleSave} disabled={saving}>
          <Save size={15} /> {saving ? 'Saving...' : 'Save Version'}
        </button>
      </div>
      {success && <div style={{ color:'#34d399',fontSize:'0.85rem',marginBottom:10 }}>✓ Prompt version saved successfully</div>}
      <textarea
        className="input-field"
        style={{ fontFamily:'var(--font-mono)',minHeight:280,resize:'vertical',fontSize:'0.82rem',lineHeight:1.7 }}
        value={draftContent}
        onChange={e => setDraftContent(e.target.value)}
        spellCheck={false}
      />
      {selectedPrompt && (
        <div style={{ fontSize:'0.75rem',color:'var(--text-dim)',marginTop:8,display:'flex',gap:16 }}>
          <span>Active: v{selectedPrompt.active_version_number}</span>
          <span>Total versions: {selectedPrompt.version_count}</span>
          <span>Role: {selectedPrompt.required_role}</span>
        </div>
      )}
    </div>
  );
}

function FeatureFlags({ flags, onToggle }) {
  return (
    <div className="glass-card" style={{ padding:22 }}>
      <div style={{ display:'flex',gap:12,marginBottom:16,alignItems:'center' }}>
        <Flag size={18} color="#f08518" />
        <span style={{ fontWeight:700,fontSize:'1rem' }}>Feature Flags</span>
      </div>
      <div style={{ display:'flex',flexDirection:'column',gap:10 }}>
        {flags.map(f => (
          <div key={f.id} style={{
            display:'flex',alignItems:'center',gap:16,padding:'12px 16px',
            borderRadius:8,background:'rgba(255,255,255,0.03)',border:'1px solid var(--border-subtle)'
          }}>
            <div style={{ flex:1 }}>
              <div style={{ fontWeight:600,fontSize:'0.9rem',marginBottom:2 }}>{f.flag_key}</div>
              <div style={{ fontSize:'0.78rem',color:'var(--text-dim)' }}>{f.description}</div>
            </div>
            {f.current_value !== undefined && (
              <div style={{ fontSize:'0.78rem',color:'var(--text-muted)',fontFamily:'var(--font-mono)' }}>
                {typeof f.current_value === 'object' ? JSON.stringify(f.current_value).slice(0,40) : String(f.current_value)}
              </div>
            )}
            <button
              onClick={() => onToggle(f.flag_key, f.is_enabled)}
              style={{
                width:48, height:26, borderRadius:13, border:'none', cursor:'pointer',
                background: f.is_enabled ? '#f08518' : 'rgba(255,255,255,0.12)',
                position:'relative', transition:'background 0.2s', flexShrink:0
              }}
            >
              <div style={{
                position:'absolute', top:3, left: f.is_enabled ? 25 : 3,
                width:20, height:20, borderRadius:'50%', background:'white',
                transition:'left 0.2s', boxShadow:'0 1px 4px rgba(0,0,0,0.4)'
              }} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SettingsView() {
  const [prompts, setPrompts] = useState([]);
  const [flags, setFlags] = useState([]);
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [backupLoading, setBackupLoading] = useState(false);
  const [tab, setTab] = useState('prompts');

  const load = () => {
    setLoading(true);
    Promise.all([adminApi.getPrompts(), adminApi.getFeatureFlags(), adminApi.getBackups()])
      .then(([p, f, b]) => { setPrompts(p); setFlags(f); setBackups(b); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleSavePrompt = async (slug, data) => {
    await adminApi.addPromptVersion(slug, data);
    load();
  };

  const handleToggleFlag = async (key, isEnabled) => {
    await adminApi.toggleFlag(key, !isEnabled); load();
  };

  const handleBackup = async () => {
    setBackupLoading(true);
    try { await adminApi.createBackup(); load(); } finally { setBackupLoading(false); }
  };

  return (
    <div>
      <div style={{ display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:22 }}>
        <div>
          <h1 style={{ fontSize:'1.4rem',fontWeight:800,marginBottom:4 }}>Settings & Configuration</h1>
          <p style={{ color:'var(--text-muted)',fontSize:'0.85rem' }}>System prompts, feature flags, and database backups</p>
        </div>
        <button className="btn-secondary" onClick={load}><RefreshCw size={15} /> Refresh</button>
      </div>

      <div style={{ display:'flex',gap:4,marginBottom:20,background:'rgba(255,255,255,0.04)',borderRadius:10,padding:4,width:'fit-content' }}>
        {[{ key:'prompts', label:'Prompts', icon:Code2 },{ key:'flags', label:'Feature Flags', icon:Flag },{ key:'backups', label:'Backups', icon:Database }].map(({ key, label, icon: Icon }) => (
          <button key={key} onClick={() => setTab(key)} style={{
            padding:'8px 18px', borderRadius:8, border:'none', cursor:'pointer', fontFamily:'var(--font-sans)',
            background: tab===key ? 'rgba(240,133,24,0.15)' : 'transparent',
            color: tab===key ? '#f08518' : 'var(--text-muted)',
            fontWeight: tab===key ? 600 : 400,
            display:'flex', alignItems:'center', gap:8, fontSize:'0.875rem'
          }}><Icon size={15} />{label}</button>
        ))}
      </div>

      {loading ? (
        <div style={{ textAlign:'center',padding:60,color:'var(--text-muted)' }}><Settings size={28} style={{ opacity:0.4,marginBottom:10 }} /><div>Loading settings...</div></div>
      ) : tab === 'prompts' ? (
        prompts.length > 0 ? <PromptEditor prompts={prompts} onSave={handleSavePrompt} /> :
        <div className="glass-card" style={{ padding:40,textAlign:'center',color:'var(--text-muted)' }}>No prompts configured</div>
      ) : tab === 'flags' ? (
        <FeatureFlags flags={flags} onToggle={handleToggleFlag} />
      ) : (
        <div>
          <div style={{ display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16 }}>
            <span style={{ fontWeight:600 }}>{backups.length} backup snapshots</span>
            <button className="btn-primary" onClick={handleBackup} disabled={backupLoading}>
              <Database size={15} /> {backupLoading ? 'Creating...' : 'Create Backup'}
            </button>
          </div>
          <div className="data-table-container">
            <table className="data-table">
              <thead><tr><th>Name</th><th>Size</th><th>Status</th><th>Created</th><th>Location</th></tr></thead>
              <tbody>
                {backups.map(b => (
                  <tr key={b.id}>
                    <td style={{ fontFamily:'var(--font-mono)',fontSize:'0.8rem' }}>{b.backup_name}</td>
                    <td style={{ color:'var(--text-muted)',fontSize:'0.85rem' }}>{b.file_size_mb ? `${b.file_size_mb} MB` : '—'}</td>
                    <td><span className={`badge ${b.status==='COMPLETED'?'badge-healthy':b.status==='FAILED'?'badge-danger':'badge-warning'}`} style={{ fontSize:'0.7rem' }}>{b.status}</span></td>
                    <td style={{ color:'var(--text-dim)',fontSize:'0.8rem' }}>{b.created_at ? new Date(b.created_at).toLocaleString() : '—'}</td>
                    <td style={{ fontFamily:'var(--font-mono)',fontSize:'0.75rem',color:'var(--text-dim)',maxWidth:200,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap' }}>{b.file_path || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
