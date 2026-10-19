"use client";

import { useState, useEffect, useCallback } from "react";
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

interface UseAuthReturn {
  isAuthenticated: boolean;
  user: Partial<User> | null;
  loading: boolean;
  login: (tokens: AuthTokens) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

export function useAuth(): UseAuthReturn {
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
      // token may be stale - we'll let the interceptor handle it
    }
  }, []);

  useEffect(() => {
    const auth = isAuthenticated();
    setAuthenticated(auth);

    if (auth) {
      // Use cached user for immediate display, then refresh in background
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
      // best-effort logout
    } finally {
      clearTokens();
      setAuthenticated(false);
      setUser(null);
      router.push("/auth/login");
    }
  }, [router]);

  return {
    isAuthenticated: authenticated,
    user,
    loading,
    login,
    logout,
    refreshUser,
  };
}
