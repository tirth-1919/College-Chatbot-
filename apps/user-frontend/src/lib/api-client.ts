function getApiBase(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  if (typeof window !== "undefined" && window.location.hostname === "127.0.0.1") {
    return envUrl.replace("localhost", "127.0.0.1");
  }
  return envUrl;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<{ success: boolean; message?: string; data?: T; error?: string }> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const collegeId = typeof window !== "undefined" ? localStorage.getItem("selected_college_id") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (collegeId) {
    headers["X-College-ID"] = collegeId;
  }

  try {
    const res = await fetch(`${getApiBase()}${endpoint}`, {
      ...options,
      headers,
    });

    const data = await res.json();
    if (!res.ok) {
      return {
        success: false,
        error: data.detail || data.message || "An error occurred during the request.",
      };
    }
    return data;
  } catch (err: any) {
    return {
      success: false,
      error: err.message || "Network error. Failed to reach backend API.",
    };
  }
}

