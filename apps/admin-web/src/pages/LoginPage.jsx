import { useState } from 'react';
import { useAdminAuth } from '../context/AdminAuthContext';
import { Shield, Lock, Eye, EyeOff, AlertCircle, KeyRound, Search } from 'lucide-react';

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
  const { login, completeMfa, cancelMfa, mfaChallenge } = useAdminAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
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
      padding: '24px 16px'
    }}>
      {mfaChallenge && (
        <MfaModal
          onSubmit={handleMfa}
          onCancel={() => { setError(''); cancelMfa(); }}
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

      <div style={{ position: 'relative', zIndex: 1, width: 440, maxWidth: '100%' }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{
            width: 68, height: 68, borderRadius: 16,
            background: 'linear-gradient(135deg, rgba(11,10,62,0.9), rgba(26,35,69,0.9))',
            border: '1px solid rgba(240,133,24,0.35)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px',
            boxShadow: '0 0 30px rgba(240,133,24,0.15)'
          }}>
            <img src="/ai-faq-college-chat-bot-icon.svg" alt="AI FAQ College Chat Bot logo" style={{ width: 36, height: 36, objectFit: 'contain' }} />
          </div>
          <h1 style={{ fontSize: '1.55rem', fontWeight: 800, marginBottom: 6, letterSpacing: '-0.02em', color: '#fff' }}>
            AI FAQ College Chat Bot
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Institutional Administration & Governance Portal
          </p>
        </div>

        {/* Login Card */}
        <div className="glass-card" style={{ padding: 32 }}>
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
                Admin Email / Username
              </label>
              <input
                id="admin-email"
                className="input-field"
                type="email"
                placeholder="admin@yourcollege.edu"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="username"
              />
            </div>

            <div style={{ marginBottom: 22 }}>
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
            marginTop: 24, paddingTop: 16, borderTop: '1px solid var(--border-subtle)',
            display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-dim)', fontSize: '0.75rem'
          }}>
            <Shield size={13} />
            <span>Multi-tenant security isolation, MFA, and automated audit trails active</span>
          </div>
        </div>
      </div>
    </div>
  );
}
