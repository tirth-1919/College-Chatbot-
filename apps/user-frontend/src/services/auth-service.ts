import { apiRequest } from "@/lib/api-client";
import { persistAuthSession } from "@/lib/auth-session";
import { User } from "@/types/auth";

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  role?: string;
  college_id?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in_minutes: number;
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  college_id?: string;
  is_verified: boolean;
}

export const authService = {
  async register(payload: RegisterPayload): Promise<{ success: boolean; data?: { user_id: string; email: string }; error?: string; message?: string }> {
    try {
      const res = await apiRequest<{ user_id: string; email: string }>("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (res.success && res.data) {
        return res;
      }
      return { success: false, error: res.error || "Registration failed." };
    } catch (e) {
      return {
        success: false,
        error: e instanceof Error ? e.message : "Registration service unavailable.",
      };
    }

    return { success: false, error: "Registration service unavailable." };
  },

  async login(payload: LoginPayload): Promise<{ success: boolean; data?: TokenResponse; error?: string }> {
    try {
      const res = await apiRequest<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (res.success && res.data) {
        persistAuthSession(res.data);
        return res;
      }
      return { success: false, error: res.error || "Invalid email or password." };
    } catch (e) {
      return {
        success: false,
        error: e instanceof Error ? e.message : "Authentication service unavailable.",
      };
    }

    return {
      success: false,
      error: "Authentication service unavailable. Please try again.",
    };
  },

  async getMe() {
    return apiRequest<User>("/auth/me");
  },

  async verifyEmail(email: string, token: string) {
    return apiRequest<boolean>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ email, token }),
    });
  },
};
