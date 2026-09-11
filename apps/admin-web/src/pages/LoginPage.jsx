import { useState } from 'react';
import { useAdminAuth } from '../context/AdminAuthContext';
import { Shield, Lock, Eye, EyeOff, AlertCircle, KeyRound } from 'lucide-react';

function MfaModal({ onSubmit, onCancel, loading }) {
  const [code, setCode] = useState('');
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
    }}>
      <div className="glass-card" style={{ width: 360, padding: 32 }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div style={{
            width: 56, height: 56, borderRadius: '50%',
            background: 'rgba(240,133,24,0.15)', border: '1px solid rgba(240,133,24,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px'
          }}>
            <KeyRound size={24} color="#f08518" />
          </div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: 6 }}>Two-Factor Authentication</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Enter your 6-digit authenticator code to continue
          </p>
        </div>
        <input
          className="input-field"
          placeholder="000000"
          value={code}
          maxLength={6}
          onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
          style={{ textAlign: 'center', fontSize: '1.5rem', letterSpacing: '0.25em', marginBottom: 16 }}
          autoFocus
          onKeyDown={e => e.key === 'Enter' && code.length === 6 && onSubmit(code)}
        />
        <p style={{ color: 'var(--text-dim)', fontSize: '0.75rem', textAlign: 'center', marginBottom: 20 }}>
          Development mode: Use code <strong style={{ color: '#f08518' }}>123456</strong>
        </p>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn-secondary" style={{ flex: 1 }} onClick={onCancel}>Cancel</button>
          <button className="btn-primary" style={{ flex: 1 }} onClick={() => onSubmit(code)} disabled={code.length !== 6 || loading}>
            {loading ? 'Verifying...' : 'Verify'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  const { login, completeMfa, mfaChallenge } = useAdminAuth();
  const [email, setEmail] = useState('admin@aitindia.in');
  const [password, setPassword] = useState('Admin@AIT2026!');
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleMfa = async (code) => {
    setLoading(true);
    try {
      await completeMfa(code);
    } catch (err) {
      setError(err.message);
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
      background: 'radial-gradient(ellipse 80% 60% at 50% -20%, rgba(11,10,62,0.7) 0%, transparent 70%), var(--bg-primary)',
    }}>
      {mfaChallenge && (
        <MfaModal
          onSubmit={handleMfa}
          onCancel={() => setError('')}
          loading={loading}
        />
      )}

      {/* Background orbs */}
      <div style={{
        position: 'fixed', inset: 0, pointerEvents: 'none', overflow: 'hidden', zIndex: 0
      }}>
        <div style={{
          position: 'absolute', top: '-10%', left: '-5%',
          width: 500, height: 500, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(11,10,62,0.5) 0%, transparent 70%)',
          filter: 'blur(80px)'
        }} />
        <div style={{
          position: 'absolute', bottom: '-10%', right: '-5%',
          width: 400, height: 400, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(240,133,24,0.1) 0%, transparent 70%)',
          filter: 'blur(60px)'
        }} />
      </div>

      <div style={{ position: 'relative', zIndex: 1, width: 420 }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div style={{
            width: 72, height: 72, borderRadius: 16,
            background: 'linear-gradient(135deg, rgba(11,10,62,0.9), rgba(26,35,69,0.9))',
            border: '1px solid rgba(240,133,24,0.35)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 20px',
            boxShadow: '0 0 30px rgba(240,133,24,0.15)'
          }}>
            <Shield size={32} color="#f08518" />
          </div>
          <h1 style={{ fontSize: '1.65rem', fontWeight: 800, marginBottom: 8, letterSpacing: '-0.02em' }}>
            AIT Admin Control Center
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Authorized administrators only — Ahmedabad Institute of Technology
          </p>
        </div>

        {/* Login Card */}
        <div className="glass-card" style={{ padding: 36 }}>
          {error && (
            <div style={{
              background: 'rgba(239,68,68,0.1)',
              border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 8,
              padding: '10px 14px',
              marginBottom: 20,
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              color: '#fca5a5',
              fontSize: '0.875rem'
            }}>
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleLogin}>
            <div style={{ marginBottom: 18 }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Admin Email
              </label>
              <input
                id="admin-email"
                className="input-field"
                type="email"
                placeholder="admin@aitindia.in"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="username"
              />
            </div>

            <div style={{ marginBottom: 24 }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="admin-password"
                  className="input-field"
                  type={showPass ? 'text' : 'password'}
                  placeholder="••••••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  style={{ paddingRight: 44 }}
                />
                <button
                  type="button"
                  onClick={() => setShowPass(v => !v)}
                  style={{
                    position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-dim)', padding: 0
                  }}
                >
                  {showPass ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button
              id="admin-login-btn"
              type="submit"
              className="btn-primary"
              style={{ width: '100%', justifyContent: 'center', padding: '12px 20px', fontSize: '0.95rem' }}
              disabled={loading}
            >
              <Lock size={18} />
              {loading ? 'Authenticating...' : 'Sign In to Admin Panel'}
            </button>
          </form>

          <div style={{
            marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--border-subtle)',
            display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-dim)', fontSize: '0.8rem'
          }}>
            <Shield size={13} />
            <span>Multi-factor authentication, session tracking, and full audit logging active</span>
          </div>
        </div>

        <p style={{ textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.78rem', marginTop: 20 }}>
          Default: admin@aitindia.in / Admin@AIT2026! · 2FA code: 123456
        </p>
      </div>
    </div>
  );
}
