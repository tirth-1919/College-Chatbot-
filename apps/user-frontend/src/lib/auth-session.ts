export interface AuthSessionTokens {
  access_token: string;
  refresh_token?: string | null;
  user_id?: string;
  email?: string;
  full_name?: string;
  role?: string;
  college_id?: string | null;
  is_verified?: boolean;
}

export const AUTH_SESSION_INVALID_KEY = "auth_session_invalid";

export function persistAuthSession(tokens: AuthSessionTokens): void {
  if (typeof window === "undefined") return;

  localStorage.setItem("auth_token", tokens.access_token);
  if (tokens.refresh_token) {
    localStorage.setItem("refresh_token", tokens.refresh_token);
  } else {
    localStorage.removeItem("refresh_token");
  }
  localStorage.removeItem(AUTH_SESSION_INVALID_KEY);

  if (tokens.user_id && tokens.email && tokens.role) {
    localStorage.setItem(
      "user_profile",
      JSON.stringify({
        id: tokens.user_id,
        email: tokens.email,
        full_name: tokens.full_name || "",
        role: tokens.role,
        college_id: tokens.college_id || undefined,
        is_verified: Boolean(tokens.is_verified),
      })
    );
  }

  if (tokens.college_id) {
    const previousCollegeId = localStorage.getItem("selected_college_id");
    localStorage.setItem("selected_college_id", tokens.college_id);
    if (previousCollegeId !== tokens.college_id) {
      localStorage.removeItem("selected_college_name");
    }
  } else {
    localStorage.removeItem("selected_college_id");
    localStorage.removeItem("selected_college_name");
  }

  window.dispatchEvent(new Event("auth-session-updated"));
}

export function markAuthSessionInvalid(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("auth_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user_profile");
  localStorage.setItem(AUTH_SESSION_INVALID_KEY, "true");
  window.dispatchEvent(new Event("auth-session-invalid"));
}

export function clearAuthSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("auth_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem(AUTH_SESSION_INVALID_KEY);
  localStorage.removeItem("user_profile");
  localStorage.removeItem("selected_college_id");
  localStorage.removeItem("selected_college_name");
  window.dispatchEvent(new Event("auth-session-updated"));
}
