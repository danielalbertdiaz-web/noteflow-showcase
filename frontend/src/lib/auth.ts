import type { AuthTokens, User, Clinician } from "@/types";

const ACCESS_TOKEN_KEY = "noteflow_access_token";
const REFRESH_TOKEN_KEY = "noteflow_refresh_token";
const USER_KEY = "noteflow_user";

// ─── Token Storage ───────────────────────────────────────────

export function getTokens(): AuthTokens | null {
  if (typeof window === "undefined") return null;
  const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!accessToken || !refreshToken) return null;
  return {
    accessToken,
    refreshToken,
    tokenType: "bearer",
    expiresIn: 0,
  };
}

export function setTokens(tokens: AuthTokens): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

// ─── Auth State ──────────────────────────────────────────────

export function isAuthenticated(): boolean {
  const token = getAccessToken();
  if (!token) return false;
  try {
    const payload = parseJwt(token);
    if (!payload) return false;
    const now = Math.floor(Date.now() / 1000);
    return payload.exp > now;
  } catch {
    return false;
  }
}

// ─── JWT Parsing ─────────────────────────────────────────────

export interface JwtPayload {
  sub: string;
  email: string;
  role: string;
  clinician_id?: string;
  agency_id?: string;
  exp: number;
  iat: number;
  jti?: string;
}

export function parseJwt(token: string): JwtPayload | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(
      base64.length + ((4 - (base64.length % 4)) % 4),
      "="
    );
    const decoded = atob(padded);
    return JSON.parse(decoded) as JwtPayload;
  } catch {
    return null;
  }
}

export function getCurrentUser(): Partial<User> | null {
  const token = getAccessToken();
  if (!token) return null;
  const payload = parseJwt(token);
  if (!payload) return null;

  const user: Partial<User> = {
    id: payload.sub,
    email: payload.email,
    role: payload.role as User["role"],
  };

  if (payload.clinician_id) {
    user.clinician = { id: payload.clinician_id } as Clinician;
  }

  return user;
}

export function getTokenExpiresIn(): number {
  const token = getAccessToken();
  if (!token) return 0;
  const payload = parseJwt(token);
  if (!payload) return 0;
  const now = Math.floor(Date.now() / 1000);
  return Math.max(0, payload.exp - now);
}

// ─── User Cache ──────────────────────────────────────────────

export function getCachedUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function setCachedUser(user: User): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}
