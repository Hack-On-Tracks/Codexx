import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import * as auth from '../services/authService';

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export const HOME = { admin: '/admin', rescue_manager: '/manager', rescue_member: '/member' };
export const ROLE_LABEL = { admin: 'Admin', rescue_manager: 'Rescue Operations Manager', rescue_member: 'Rescue Team Member' };

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    auth.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
    const expired = () => setUser(null);
    window.addEventListener('auth:expired', expired);
    return () => window.removeEventListener('auth:expired', expired);
  }, []);

  const signIn = useCallback(async (email, password) => { const r = await auth.login(email, password); setUser(r.user); return r.user; }, []);
  const signOut = useCallback(async () => { try { await auth.logout(); } finally { setUser(null); } }, []);

  return <Ctx.Provider value={{ user, loading, signIn, signOut }}>{children}</Ctx.Provider>;
}
