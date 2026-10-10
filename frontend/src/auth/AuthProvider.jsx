import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AuthContext } from './AuthContext';
import { authService } from '../services/authService';
import { preferenceService } from '../services/preferenceService';
import { onUnauthorized } from '../services/apiClient';
import { SUPPORTED_LANGUAGES, setLanguage } from '../i18n';

/**
 * status:
 *  - 'loading'          session check in progress
 *  - 'authenticated'    backend confirmed the session
 *  - 'unauthenticated'  backend said there is no valid session
 *  - 'error'            session could NOT be verified (backend down etc.) - never treated as logged in
 */
export function AuthProvider({ children }) {
  const { i18n } = useTranslation();
  const [status, setStatus] = useState('loading');
  const [user, setUser] = useState(null);
  const [preferences, setPreferences] = useState(null);
  const [error, setError] = useState(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const statusRef = useRef(status);
  statusRef.current = status;

  const loadPreferences = useCallback(async () => {
    try {
      const prefs = await preferenceService.get();
      setPreferences(prefs);
      if (prefs.language && SUPPORTED_LANGUAGES.some((l) => l.code === prefs.language)) {
        setLanguage(prefs.language);
      }
    } catch {
      // Preferences are optional: endpoint may not exist yet. Local language setting still works.
      setPreferences(null);
    }
  }, []);

  const verifySession = useCallback(async (signal) => {
    setStatus('loading');
    setError(null);
    try {
      const u = await authService.getCurrentUser(signal);
      setUser(u);
      setStatus('authenticated');
      loadPreferences();
    } catch (err) {
      if (err?.code === 'ERR_CANCELED') return;
      setUser(null);
      if (err?.kind === 'unauthorized') {
        setStatus('unauthenticated');
      } else {
        setError(err);
        setStatus('error');
      }
    }
  }, [loadPreferences]);

  useEffect(() => {
    const controller = new AbortController();
    verifySession(controller.signal);
    return () => controller.abort();
  }, [verifySession]);

  // Any authenticated request that returns 401 means the session expired.
  useEffect(
    () =>
      onUnauthorized(() => {
        if (statusRef.current === 'authenticated') {
          setUser(null);
          setPreferences(null);
          setSessionExpired(true);
          setStatus('unauthenticated');
        }
      }),
    [],
  );

  // Keep the user's saved profile language in sync when they change language.
  useEffect(() => {
    const handler = (lng) => {
      if (statusRef.current === 'authenticated') {
        preferenceService.update({ language: lng }).catch(() => {});
      }
    };
    i18n.on('languageChanged', handler);
    return () => i18n.off('languageChanged', handler);
  }, [i18n]);

  const login = useCallback(
    async (credentials) => {
      await authService.login(credentials);
      // Do not trust the login response alone: confirm via the current-user endpoint.
      const u = await authService.getCurrentUser();
      setUser(u);
      setSessionExpired(false);
      setError(null);
      setStatus('authenticated');
      await loadPreferences();
      return u;
    },
    [loadPreferences],
  );

  const register = useCallback(
    async (details) => {
      await authService.register(details);
      // If the backend starts a session on registration, pick it up. Otherwise caller sends user to Login.
      try {
        const u = await authService.getCurrentUser();
        setUser(u);
        setStatus('authenticated');
        loadPreferences();
        return { autoLoggedIn: true };
      } catch {
        return { autoLoggedIn: false };
      }
    },
    [loadPreferences],
  );

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } finally {
      setUser(null);
      setPreferences(null);
      setSessionExpired(false);
      setStatus('unauthenticated');
    }
  }, []);

  const value = useMemo(
    () => ({
      status,
      user,
      preferences,
      error,
      sessionExpired,
      isAuthenticated: status === 'authenticated',
      login,
      register,
      logout,
      retry: () => verifySession(),
      clearSessionExpired: () => setSessionExpired(false),
    }),
    [status, user, preferences, error, sessionExpired, login, register, logout, verifySession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
