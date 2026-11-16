"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authService } from "@/services/auth-service";
import { collegeService } from "@/services/college-service";
import { College } from "@/types/college";
import { User, Mail, Lock, Building2, AlertCircle, CheckCircle2, ArrowRight } from "lucide-react";

const DEFAULT_COLLEGES: College[] = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    name: "Ahmedabad Institute of Technology",
    slug: "ait-college",
    official_domain: "aitindia.in",
    logo_url: null,
    contact_email: "admissions@aitindia.in",
    contact_phone: "+91-79-27663244",
    status: "APPROVED",
    is_active: true,
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    name: "RC Technical Institute",
    slug: "rcti-college",
    official_domain: "rcti.cteguj.org",
    logo_url: null,
    contact_email: "info@rcti.cteguj.org",
    contact_phone: null,
    status: "APPROVED",
    is_active: true,
  },
  {
    id: "33333333-3333-3333-3333-333333333333",
    name: "Gujarat Technological University",
    slug: "gtu-ahmedabad",
    official_domain: "gtu.ac.in",
    logo_url: null,
    contact_email: "info@gtu.ac.in",
    contact_phone: null,
    status: "APPROVED",
    is_active: true,
  },
];

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [selectedCollegeId, setSelectedCollegeId] = useState("11111111-1111-1111-1111-111111111111");
  const [colleges, setColleges] = useState<College[]>(DEFAULT_COLLEGES);
  const [agreeTerms, setAgreeTerms] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    collegeService.getColleges(true).then((res) => {
      if (res.success && res.data && res.data.length > 0) {
        setColleges(res.data);
        setSelectedCollegeId(res.data[0].id);
      }
    });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanEmail = email.trim();
    if (!cleanEmail || !cleanEmail.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }

    if (!password || password.length < 6) {
      setError("Password must be at least 6 characters long.");
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
      college_id: selectedCollegeId,
    });

    if (res.success) {
      setSuccess(true);
      // Auto-login registered student
      const loginRes = await authService.login({ email: cleanEmail, password });
      setLoading(false);

      if (loginRes.success && loginRes.data) {
        localStorage.setItem("auth_token", loginRes.data.access_token);
        if (loginRes.data.college_id) {
          localStorage.setItem("selected_college_id", loginRes.data.college_id);
          const foundCollege = colleges.find((c) => c.id === loginRes.data?.college_id);
          if (foundCollege) {
            localStorage.setItem("selected_college_name", foundCollege.name);
          }
        }
        setTimeout(() => {
          router.push("/dashboard");
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
                minLength={6}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (!confirmPassword) setConfirmPassword(e.target.value);
                }}
                placeholder="Minimum 6 characters"
                className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">Select College Institution</label>
            <div className="relative">
              <Building2 className="absolute left-3.5 top-3 h-4 w-4 text-[#A1A1AA]" />
              <select
                value={selectedCollegeId}
                onChange={(e) => setSelectedCollegeId(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] text-xs focus:outline-none focus:border-[#6366F1] transition cursor-pointer"
              >
                {colleges.map((c) => (
                  <option key={c.id} value={c.id} className="bg-[#111114]">
                    {c.name}
                  </option>
                ))}
              </select>
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
