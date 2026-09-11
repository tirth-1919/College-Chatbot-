import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { adminApi } from '../services/adminApi';

const AdminAuthContext = createContext(null);

export function AdminAuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mfaChallenge, setMfaChallenge] = useState(null); // { tempToken }

  useEffect(() => {
    const token = adminApi.loadToken();
    if (token) {
      adminApi.getProfile()
        .then(profile => setUser(profile))
        .catch(() => { adminApi.setToken(null); })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (email, password, totpCode = null) => {
    const res = await adminApi.login(email, password, totpCode);
    if (res.mfa_required) {
      setMfaChallenge({ tempToken: res.temp_token });
      return { mfaRequired: true };
    }
    adminApi.setToken(res.access_token);
    setUser(res.user);
    setMfaChallenge(null);
    return { mfaRequired: false };
  }, []);

  const completeMfa = useCallback(async (totpCode) => {
    if (!mfaChallenge) throw new Error('No MFA challenge active');
    const res = await adminApi.verifyMfa(mfaChallenge.tempToken, totpCode);
    adminApi.setToken(res.access_token);
    setUser(res.user);
    setMfaChallenge(null);
  }, [mfaChallenge]);

  const logout = useCallback(() => {
    adminApi.setToken(null);
    setUser(null);
    setMfaChallenge(null);
  }, []);

  return (
    <AdminAuthContext.Provider value={{ user, loading, mfaChallenge, login, completeMfa, logout }}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export const useAdminAuth = () => useContext(AdminAuthContext);
