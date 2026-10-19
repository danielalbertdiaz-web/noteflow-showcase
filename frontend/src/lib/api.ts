import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";
import {
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
} from "@/lib/auth";
import type {
  AuthTokens,
  Note,
  NoteListResponse,
  NoteStatusResponse,
  CreateTextNoteRequest,
  UpdateNoteRequest,
  SOAPNote,
  User,
} from "@/types";

// ─── Snake → Camel Case Transform ───────────────────────────

function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
}

function transformKeys(obj: unknown): unknown {
  if (Array.isArray(obj)) return obj.map(transformKeys);
  if (obj !== null && typeof obj === 'object' && !(obj instanceof Date)) {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([k, v]) => [
        snakeToCamel(k),
        transformKeys(v),
      ])
    );
  }
  return obj;
}

// ─── Axios Instance ──────────────────────────────────────────

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Transform all response data from snake_case to camelCase
api.interceptors.response.use((response) => {
  if (response.data && typeof response.data === 'object') {
    response.data = transformKeys(response.data);
  }
  return response;
});

// Track in-progress refresh to avoid concurrent refresh storms
let isRefreshing = false;
let pendingRequests: Array<(token: string) => void> = [];

function onRefreshComplete(token: string) {
  pendingRequests.forEach((cb) => cb(token));
  pendingRequests = [];
}

// ─── Request Interceptor: attach JWT ────────────────────────

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ─── Response Interceptor: 401 refresh flow ─────────────────

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as AxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        clearTokens();
        if (typeof window !== "undefined") window.location.href = "/auth/login";
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          pendingRequests.push((token: string) => {
            if (originalRequest.headers) {
              (originalRequest.headers as Record<string, string>)[
                "Authorization"
              ] = `Bearer ${token}`;
            }
            resolve(api(originalRequest));
          });
          void reject;
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const tokens = await authApi.refreshToken(refreshToken);
        setTokens(tokens);
        onRefreshComplete(tokens.accessToken);
        if (originalRequest.headers) {
          (originalRequest.headers as Record<string, string>)[
            "Authorization"
          ] = `Bearer ${tokens.accessToken}`;
        }
        return api(originalRequest);
      } catch {
        clearTokens();
        pendingRequests = [];
        if (typeof window !== "undefined") window.location.href = "/auth/login";
        return Promise.reject(error);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// ─── Auth API ────────────────────────────────────────────────

export const authApi = {
  sendMagicLink: async (email: string): Promise<{ message: string }> => {
    const { data } = await api.post<{ message: string }>("/auth/login", {
      email,
    });
    return data;
  },

  verifyMagicLink: async (token: string): Promise<AuthTokens> => {
    const { data } = await api.post<AuthTokens>("/auth/verify", { token });
    return data;
  },

  refreshToken: async (refreshToken: string): Promise<AuthTokens> => {
    const { data } = await api.post<AuthTokens>("/auth/refresh", {
      refresh_token: refreshToken,
    });
    return data;
  },

  logout: async (): Promise<void> => {
    await api.post("/auth/logout");
  },

  getMe: async (): Promise<User> => {
    const { data } = await api.get<User>("/auth/me");
    return data;
  },
};

// ─── Notes API ───────────────────────────────────────────────

export const notesApi = {
  getNotes: async (params?: {
    page?: number;
    pageSize?: number;
    status?: string;
    visitType?: string;
    search?: string;
  }): Promise<NoteListResponse> => {
    const { data } = await api.get<NoteListResponse>("/notes", { params });
    return data;
  },

  getNote: async (id: string): Promise<Note> => {
    const { data } = await api.get<Note>(`/notes/${id}`);
    return data;
  },

  createVoiceNote: async (
    audioBlob: Blob,
    metadata: {
      patientId?: string;
      patientName?: string;
      visitDate: string;
      visitType: string;
    }
  ): Promise<Note> => {
    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.webm");
    formData.append("patient_name", metadata.patientName || "");
    formData.append("visit_date", metadata.visitDate);
    formData.append("visit_type", metadata.visitType);
    if (metadata.patientId) formData.append("patient_id", metadata.patientId);

    const { data } = await api.post<Note>("/notes/voice", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120000, // 2 min for large audio
    });
    return data;
  },

  createTextNote: async (payload: CreateTextNoteRequest): Promise<Note> => {
    const backendPayload = {
      patient_id: payload.patientId,
      patient_name: payload.patientName,
      visit_date: payload.visitDate,
      visit_type: payload.visitType,
      raw_input: payload.rawText, // Convert rawText to raw_input
    };
    const { data } = await api.post<Note>("/notes/text", backendPayload);
    return data;
  },

  updateNote: async (id: string, payload: UpdateNoteRequest): Promise<Note> => {
    const { data } = await api.put<Note>(`/notes/${id}`, payload);
    return data;
  },

  updateSOAPNote: async (id: string, soapNote: SOAPNote): Promise<Note> => {
    const { data } = await api.patch<Note>(`/notes/${id}/soap`, {
      structured_note: soapNote,
    });
    return data;
  },

  approveNote: async (id: string): Promise<Note> => {
    const { data } = await api.post<Note>(`/notes/${id}/approve`);
    return data;
  },

  submitToKinnser: async (id: string): Promise<Note> => {
    const { data } = await api.post<Note>(`/notes/${id}/submit`);
    return data;
  },

  getNoteStatus: async (id: string): Promise<NoteStatusResponse> => {
    const { data } = await api.get<NoteStatusResponse>(
      `/notes/${id}/status`
    );
    return data;
  },

  deleteNote: async (id: string): Promise<void> => {
    await api.delete(`/notes/${id}`);
  },

  getDashboardStats: async (): Promise<{
    totalNotes: number;
    pendingReview: number;
    submittedToday: number;
    processingNotes: number;
  }> => {
    const { data } = await api.get("/notes/stats/dashboard");
    return data;
  },
};

// ─── Users API ───────────────────────────────────────────────

export const usersApi = {
  getKinnserCredentials: async (): Promise<{
    kinnser_username: string | null;
    has_password: boolean;
  }> => {
    const { data } = await api.get("/users/me/kinnser-credentials");
    return data;
  },

  updateKinnserCredentials: async (
    username: string,
    password: string
  ): Promise<{ message: string }> => {
    const { data } = await api.put("/users/me/kinnser-credentials", {
      kinnser_username: username,
      kinnser_password: password,
    });
    return data;
  },
};

export default api;
