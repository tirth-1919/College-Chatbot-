"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { adminApiRequest } from "@/lib/api-client";
import { Shield, Lock, Mail, AlertCircle, ArrowRight, UserCheck, Zap, Building2 } from "lucide-react";
import Link from "next/link";

function AdminLoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const autologinParam = searchParams.get("autologin");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoLoggingIn, setAutoLoggingIn] = useState<string | null>(null);

  const performLogin = async (targetEmail: string, targetPass: string) => {
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
        setAutoLoggingIn(null);
        return;
      }

      localStorage.setItem("admin_auth_token", res.data.access_token);
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

      const dest = res.data.role === "SUPER_ADMIN" ? "/super-admin/dashboard" : "/college-admin/dashboard";
      window.location.href = dest;
    } else {
      setError(res.error || "Administrative authentication failed.");
      setAutoLoggingIn(null);
    }
  };

  // Handle URL automatic login trigger
  useEffect(() => {
    if (!autologinParam) return;

    const lower = autologinParam.toLowerCase();
    if (lower === "collegeadmin" || lower === "ait" || lower === "college") {
      setAutoLoggingIn("College Administrator (AIT College)");
      setEmail("admin@aitindia.in");
      setPassword("Admin@12345");
      const t = setTimeout(() => performLogin("admin@aitindia.in", "Admin@12345"), 400);
      return () => clearTimeout(t);
    } else if (lower === "superadmin" || lower === "true" || lower === "1" || lower === "super") {
      setAutoLoggingIn("Global Super Administrator");
      setEmail("superadmin@platform.com");
      setPassword("Admin@12345");
      const t = setTimeout(() => performLogin("superadmin@platform.com", "Admin@12345"), 400);
      return () => clearTimeout(t);
    }
  }, [autologinParam]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    performLogin(email, password);
  };

  const quickFill = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    performLogin(demoEmail, demoPass);
  };

  return (
    <div className="flex items-center justify-center min-h-screen px-4 bg-[#0B0B0D]">
      <div className="w-full max-w-md p-8 rounded-2xl border border-[#2A2A30] bg-[#111114] shadow-2xl">
        <div className="h-12 w-12 rounded-xl bg-[#6366F1]/10 flex items-center justify-center text-[#6366F1] mx-auto mb-4">
          <Shield className="h-6 w-6" />
        </div>

        {/* Automatic Login Notification */}
        {autoLoggingIn && (
          <div className="mb-6 p-3.5 rounded-xl bg-[#6366F1]/20 border border-[#6366F1]/50 text-white flex items-center gap-3 animate-pulse">
            <Zap className="h-5 w-5 text-[#818CF8] shrink-0" />
            <div className="text-xs">
              <div className="font-semibold text-[#F5F5F5]">Automatic ID Login Active</div>
              <div className="text-[#A1A1AA] text-[11px]">Authenticating as {autoLoggingIn}...</div>
            </div>
          </div>
        )}

        <h2 className="text-2xl font-bold tracking-tight mb-2 text-center text-[#F5F5F5]">
          Administrative Sign In
        </h2>
        <p className="text-xs text-[#A1A1AA] text-center mb-6">
          Restricted access for College Administrators &amp; Global Super Admins
        </p>

        {error && (
          <div className="flex items-center gap-2 p-3 mb-6 rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/30 text-[#EF4444] text-xs">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* 1-Click Fast Auto-Login Action Cards */}
        <div className="space-y-2.5 mb-6">
          <button
            type="button"
            onClick={() => quickFill("superadmin@platform.com", "Admin@12345")}
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-[#6366F1] to-[#8B5CF6] hover:opacity-95 text-white text-xs font-semibold flex items-center justify-between transition shadow-lg shadow-[#6366F1]/20 cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 fill-current" />
              <span>Auto-Login: Global Super Admin</span>
            </div>
            <ArrowRight className="h-3.5 w-3.5 opacity-80" />
          </button>

          <button
            type="button"
            onClick={() => quickFill("admin@aitindia.in", "Admin@12345")}
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl bg-[#1F1F23] hover:bg-[#2A2A30] border border-[#2A2A30] text-[#F5F5F5] text-xs font-medium flex items-center justify-between transition cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-emerald-400" />
              <span>Auto-Login: College Admin (AIT College)</span>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono">
              College
            </span>
          </button>
        </div>

        <div className="relative flex py-2 items-center mb-4">
          <div className="flex-grow border-t border-[#2A2A30]"></div>
          <span className="flex-shrink mx-3 text-[11px] text-[#A1A1AA] uppercase tracking-wider font-mono">or manual credentials</span>
          <div className="flex-grow border-t border-[#2A2A30]"></div>
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
                placeholder="superadmin@platform.com"
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
    <Suspense fallback={<div className="min-h-screen bg-[#0B0B0D] flex items-center justify-center text-xs text-[#A1A1AA]">Loading...</div>}>
      <AdminLoginContent />
    </Suspense>
  );
}
