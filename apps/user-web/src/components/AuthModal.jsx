import React, { useState, useEffect } from 'react';
import { X, Mail, Lock, User as UserIcon, AlertCircle } from 'lucide-react';
import { apiClient } from '../services/api';

export function AuthModal({ isOpen, onClose, onAuthSuccess, onNavigateRegister }) {
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [oauthStatus, setOauthStatus] = useState(null);

  useEffect(() => {
    if (isOpen) {
      apiClient.getOAuthStatus().then(setOauthStatus).catch(() => {});
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let res;
      if (isSignup) {
        res = await apiClient.signup(email, password, fullName);
      } else {
        res = await apiClient.login(email, password);
      }
      onAuthSuccess(res.user);
      onClose();
    } catch (err) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 600 }}>
            {isSignup ? 'Create Student/Faculty Account' : 'Sign in to AI FAQ College Chat Bot'}
          </h2>
          <button className="item-action-icon" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {error && (
          <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#f87171', padding: '10px 14px', borderRadius: 'var(--radius-sm)', fontSize: '0.85rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {isSignup && (
            <div>
              <label style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Full Name</label>
              <div style={{ position: 'relative' }}>
                <UserIcon size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
                <input
                  type="text"
                  required
                  placeholder="e.g. Anjali Sharma"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px 10px 36px', background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', color: 'white' }}
                />
              </div>
            </div>
          )}

          <div>
            <label style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Email Address</label>
            <div style={{ position: 'relative' }}>
              <Mail size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
              <input
                type="email"
                required
                placeholder="name@example.com" 
                value={email} 
                onChange={(e) => setEmail(e.target.value)}
                style={{ width: '100%', padding: '10px 12px 10px 36px', background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', color: 'white' }}
              />
            </div>
          </div>

          <div>
            <label style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Password</label>
            <div style={{ position: 'relative' }}>
              <Lock size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
              <input 
                type="password" 
                required
                placeholder="••••••••" 
                value={password} 
                onChange={(e) => setPassword(e.target.value)}
                style={{ width: '100%', padding: '10px 12px 10px 36px', background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', color: 'white' }}
              />
            </div>
          </div>

          <button 
            type="submit" 
            disabled={loading}
            style={{ marginTop: '8px', padding: '12px', background: 'var(--text-main)', border: 'none', borderRadius: 'var(--radius-sm)', color: '#000000', fontWeight: 600, cursor: 'pointer' }}
          >
            {loading ? 'Please wait...' : (isSignup ? 'Sign Up' : 'Sign In')}
          </button>
        </form>

        {/* Google OAuth Section */}
        <div style={{ marginTop: '20px', borderTop: '1px solid var(--border-subtle)', paddingTop: '16px', textAlign: 'center' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginBottom: '10px' }}>
            {oauthStatus?.is_configured 
              ? 'Or continue with Google' 
              : 'Google OAuth: Not configured in environment (email/password active)'}
          </div>
          <button 
            type="button"
            disabled={!oauthStatus?.is_configured}
            style={{ width: '100%', padding: '10px', background: 'rgba(255, 255, 255, 0.05)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', color: oauthStatus?.is_configured ? 'white' : 'var(--text-dim)', cursor: oauthStatus?.is_configured ? 'pointer' : 'not-allowed', fontSize: '0.85rem' }}
          >
            Continue with Google
          </button>
        </div>

        <div style={{ marginTop: '16px', textAlign: 'center', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          {isSignup ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button 
            type="button"
            onClick={() => { setIsSignup(!isSignup); setError(''); }}
            style={{ background: 'none', border: 'none', color: 'var(--ait-accent)', cursor: 'pointer', fontWeight: 600 }}
          >
            {isSignup ? 'Sign In' : 'Create Account'}
          </button>
        </div>

        <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)', textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-dim)' }}>
          Representing an institution?{' '}
          <a
            href="/register-college"
            onClick={(e) => {
              e.preventDefault();
              if (onNavigateRegister) {
                onNavigateRegister();
              } else {
                window.location.href = '/register-college';
              }
            }}
            style={{ color: 'var(--ait-accent)', fontWeight: 600, textDecoration: 'none', cursor: 'pointer' }}
          >
            Register Your College →
          </a>
        </div>
      </div>
    </div>
  );
}
