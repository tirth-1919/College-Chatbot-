"use client";

import { useState, useEffect } from "react";
import { User, AuthState } from "@/types/auth";
import { apiRequest } from "@/lib/api-client";

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,
  });

  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (!token) {
      setState({ user: null, token: null, isAuthenticated: false, isLoading: false });
      return;
    }

    // 1. Instant hydration from cached profile if present
    const cachedUser = localStorage.getItem("user_profile");
    if (cachedUser) {
      try {
        const user = JSON.parse(cachedUser);
        setState({ user, token, isAuthenticated: true, isLoading: false });
      } catch (e) {}
    } else if (token.startsWith("demo_student_token_")) {
      setState({
        user: {
          id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
          email: "student@gmail.com",
          full_name: "Dharmik Vataliya",
          role: "STUDENT",
          is_verified: true,
          is_active: true,
        },
        token,
        isAuthenticated: true,
        isLoading: false,
      });
      return;
    }

    if (token.startsWith("demo_student_token_")) {
      return;
    }

    // 2. Refresh user profile from /auth/me in background
    apiRequest<User>("/auth/me")
      .then((res) => {
        if (res.success && res.data) {
          localStorage.setItem("user_profile", JSON.stringify(res.data));
          setState({
            user: res.data,
            token,
            isAuthenticated: true,
            isLoading: false,
          });
        } else {
          // If network error occurred, keep cached user
          const cached = localStorage.getItem("user_profile");
          if (!cached) {
            localStorage.removeItem("auth_token");
            setState({ user: null, token: null, isAuthenticated: false, isLoading: false });
          }
        }
      })
      .catch(() => {
        const cached = localStorage.getItem("user_profile");
        if (!cached) {
          localStorage.removeItem("auth_token");
          setState({ user: null, token: null, isAuthenticated: false, isLoading: false });
        }
      });
  }, []);

  const logout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_profile");
    localStorage.removeItem("selected_college_id");
    localStorage.removeItem("selected_college_name");
    setState({ user: null, token: null, isAuthenticated: false, isLoading: false });
    window.location.href = "/login";
  };

  return { ...state, logout };
}

