import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { clearSession, loadSession, login as apiLogin } from "../api/client";
import type { AuthSession } from "../api/types";

interface AuthContextValue {
  session: AuthSession | null;
  signIn: (email: string, password: string) => Promise<AuthSession>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(() => loadSession());

  const signIn = useCallback(async (email: string, password: string) => {
    const next = await apiLogin(email, password);
    setSession(next);
    return next;
  }, []);

  const signOut = useCallback(() => {
    clearSession();
    setSession(null);
  }, []);

  const value = useMemo(() => ({ session, signIn, signOut }), [session, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
