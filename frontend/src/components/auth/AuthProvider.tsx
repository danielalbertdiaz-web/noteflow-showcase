"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  isAuthenticated,
  clearTokens,
  setTokens,
  getCachedUser,
  setCachedUser,
} from "@/lib/auth";
import { authApi } from "@/lib/api";
import type { User, AuthTokens } from "@/types";

interface AuthContextValue {
  isAuthenticated: boolean;
  user: Partial<User> | null;
  loading: boolean;
  login: (tokens: AuthTokens) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState(false);
  const [user, setUser] = useState<Partial<User> | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const freshUser = await authApi.getMe();
      setUser(freshUser);
      setCachedUser(freshUser);
    } catch {
      // stale token — interceptor will handle redirect
    }
  }, []);

  useEffect(() => {
    const auth = isAuthenticated();
    setAuthenticated(auth);
    if (auth) {
      const cached = getCachedUser();
      if (cached) setUser(cached);
      refreshUser().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [refreshUser]);

  const login = useCallback(
    async (tokens: AuthTokens) => {
      setTokens(tokens);
      setAuthenticated(true);
      await refreshUser();
      router.push("/dashboard");
    },
    [router, refreshUser]
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // best-effort
    } finally {
      clearTokens();
      setAuthenticated(false);
      setUser(null);
      router.push("/login");
    }
  }, [router]);

  return (
    <AuthContext.Provider
      value={{ isAuthenticated: authenticated, user, loading, login, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext must be used within AuthProvider");
  return ctx;
}
