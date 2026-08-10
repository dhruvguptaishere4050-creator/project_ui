import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { login as apiLogin, logout as apiLogout, refreshSession } from "../api/client";
import type { AuthSession } from "../api/types";

interface AuthContextValue {
  session: AuthSession | null;
  restoring: boolean;
  signIn: (email: string, password: string) => Promise<AuthSession>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [restoring, setRestoring] = useState(true);

  useEffect(() => {
    // Nothing is persisted in the browser, so a reload re-mints the access
    // token from the HttpOnly refresh cookie.
    refreshSession()
      .then(setSession)
      .catch(() => setSession(null))
      .finally(() => setRestoring(false));
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const next = await apiLogin(email, password);
    setSession(next);
    return next;
  }, []);

  const signOut = useCallback(() => {
    setSession(null);
    void apiLogout();
  }, []);

  const value = useMemo(
    () => ({ session, restoring, signIn, signOut }),
    [session, restoring, signIn, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
