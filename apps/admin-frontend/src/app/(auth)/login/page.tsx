"use client";

import React, { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { adminApiRequest } from "@/lib/api-client";
import { Shield, Lock, Mail, AlertCircle, ArrowRight, Zap } from "lucide-react";
import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";

function AdminLoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const autologinParam = searchParams.get("autologin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [autoLoggingIn, setAutoLoggingIn] = useState(false);

  const autoLoginConfig =
    autologinParam === "superadmin"
      ? { email: "superadmin@platform.com", password: "Admin@12345", label: "Super Admin" }
      : autologinParam === "collegeadmin" ||
          autologinParam === "college-admin" ||
          autologinParam === "admin" ||
          autologinParam === "true" ||
          autologinParam === "1"
        ? { email: "admin@aitindia.in", password: "Admin@12345", label: "College Admin" }
        : null;

  useEffect(() => {
    let cancelled = false;
    if (autoLoginConfig) {
      setCheckingSession(false);
      return () => {
        cancelled = true;
      };
    }

    const token = localStorage.getItem("admin_auth_token");

    if (!token) {
      setCheckingSession(false);
      return () => {
        cancelled = true;
      };
    }

    adminApiRequest<{
      id: string;
      email: string;
      full_name: string;
      role: string;
      is_verified: boolean;
      is_active: boolean;
    }>("/auth/me").then((res) => {
      if (cancelled) return;

      const user = res.data;
      if (res.success && user && (user.role === "COLLEGE_ADMIN" || user.role === "SUPER_ADMIN")) {
        let cachedUser: { id?: string; role?: string; college_id?: string | null } | null = null;
        try {
          const cachedValue = localStorage.getItem("admin_user");
          cachedUser = cachedValue ? JSON.parse(cachedValue) : null;
        } catch {
          cachedUser = null;
        }

        const collegeId =
          cachedUser?.id === user.id && cachedUser.role === user.role
            ? cachedUser.college_id
            : null;

        if (user.role === "COLLEGE_ADMIN" && !collegeId) {
          setError("Please sign in again to restore your college administrator session.");
          localStorage.removeItem("admin_auth_token");
          localStorage.removeItem("admin_refresh_token");
          localStorage.removeItem("admin_college_id");
          localStorage.removeItem("admin_user");
          setCheckingSession(false);
          return;
        }

        const adminUser = { ...user, college_id: collegeId };
        localStorage.setItem("admin_user", JSON.stringify(adminUser));
        if (collegeId) {
          localStorage.setItem("admin_college_id", collegeId);
        } else {
          localStorage.removeItem("admin_college_id");
        }
        router.replace(
          user.role === "SUPER_ADMIN"
            ? "/super-admin/dashboard"
            : "/college-admin/dashboard"
        );
        return;
      }

      const isNetworkError =
        res.error?.includes("Failed to reach") ||
        res.error?.includes("fetch") ||
        res.error?.includes("Network");
      if (isNetworkError) {
        setError("Unable to verify your existing session. Please try again or sign in.");
      } else {
        localStorage.removeItem("admin_auth_token");
        localStorage.removeItem("admin_refresh_token");
        localStorage.removeItem("admin_college_id");
        localStorage.removeItem("admin_user");
      }
      setCheckingSession(false);
    }).catch(() => {
      if (cancelled) return;
      setError("Unable to verify your existing session. Please try again or sign in.");
      setCheckingSession(false);
    });

    return () => {
      cancelled = true;
    };
  }, [router, autologinParam]);

  const performLogin = useCallback(async (targetEmail: string, targetPass: string) => {
    setError(null);
    setLoading(true);

    let res = await adminApiRequest<{
      access_token: string;
      refresh_token?: string;
      user_id: string;
      role: string;
      college_id?: string;
      full_name: string;
    }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: targetEmail, password: targetPass }),
    });

    setLoading(false);

    if (res.success && res.data) {
      if (res.data.role !== "COLLEGE_ADMIN" && res.data.role !== "SUPER_ADMIN") {
        setError("Access Denied: Regular students cannot access the Administration Portal.");
        return;
      }

      localStorage.setItem("admin_auth_token", res.data.access_token);
      localStorage.removeItem("admin_refresh_token");
      localStorage.removeItem("admin_college_id");
      localStorage.removeItem("admin_user");
      if (res.data.refresh_token) localStorage.setItem("admin_refresh_token", res.data.refresh_token);
      if (res.data.college_id) {
        localStorage.setItem("admin_college_id", res.data.college_id);
      }
      localStorage.setItem(
        "admin_user",
        JSON.stringify({
          id: res.data.user_id,
          email: targetEmail,
          full_name: res.data.full_name,
          role: res.data.role,
          college_id: res.data.college_id,
          is_verified: true,
          is_active: true,
        })
      );

      const dest =
        res.data.role === "SUPER_ADMIN"
          ? "/super-admin/dashboard"
          : "/college-admin/dashboard";
      router.replace(dest);
    } else {
      setError(res.error || "Administrative authentication failed.");
      setAutoLoggingIn(false);
    }
  }, [router]);

  useEffect(() => {
    if (!autoLoginConfig) return;

    setAutoLoggingIn(true);
    setEmail(autoLoginConfig.email);
    setPassword(autoLoginConfig.password);
    const timer = window.setTimeout(() => {
      void performLogin(autoLoginConfig.email, autoLoginConfig.password);
    }, 400);

    return () => window.clearTimeout(timer);
  }, [autoLoginConfig?.email, autoLoginConfig?.password, autoLoginConfig?.label, performLogin]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    performLogin(email, password);
  };

  const quickFill = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    void performLogin(demoEmail, demoPass);
  };

  if (checkingSession) {
    return (
      <div className="flex items-center justify-center min-h-screen px-4 bg-[#0B0B0D] text-xs text-[#A1A1AA]">
        Checking your administrative session...
      </div>
    );
  }

  return (
    <div className="relative flex items-center justify-center min-h-screen px-4 bg-[#0B0B0D]">
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>
      <div className="w-full max-w-md p-8 rounded-2xl border border-[#2A2A30] bg-[#111114] shadow-2xl">
        <div className="h-12 w-12 rounded-xl bg-[#6366F1]/10 flex items-center justify-center text-[#6366F1] mx-auto mb-4">
          <Shield className="h-6 w-6" />
        </div>

        <h2 className="text-2xl font-bold tracking-tight mb-2 text-center text-[#F5F5F5]">
          Administrative Sign In
        </h2>
        <p className="text-xs text-[#A1A1AA] text-center mb-6">
          Use the credentials issued for your College Administrator or Super Admin account.
        </p>

        {autoLoggingIn && (
          <div className="mb-6 p-3.5 rounded-xl bg-[#6366F1]/20 border border-[#6366F1]/50 text-white flex items-center gap-3 animate-pulse">
            <Zap className="h-5 w-5 text-[#818CF8] shrink-0" />
            <div className="text-xs">
              <div className="font-semibold text-[#F5F5F5]">Automatic ID Login Triggered</div>
              <div className="text-[#A1A1AA] text-[11px]">
                Signing in as {autoLoginConfig?.label} ({autoLoginConfig?.email})...
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-3 mb-6 rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/30 text-[#EF4444] text-xs">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 gap-2 mb-5">
          <button
            type="button"
            onClick={() => quickFill("admin@aitindia.in", "Admin@12345")}
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-[#6366F1] to-[#8B5CF6] hover:opacity-95 text-white text-xs font-semibold flex items-center justify-center gap-2 transition shadow-lg shadow-[#6366F1]/25 cursor-pointer disabled:opacity-50"
          >
            <Zap className="h-4 w-4 fill-current" />
            <span>Automatic College Admin Login</span>
          </button>
          <button
            type="button"
            onClick={() => quickFill("superadmin@platform.com", "Admin@12345")}
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl border border-[#6366F1]/50 bg-[#6366F1]/10 hover:bg-[#6366F1]/20 text-[#C7D2FE] text-xs font-semibold flex items-center justify-center gap-2 transition cursor-pointer disabled:opacity-50"
          >
            <Zap className="h-4 w-4" />
            <span>Automatic Super Admin Login</span>
          </button>
        </div>

        <div className="relative flex py-2 items-center mb-4">
          <div className="flex-grow border-t border-[#2A2A30]" />
          <span className="flex-shrink mx-3 text-[11px] text-[#A1A1AA] uppercase tracking-wider">
            or manual credentials
          </span>
          <div className="flex-grow border-t border-[#2A2A30]" />
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">Official Admin Email</label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-3 h-4 w-4 text-[#A1A1AA]" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@college.edu"
                className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">Admin Password</label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-3 h-4 w-4 text-[#A1A1AA]" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-lg bg-[#2A2A30] hover:bg-[#3F3F46] text-[#F5F5F5] text-xs font-semibold flex items-center justify-center gap-2 transition disabled:opacity-50 mt-2 cursor-pointer"
          >
            {loading ? "Authenticating Authority..." : "Sign In with Credentials"}
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        <div className="mt-5 pt-3 flex items-center justify-between border-t border-[#2A2A30]/50 text-[11px] text-[#A1A1AA]">
          <Link href="/register-college" className="text-[#6366F1] hover:underline font-medium">
            Register Institution
          </Link>
          <Link href="/registration-status" className="text-[#A1A1AA] hover:text-[#F5F5F5] transition">
            Check Status →
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function AdminLoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-[#0B0B0D] text-xs text-[#A1A1AA]">Loading...</div>}>
      <AdminLoginContent />
    </Suspense>
  );
}
