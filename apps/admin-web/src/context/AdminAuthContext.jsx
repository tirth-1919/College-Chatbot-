import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { adminApi } from '../services/adminApi';

const AdminAuthContext = createContext(null);

export function AdminAuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mfaChallenge, setMfaChallenge] = useState(null); // { tempToken }

  useEffect(() => {
    const handleAuthExpired = () => setUser(null);
    window.addEventListener('ait-admin-auth-expired', handleAuthExpired);
    const token = adminApi.loadToken();
    if (token) {
      adminApi.getProfile()
        .then(profile => setUser(profile))
        .catch(() => { adminApi.setToken(null); })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
    return () => window.removeEventListener('ait-admin-auth-expired', handleAuthExpired);
  }, []);

  const login = useCallback(async (email, password, totpCode = null) => {
    const res = await adminApi.login(email, password, totpCode);
    if (res.mfa_required) {
      setMfaChallenge({ tempToken: res.temp_token });
      return { mfaRequired: true };
    }
    adminApi.setSession(res);
    setUser(res.user);
    setMfaChallenge(null);
    return { mfaRequired: false, user: res.user };
  }, []);

  const completeMfa = useCallback(async (totpCode) => {
    if (!mfaChallenge) throw new Error('No MFA challenge active');
    try {
      const res = await adminApi.verifyMfa(mfaChallenge.tempToken, totpCode);
      adminApi.setSession(res);
      setUser(res.user);
      setMfaChallenge(null);
    } catch (error) {
      // A challenge token is intentionally short-lived and becomes invalid after
      // a backend restart/secret rotation. Do not keep retrying a stale token.
      if (error.message.toLowerCase().includes('challenge') || error.message.includes('401')) {
        setMfaChallenge(null);
        throw new Error('Your MFA challenge expired or is invalid. Please sign in again.');
      }
      throw error;
    }
  }, [mfaChallenge]);

  const cancelMfa = useCallback(() => {
    setMfaChallenge(null);
  }, []);

  const logout = useCallback(async () => {
    try { await adminApi.logout(); } catch {}
    adminApi.clearSession();
    setUser(null);
    setMfaChallenge(null);
  }, []);

  const refreshProfile = useCallback(async () => {
    try {
      const profile = await adminApi.getProfile();
      setUser(profile);
      return profile;
    } catch {
      return null;
    }
  }, []);

  return (
    <AdminAuthContext.Provider value={{ user, loading, mfaChallenge, login, completeMfa, cancelMfa, logout, refreshProfile, setUser }}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export const useAdminAuth = () => useContext(AdminAuthContext);
