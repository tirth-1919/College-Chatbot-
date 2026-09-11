import { useState, useEffect } from 'react';
import { adminApi } from '../services/adminApi';
import { Users, Search, Shield, UserCheck, UserX } from 'lucide-react';

const ROLES = ['ALL','STUDENT','ADMIN','SUPER_ADMIN'];

export default function UsersView() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('ALL');

  const load = () => {
    setLoading(true);
    const params = {};
    if (search) params.search = search;
    if (roleFilter !== 'ALL') params.role_filter = roleFilter;
    adminApi.getUsers(params).then(setUsers).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [search, roleFilter]);

  const handleRoleChange = async (id, currentRole) => {
    const role = prompt(`Change role (current: ${currentRole})\nOptions: STUDENT, ADMIN, SUPER_ADMIN`);
    if (!role) return;
    try {
      await adminApi.changeUserRole(id, role.toUpperCase());
      load();
    } catch (err) { alert(err.message); }
  };

  const handleToggleStatus = async (id, isActive) => {
    await adminApi.toggleUserStatus(id, !isActive); load();
  };

  const roleBadge = (role) => {
    const map = { SUPER_ADMIN: 'badge-danger', ADMIN: 'badge-ait', STUDENT: 'badge-neutral' };
    return <span className={`badge ${map[role] || 'badge-neutral'}`}>{role}</span>;
  };

  return (
    <div>
      <div style={{ display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:22 }}>
        <div>
          <h1 style={{ fontSize:'1.4rem',fontWeight:800,marginBottom:4 }}>User Management</h1>
          <p style={{ color:'var(--text-muted)',fontSize:'0.85rem' }}>{users.length} users · Role governance and account administration</p>
        </div>
      </div>

      <div style={{ display:'flex',gap:12,marginBottom:20 }}>
        <div style={{ position:'relative',flex:1,maxWidth:340 }}>
          <Search size={15} style={{ position:'absolute',left:12,top:'50%',transform:'translateY(-50%)',color:'var(--text-dim)',pointerEvents:'none' }} />
          <input className="input-field" placeholder="Search by name or email..." style={{ paddingLeft:38 }}
                 value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <select className="input-field" style={{ width:180 }} value={roleFilter} onChange={e => setRoleFilter(e.target.value)}>
          {ROLES.map(r => <option key={r} value={r}>{r === 'ALL' ? 'All Roles' : r}</option>)}
        </select>
      </div>

      {loading ? (
        <div style={{ textAlign:'center',padding:60,color:'var(--text-muted)' }}>
          <Users size={28} style={{ opacity:0.4,marginBottom:10 }} /><div>Loading users...</div>
        </div>
      ) : (
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr><th>Name</th><th>Email</th><th>Role</th><th>MFA</th><th>Status</th><th>Last Login</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id}>
                  <td style={{ fontWeight:600 }}>{u.full_name}</td>
                  <td style={{ color:'var(--text-muted)',fontSize:'0.85rem' }}>{u.email}</td>
                  <td>{roleBadge(u.role)}</td>
                  <td>
                    {u.mfa_enabled
                      ? <span className="badge badge-healthy" style={{ fontSize:'0.7rem' }}>2FA ON</span>
                      : <span className="badge badge-neutral" style={{ fontSize:'0.7rem' }}>—</span>}
                  </td>
                  <td>
                    {u.is_active
                      ? <span className="badge badge-healthy" style={{ fontSize:'0.7rem' }}>Active</span>
                      : <span className="badge badge-danger" style={{ fontSize:'0.7rem' }}>Disabled</span>}
                  </td>
                  <td style={{ color:'var(--text-dim)',fontSize:'0.8rem' }}>
                    {u.last_login_at ? new Date(u.last_login_at).toLocaleDateString() : 'Never'}
                  </td>
                  <td>
                    <div style={{ display:'flex',gap:6 }}>
                      <button className="btn-secondary" style={{ padding:'5px 12px',fontSize:'0.78rem' }}
                              onClick={() => handleRoleChange(u.id, u.role)}>
                        <Shield size={13} /> Role
                      </button>
                      <button
                        onClick={() => handleToggleStatus(u.id, u.is_active)}
                        style={{
                          padding:'5px 12px', borderRadius:6, border:'none', cursor:'pointer',
                          fontFamily:'var(--font-sans)', fontSize:'0.78rem', display:'flex', alignItems:'center', gap:5,
                          background: u.is_active ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)',
                          color: u.is_active ? '#f87171' : '#34d399'
                        }}
                      >
                        {u.is_active ? <UserX size={13} /> : <UserCheck size={13} />}
                        {u.is_active ? 'Disable' : 'Enable'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
