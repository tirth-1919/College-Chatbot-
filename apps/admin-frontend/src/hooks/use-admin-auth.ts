"use client";

import { useState, useEffect } from "react";
import { AdminUser, AdminAuthState } from "@/types/admin";
import { adminApiRequest } from "@/lib/api-client";

export function useAdminAuth() {
  const [state, setState] = useState<AdminAuthState>({
    admin: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,
  });

  useEffect(() => {
    const token = localStorage.getItem("admin_auth_token");
    if (!token) {
      setState({ admin: null, token: null, isAuthenticated: false, isLoading: false });
      return;
    }

    // Preload cached user profile for instant authentication without flicker
    let cachedUser: AdminUser | null = null;
    const cachedStr = localStorage.getItem("admin_user");
    if (cachedStr) {
      try {
        const parsed = JSON.parse(cachedStr);
        if (parsed && (parsed.role === "COLLEGE_ADMIN" || parsed.role === "SUPER_ADMIN")) {
          cachedUser = parsed;
        }
      } catch (e) {}
    }

    if (cachedUser) {
      setState({
        admin: cachedUser,
        token,
        isAuthenticated: true,
        isLoading: false,
      });
    }

    // 3. Verify / refresh active session from backend
    adminApiRequest<AdminUser>("/auth/me")
      .then((res) => {
        if (res.success && res.data && (res.data.role === "COLLEGE_ADMIN" || res.data.role === "SUPER_ADMIN")) {
          localStorage.setItem("admin_user", JSON.stringify(res.data));
          setState({
            admin: res.data,
            token,
            isAuthenticated: true,
            isLoading: false,
          });
        } else {
          // If error is network related, retain cached user session if available
          const isNetworkError = res.error?.includes("Failed to reach") || res.error?.includes("fetch") || res.error?.includes("Network");
          if (isNetworkError && cachedUser) {
            setState({
              admin: cachedUser,
              token,
              isAuthenticated: true,
              isLoading: false,
            });
            return;
          }

          // Genuine 401 / token invalidation
          localStorage.removeItem("admin_auth_token");
          localStorage.removeItem("admin_refresh_token");
          localStorage.removeItem("admin_college_id");
          localStorage.removeItem("admin_user");
          setState({ admin: null, token: null, isAuthenticated: false, isLoading: false });
        }
      })
      .catch(() => {
        if (cachedUser) {
          setState({
            admin: cachedUser,
            token,
            isAuthenticated: true,
            isLoading: false,
          });
        } else {
          setState({ admin: null, token: null, isAuthenticated: false, isLoading: false });
        }
      });
  }, []);

  const logout = () => {
    localStorage.removeItem("admin_auth_token");
    localStorage.removeItem("admin_refresh_token");
    localStorage.removeItem("admin_college_id");
    localStorage.removeItem("admin_user");
    setState({ admin: null, token: null, isAuthenticated: false, isLoading: false });
    window.location.href = "/login";
  };

  return { ...state, logout };
}

