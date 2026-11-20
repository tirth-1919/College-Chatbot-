function getApiBase(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  if (typeof window !== "undefined" && window.location.hostname === "127.0.0.1") {
    return envUrl.replace("localhost", "127.0.0.1");
  }
  return envUrl;
}

let refreshInFlight: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    const refreshToken = localStorage.getItem("admin_refresh_token");
    if (!refreshToken) return null;

    try {
      const response = await fetch(`${getApiBase()}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      const payload = await response.json();
      const data = payload?.data;
      if (!response.ok || !data?.access_token) return null;

      localStorage.setItem("admin_auth_token", data.access_token);
      if (data.refresh_token) localStorage.setItem("admin_refresh_token", data.refresh_token);
      return data.access_token;
    } catch {
      return null;
    }
  })();

  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

export async function adminApiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<{ success: boolean; message?: string; data?: T; error?: string }> {
  const token = typeof window !== "undefined" ? localStorage.getItem("admin_auth_token") : null;
  const collegeId = typeof window !== "undefined" ? localStorage.getItem("admin_college_id") : null;

  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const headers = new Headers(options.headers);
  if (!isFormData && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (collegeId) {
    headers.set("X-College-ID", collegeId);
  }

  const isAuthExchange = endpoint === "/auth/login" || endpoint === "/auth/refresh";
  const makeRequest = (accessToken: string | null) => {
    const requestHeaders = new Headers(headers);
    requestHeaders.delete("Authorization");
    if (accessToken && !isAuthExchange) requestHeaders.set("Authorization", `Bearer ${accessToken}`);
    return fetch(`${getApiBase()}${endpoint}`, { ...options, headers: requestHeaders });
  };

  try {
    let res = await makeRequest(token);
    if (res.status === 401 && token && !isAuthExchange && typeof window !== "undefined") {
      const refreshedToken = await refreshAccessToken();
      if (refreshedToken) {
        res = await makeRequest(refreshedToken);
      } else if (localStorage.getItem("admin_auth_token") === token) {
        // Do not let a delayed request from an older tab erase a newer login.
        localStorage.removeItem("admin_auth_token");
        localStorage.removeItem("admin_refresh_token");
        localStorage.removeItem("admin_college_id");
        localStorage.removeItem("admin_user");
      }
    }

    const contentType =
      typeof res.headers?.get === "function"
        ? res.headers.get("content-type") || ""
        : "";
    let data: any;
    if (typeof res.json === "function" && (contentType.includes("application/json") || typeof res.text !== "function")) {
      data = await res.json();
    } else if (typeof res.text === "function") {
      const text = await res.text();
      data = text ? { message: text } : null;
    } else if (typeof res.json === "function") {
      data = await res.json();
    } else {
      data = null;
    }

    if (!res.ok) {
      if (res.status === 404) {
        return {
          success: false,
          error: `API route not found (404): ${getApiBase()}${endpoint}. Make sure the backend API is running.`,
        };
      }
      const detail =
        typeof data?.detail === "string"
          ? data.detail
          : Array.isArray(data?.detail)
            ? data.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join("; ")
            : null;
      return {
        success: false,
        error: detail || data?.message || data?.error || "An administrative API error occurred.",
      };
    }
    if (!data || typeof data !== "object") {
      return {
        success: false,
        error: "The backend returned an invalid administrative API response.",
      };
    }
    return data;
  } catch (err: any) {
    return {
      success: false,
      error: err.message || "Failed to reach backend management API.",
    };
  }
}

