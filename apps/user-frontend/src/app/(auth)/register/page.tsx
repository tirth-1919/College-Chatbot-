"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authService } from "@/services/auth-service";
import { User, Mail, Lock, AlertCircle, CheckCircle2, ArrowRight } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [agreeTerms, setAgreeTerms] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanEmail = email.trim();
    if (!cleanEmail || !cleanEmail.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }

    if (!password || password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    if (confirmPassword && password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    const resolvedName = fullName.trim() || cleanEmail.split("@")[0].replace(/[^a-zA-Z]/g, " ").trim() || "Student User";

    setLoading(true);

    const res = await authService.register({
      email: cleanEmail,
      password,
      full_name: resolvedName,
      role: "STUDENT",
    });

    if (res.success) {
      setSuccess(true);
      // Auto-login registered student
      const loginRes = await authService.login({ email: cleanEmail, password });
      setLoading(false);

      if (loginRes.success && loginRes.data) {
        setTimeout(() => {
          router.push("/chat");
        }, 800);
      } else {
        setTimeout(() => {
          router.push("/login");
        }, 1200);
      }
    } else {
      setLoading(false);
      setError(res.error || "Failed to create account. Please check your details.");
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-4rem)] px-4 py-8">
      <div className="w-full max-w-md p-8 rounded-2xl border border-[#2A2A30] bg-[#111114] shadow-2xl">
        <h2 className="text-2xl font-bold tracking-tight mb-2 text-center text-[#F5F5F5]">
          Create Student Account
        </h2>
        <p className="text-xs text-[#A1A1AA] text-center mb-6">
          Access verified knowledge on fees, admissions, and campus facilities
        </p>

        {error && (
          <div className="flex items-center gap-2 p-3 mb-6 rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/30 text-[#EF4444] text-xs">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="flex items-center gap-2 p-3 mb-6 rounded-lg bg-[#10B981]/10 border border-[#10B981]/30 text-[#10B981] text-xs">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>Account created successfully! Logging you in...</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">Full Name (Optional)</label>
            <div className="relative">
              <User className="absolute left-3.5 top-3 h-4 w-4 text-[#A1A1AA]" />
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g. Dharmik Vataliya"
                className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">Email Address *</label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-3 h-4 w-4 text-[#A1A1AA]" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="student@example.com"
                className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">Password *</label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-3 h-4 w-4 text-[#A1A1AA]" />
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (!confirmPassword) setConfirmPassword(e.target.value);
                }}
                placeholder="Minimum 8 characters"
                className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
              />
            </div>
          </div>

          <div className="flex items-start gap-2 pt-1">
            <input
              type="checkbox"
              id="terms"
              checked={agreeTerms}
              onChange={(e) => setAgreeTerms(e.target.checked)}
              className="mt-0.5 rounded border-[#2A2A30] text-[#6366F1] focus:ring-0 cursor-pointer"
            />
            <label htmlFor="terms" className="text-[11px] text-[#A1A1AA] cursor-pointer">
              I agree to the college platform terms of service and privacy policy.
            </label>
          </div>

          <button
            type="submit"
            disabled={loading || success}
            className="w-full py-2.5 px-4 rounded-lg bg-[#6366F1] hover:bg-[#4F46E5] text-white font-medium text-xs transition disabled:opacity-50 mt-2 flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-[#6366F1]/20"
          >
            {loading ? "Creating Account..." : "Create Account & Sign In"}
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-[#A1A1AA]">
          Already have an account?{" "}
          <Link href="/login" className="text-[#6366F1] hover:underline font-medium">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}
