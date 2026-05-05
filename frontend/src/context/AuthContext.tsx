import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  ReactNode,
} from 'react';
import api from '../api/axios';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface User {
  id: number;
  email: string;
  username: string;
}

type SessionStatus = 'loading' | 'authenticated' | 'unauthenticated';

interface AuthContextValue {
  user: User | null;
  token: string | null;
  status: SessionStatus;          // 'loading' while /me is in flight
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  logout: (reason?: 'manual' | 'inactivity' | 'expired') => void;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const TOKEN_KEY = 'token';
const USER_KEY  = 'lumera_user';

const INACTIVITY_MS    = 10 * 60 * 1000;   // 10 minutes
const WARNING_BEFORE_MS =  1 * 60 * 1000;  // warn 1 min before

const ACTIVITY_EVENTS: (keyof WindowEventMap)[] = [
  'mousemove', 'mousedown', 'keydown',
  'touchstart', 'touchmove', 'scroll', 'click',
];

// ─── Context ─────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}

// ─── Provider ─────────────────────────────────────────────────────────────────

export function AuthProvider({ children, onInactivityWarning, onWarningDismiss }: {
  children: ReactNode;
  /** called when 1 minute of inactivity remains — show your warning modal */
  onInactivityWarning?: () => void;
  /** called when user moves again after the warning — hide your modal */
  onWarningDismiss?: () => void;
}) {
  const [user,   setUser]   = useState<User | null>(null);
  const [token,  setToken]  = useState<string | null>(null);
  const [status, setStatus] = useState<SessionStatus>('loading');

  // Inactivity timers
  const logoutTimer  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const warningTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const warningLive  = useRef(false);
  const lastActivity = useRef(Date.now());

  // ── Helpers ────────────────────────────────────────────────────────────────

  const clearTimers = useCallback(() => {
    if (logoutTimer.current)  clearTimeout(logoutTimer.current);
    if (warningTimer.current) clearTimeout(warningTimer.current);
    logoutTimer.current  = null;
    warningTimer.current = null;
  }, []);

  const logout = useCallback((reason: 'manual' | 'inactivity' | 'expired' = 'manual') => {
    clearTimers();
    warningLive.current = false;

    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
    setStatus('unauthenticated');

    // Soft redirect — works inside and outside React Router
    if (reason === 'inactivity') {
      window.location.replace('/login?reason=inactivity');
    } else if (reason === 'expired') {
      window.location.replace('/login?reason=expired');
    } else {
      window.location.replace('/login');
    }
  }, [clearTimers]);

  // ── Inactivity timer scheduling ───────────────────────────────────────────

  const scheduleInactivity = useCallback(() => {
    clearTimers();

    warningTimer.current = setTimeout(() => {
      warningLive.current = true;
      onInactivityWarning?.();
    }, INACTIVITY_MS - WARNING_BEFORE_MS);

    logoutTimer.current = setTimeout(() => {
      warningLive.current = false;
      logout('inactivity');
    }, INACTIVITY_MS);
  }, [clearTimers, logout, onInactivityWarning]);

  const resetInactivity = useCallback(() => {
    lastActivity.current = Date.now();
    if (warningLive.current) {
      warningLive.current = false;
      onWarningDismiss?.();
    }
    scheduleInactivity();
  }, [scheduleInactivity, onWarningDismiss]);

  // ── Login ─────────────────────────────────────────────────────────────────

  const login = useCallback((newToken: string, newUser: User) => {
    sessionStorage.setItem(TOKEN_KEY, newToken);
    sessionStorage.setItem(USER_KEY, JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
    setStatus('authenticated');
    // Inactivity timer starts once authenticated
  }, []);

  // ── Session restore on mount ───────────────────────────────────────────────
  // This is the fix for the production ghost-tab bug.
  // We never trust sessionStorage alone — we always validate with /me.

  useEffect(() => {
    const storedToken = sessionStorage.getItem(TOKEN_KEY);

    if (!storedToken) {
      setStatus('unauthenticated');
      return;
    }

    // Token exists — validate it against the backend
    api
      .get('/auth/me', {
        headers: { Authorization: `Bearer ${storedToken}` },
      })
      .then((res) => {
        const validatedUser: User = res.data.user ?? res.data;
        setToken(storedToken);
        setUser(validatedUser);
        sessionStorage.setItem(USER_KEY, JSON.stringify(validatedUser));
        setStatus('authenticated');
      })
      .catch(() => {
        // Token is invalid/expired on the server — clear everything silently
        sessionStorage.removeItem(TOKEN_KEY);
        sessionStorage.removeItem(USER_KEY);
        setStatus('unauthenticated');
        // No redirect here — ProtectedRoute will redirect to /login naturally
      });
  }, []); // runs once on mount

  // ── Inactivity listeners — only when authenticated ────────────────────────

  useEffect(() => {
    if (status !== 'authenticated') {
      clearTimers();
      return;
    }

    scheduleInactivity();

    const onActivity = () => resetInactivity();
    ACTIVITY_EVENTS.forEach((e) => window.addEventListener(e, onActivity, { passive: true }));

    // Handle tab becoming visible after being hidden
    const onVisibility = () => {
      if (document.visibilityState === 'visible') {
        const elapsed = Date.now() - lastActivity.current;
        if (elapsed >= INACTIVITY_MS) {
          clearTimers();
          logout('inactivity');
        } else {
          resetInactivity();
        }
      }
    };
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      clearTimers();
      ACTIVITY_EVENTS.forEach((e) => window.removeEventListener(e, onActivity));
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [status, scheduleInactivity, resetInactivity, clearTimers, logout]);

  // ── Intercept 401 responses globally ─────────────────────────────────────
  // Catches expired tokens that pass sessionStorage check but fail on server

  useEffect(() => {
    const id = api.interceptors.response.use(
      (res) => res,
      (err) => {
        if (err?.response?.status === 401 && status === 'authenticated') {
          logout('expired');
        }
        return Promise.reject(err);
      }
    );
    return () => api.interceptors.response.eject(id);
  }, [status, logout]);

  // ─────────────────────────────────────────────────────────────────────────

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        status,
        isAuthenticated: status === 'authenticated',
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}