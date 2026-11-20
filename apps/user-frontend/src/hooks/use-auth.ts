"use client";

import { useState, useEffect } from "react";
import { User, AuthState } from "@/types/auth";
import { apiRequest } from "@/lib/api-client";
import {
  AUTH_SESSION_INVALID_KEY,
  clearAuthSession,
  markAuthSessionInvalid,
} from "@/lib/auth-session";

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,
  });

  useEffect(() => {
    const handleInvalidSession = () => {
      setState({ user: null, token: null, isAuthenticated: false, isLoading: false });
    };
    const handleUpdatedSession = () => {
      const currentToken = localStorage.getItem("auth_token");
      if (!currentToken || localStorage.getItem(AUTH_SESSION_INVALID_KEY)) {
        handleInvalidSession();
        return;
      }
      let user: User | null = null;
      try {
        const cached = localStorage.getItem("user_profile");
        user = cached ? JSON.parse(cached) : null;
      } catch (e) {}
      setState({ user, token: currentToken, isAuthenticated: true, isLoading: false });
    };
    window.addEventListener("auth-session-invalid", handleInvalidSession);
    window.addEventListener("auth-session-updated", handleUpdatedSession);

    const token = localStorage.getItem("auth_token");
    if (!token || localStorage.getItem(AUTH_SESSION_INVALID_KEY)) {
      setState({ user: null, token: null, isAuthenticated: false, isLoading: false });
      return () => {
        window.removeEventListener("auth-session-invalid", handleInvalidSession);
        window.removeEventListener("auth-session-updated", handleUpdatedSession);
      };
    }

    // 1. Instant hydration from cached profile if present
    const cachedUser = localStorage.getItem("user_profile");
    if (cachedUser) {
      try {
        const user = JSON.parse(cachedUser);
        setState({ user, token, isAuthenticated: true, isLoading: false });
      } catch (e) {}
    }

    // Refresh the profile; apiRequest renews an expired access token once.
    apiRequest<User>("/auth/me")
      .then((res) => {
        if (localStorage.getItem("auth_token") !== token) return;
        if (res.success && res.data) {
          localStorage.setItem("user_profile", JSON.stringify(res.data));
          setState({
            user: res.data,
            token,
            isAuthenticated: true,
            isLoading: false,
          });
        } else if (res.status === 401 || res.status === 403) {
          markAuthSessionInvalid();
          handleInvalidSession();
        } else {
          const cached = localStorage.getItem("user_profile");
          if (!cached) {
            setState({ user: null, token: null, isAuthenticated: false, isLoading: false });
          }
        }
      })
      .catch(() => {
        if (localStorage.getItem("auth_token") !== token) return;
        const cached = localStorage.getItem("user_profile");
        if (!cached) setState({ user: null, token: null, isAuthenticated: false, isLoading: false });
      });

    return () => {
      window.removeEventListener("auth-session-invalid", handleInvalidSession);
      window.removeEventListener("auth-session-updated", handleUpdatedSession);
    };
  }, []);

  const logout = () => {
    clearAuthSession();
    setState({ user: null, token: null, isAuthenticated: false, isLoading: false });
    window.location.href = "/login";
  };

  return { ...state, logout };
}

