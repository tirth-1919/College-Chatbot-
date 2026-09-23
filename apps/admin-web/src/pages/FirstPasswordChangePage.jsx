import { useState } from 'react';
import { useAdminAuth } from '../context/AdminAuthContext';
import { adminApi } from '../services/adminApi';
import { Lock, KeyRound, Check, X, Eye, EyeOff, AlertCircle, ShieldCheck } from 'lucide-react';

export default function FirstPasswordChangePage() {
  const { user, refreshProfile, logout } = useAdminAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // Requirements validation
  const reqLength = newPassword.length >= 8;
  const reqUpper = /[A-Z]/.test(newPassword);
  const reqLower = /[a-z]/.test(newPassword);
  const reqNum = /[0-9]/.test(newPassword);
  const reqSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(newPassword);
  const passwordsMatch = newPassword.length > 0 && newPassword === confirmPassword;
  const isAllValid = reqLength && reqUpper && reqLower && reqNum && reqSpecial && passwordsMatch;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!isAllValid) {
      if (!passwordsMatch) {
        setError('New passwords do not match.');
      } else {
        setError('Please satisfy all password complexity criteria.');
      }
      return;
    }

    setLoading(true);
    try {
      await adminApi.changeFirstPassword(user?.email, currentPassword, newPassword);
      setSuccess(true);
      // Refresh profile to clear must_change_password flag
      setTimeout(async () => {
        await refreshProfile();
      }, 1200);
    } catch (err) {
      setError(err.message || 'Failed to update password. Please verify your current temporary password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'radial-gradient(ellipse 80% 60% at 50% -20%, rgba(11,10,62,0.85) 0%, transparent 70%), var(--bg-primary)',
      padding: '24px'
    }}>
      <div className="glass-card" style={{ width: '100%', maxWidth: 460, padding: '36px 32px' }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{
            width: 64, height: 64, borderRadius: 16,
            background: 'linear-gradient(135deg, rgba(240,133,24,0.2), rgba(240,133,24,0.05))',
            border: '1px solid rgba(240,133,24,0.4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px',
            boxShadow: '0 0 25px rgba(240,133,24,0.15)'
          }}>
            <KeyRound size={28} color="#f08518" />
          </div>
          <h1 style={{ fontSize: '1.45rem', fontWeight: 800, marginBottom: 8, letterSpacing: '-0.02em', color: '#fff' }}>
            Set Your Permanent Password
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', lineHeight: 1.5 }}>
            Welcome to AI FAQ College Chat Bot. For institutional security, you must update your temporary password before accessing your control center.
          </p>
        </div>

        {error && (
          <div style={{
            background: 'rgba(239,68,68,0.12)',
            border: '1px solid rgba(239,68,68,0.3)',
            borderRadius: 8,
            padding: '10px 14px',
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            color: '#fca5a5',
            fontSize: '0.85rem'
          }}>
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div style={{
            background: 'rgba(16,185,129,0.12)',
            border: '1px solid rgba(16,185,129,0.3)',
            borderRadius: 8,
            padding: '12px 16px',
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            color: '#34d399',
            fontSize: '0.9rem',
            fontWeight: 600
          }}>
            <ShieldCheck size={20} />
            <span>Password updated successfully! Entering dashboard...</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Current / Temporary Password
            </label>
            <div style={{ position: 'relative' }}>
              <input
                className="input-field"
                type={showCurrent ? 'text' : 'password'}
                placeholder="Enter temporary password"
                value={currentPassword}
                onChange={e => setCurrentPassword(e.target.value)}
                required
                style={{ paddingRight: 40 }}
              />
              <button
                type="button"
                onClick={() => setShowCurrent(v => !v)}
                style={{
                  position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
                  background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-dim)', padding: 0
                }}
              >
                {showCurrent ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              New Permanent Password
            </label>
            <div style={{ position: 'relative' }}>
              <input
                className="input-field"
                type={showNew ? 'text' : 'password'}
                placeholder="Create new permanent password"
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
                required
                style={{ paddingRight: 40 }}
              />
              <button
                type="button"
                onClick={() => setShowNew(v => !v)}
                style={{
                  position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
                  background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-dim)', padding: 0
                }}
              >
                {showNew ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* Password Requirements Checklist */}
          <div style={{
            background: 'rgba(0,0,0,0.25)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 8,
            padding: '12px 14px',
            marginBottom: 16,
            fontSize: '0.78rem'
          }}>
            <div style={{ color: 'var(--text-dim)', fontWeight: 600, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Password Requirements:
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 12px' }}>
              {[
                { label: 'Min 8 characters', met: reqLength },
                { label: '1 uppercase letter', met: reqUpper },
                { label: '1 lowercase letter', met: reqLower },
                { label: '1 number', met: reqNum },
                { label: '1 special character', met: reqSpecial },
              ].map((item, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 6, color: item.met ? '#34d399' : 'var(--text-dim)' }}>
                  {item.met ? <Check size={12} color="#34d399" /> : <X size={12} color="#64748b" />}
                  <span>{item.label}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: 24 }}>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Confirm New Password
            </label>
            <input
              className="input-field"
              type="password"
              placeholder="Confirm new permanent password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              required
              style={{
                borderColor: confirmPassword && !passwordsMatch ? '#ef4444' : (passwordsMatch ? '#10b981' : undefined)
              }}
            />
            {confirmPassword && !passwordsMatch && (
              <div style={{ fontSize: '0.75rem', color: '#fca5a5', marginTop: 4 }}>Passwords do not match</div>
            )}
          </div>

          <button
            type="submit"
            className="btn-primary"
            disabled={!isAllValid || loading || success}
            style={{
              width: '100%', justifyContent: 'center', padding: '12px 20px',
              fontSize: '0.95rem', fontWeight: 700
            }}
          >
            <Lock size={16} />
            {loading ? 'Updating Credentials...' : 'Update Password & Continue'}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: 18 }}>
          <button
            onClick={logout}
            style={{
              background: 'none', border: 'none', color: 'var(--text-dim)',
              fontSize: '0.8rem', cursor: 'pointer', textDecoration: 'underline'
            }}
          >
            Cancel & Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}
