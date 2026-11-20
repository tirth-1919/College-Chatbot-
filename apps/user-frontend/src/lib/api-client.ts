import {
  AUTH_SESSION_INVALID_KEY,
  AuthSessionTokens,
  markAuthSessionInvalid,
  persistAuthSession,
} from "@/lib/auth-session";

function getApiBase(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  if (typeof window !== "undefined" && window.location.hostname === "127.0.0.1") {
    return envUrl.replace("localhost", "127.0.0.1");
  }
  return envUrl;
}

let refreshInFlight: Promise<boolean> | null = null;

function isAuthEndpoint(endpoint: string): boolean {
  const path = endpoint.split("?")[0];
  return path === "/auth/login" || path === "/auth/register" || path === "/auth/refresh";
}

async function refreshAccessToken(expectedAccessToken: string): Promise<boolean> {
  if (typeof window === "undefined") return false;
  if (localStorage.getItem("auth_token") !== expectedAccessToken) return false;
  if (localStorage.getItem(AUTH_SESSION_INVALID_KEY)) return false;

  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) {
    markAuthSessionInvalid();
    return false;
  }

  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const response = await fetch(`${getApiBase()}/auth/refresh`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Request-ID": createRequestId(),
          },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        const envelope = await response.json().catch(() => null);
        const tokens = envelope?.data as AuthSessionTokens | undefined;

        if (
          response.ok &&
          envelope?.success === true &&
          typeof tokens?.access_token === "string" &&
          tokens.access_token.length > 0 &&
          typeof tokens.refresh_token === "string" &&
          tokens.refresh_token.length > 0
        ) {
          if (localStorage.getItem("auth_token") !== expectedAccessToken) return false;
          const cachedProfile = localStorage.getItem("user_profile");
          if (cachedProfile && tokens.user_id) {
            try {
              const profile = JSON.parse(cachedProfile);
              if (profile.id && profile.id !== tokens.user_id) {
                markAuthSessionInvalid();
                return false;
              }
            } catch {
              markAuthSessionInvalid();
              return false;
            }
          }
          persistAuthSession(tokens);
          return true;
        }

        if (response.status === 401 || response.status === 403 || response.ok) {
          markAuthSessionInvalid();
        }
        return false;
      } catch {
        return false;
      }
    })().finally(() => {
      refreshInFlight = null;
    });
  }

  return refreshInFlight;
}

function createRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (character) => {
    const random = Math.floor(Math.random() * 16);
    const value = character === "x" ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<{
  success: boolean;
  message?: string;
  data?: T;
  error?: string;
  status?: number;
  requestId?: string;
}> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const collegeId = typeof window !== "undefined" ? localStorage.getItem("selected_college_id") : null;
  const publicAuthEndpoint = isAuthEndpoint(endpoint);

  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  if (token && !publicAuthEndpoint) {
    headers.set("Authorization", `Bearer ${token}`);
  } else if (publicAuthEndpoint) {
    headers.delete("Authorization");
  }
  if (collegeId && !headers.has("X-College-ID")) {
    headers.set("X-College-ID", collegeId);
  }
  const requestId = headers.get("X-Request-ID") || createRequestId();
  headers.set("X-Request-ID", requestId);

  if (
    typeof window !== "undefined" &&
    !publicAuthEndpoint &&
    localStorage.getItem(AUTH_SESSION_INVALID_KEY)
  ) {
    return {
      success: false,
      error: "Your session is no longer valid. Sign in again before continuing.",
      status: 401,
      requestId,
    };
  }

  try {
    const requestOptions: RequestInit = {
      ...options,
      headers,
    };
    let res = await fetch(`${getApiBase()}${endpoint}`, requestOptions);
    if (res.status === 401 && token && !publicAuthEndpoint) {
      const refreshed = await refreshAccessToken(token);
      if (refreshed) {
        const updatedToken = localStorage.getItem("auth_token");
        if (updatedToken) {
          headers.set("Authorization", `Bearer ${updatedToken}`);
          res = await fetch(`${getApiBase()}${endpoint}`, requestOptions);
        }
      }
    }

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return {
        success: false,
        error: data.detail || data.message || "An error occurred during the request.",
        status: res.status,
        requestId: data.request_id || res.headers.get("X-Request-ID") || requestId,
      };
    }
    return data;
  } catch (err: any) {
    return {
      success: false,
      error: err.message || "Network error. Failed to reach backend API.",
      requestId,
    };
  }
}

