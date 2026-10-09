import axios from "axios";

const TOKEN_KEY = "ulpf.token";

export const api = axios.create({
  baseURL: "/api",
});

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable - operate in-memory only */
  }
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401 && getToken()) {
      setToken(null);
      if (!location.pathname.startsWith("/login")) location.href = "/login";
    }
    return Promise.reject(error);
  },
);

export function apiError(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const d = e.response?.data as { detail?: unknown } | undefined;
    if (typeof d?.detail === "string") return d.detail;
    if (Array.isArray(d?.detail)) {
      return d.detail
        .map((x: any) => {
          const loc = Array.isArray(x.loc) ? x.loc.filter((p: string) => p !== "body").join(".") : "";
          return loc ? `${loc}: ${x.msg}` : (x.msg || JSON.stringify(x));
        })
        .join("; ");
    }
    if (typeof d === "object" && d !== null) {
      if ("message" in d && typeof (d as any).message === "string") return (d as any).message;
    }
    return e.message;
  }
  return String(e);
}
