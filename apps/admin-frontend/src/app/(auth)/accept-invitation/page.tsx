"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { adminApiRequest } from "@/lib/api-client";
import {
  ShieldCheck,
  Building2,
  Lock,
  User,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  Sparkles,
} from "lucide-react";

function AcceptInvitationContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isSignedIn, setIsSignedIn] = useState(false);

  const [inviteInfo, setInviteInfo] = useState<{
    college_name: string;
    email: string;
    full_name: string;
    role_in_college: string;
  } | null>(null);

  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  useEffect(() => {
    async function verifyToken() {
      setIsSignedIn(Boolean(localStorage.getItem("admin_auth_token")));
      if (!token) {
        setError("Missing invitation token. Please check your invitation link.");
        setLoading(false);
        return;
      }

      try {
        const res = await adminApiRequest<any>(`/auth/invitations/${token}`);
        if (res.success && res.data) {
          setInviteInfo({
            college_name: res.data.college_name || "Assigned Institution",
            email: res.data.email,
            full_name: res.data.full_name,
            role_in_college: res.data.role_in_college || "ADMIN",
          });
          setFullName(res.data.full_name || "");
        } else {
          setError(res.error || "This invitation is invalid, expired, or already used.");
        }
      } catch (verificationError) {
        setError(
          verificationError instanceof Error
            ? verificationError.message
            : "Unable to verify this invitation."
        );
      } finally {
        setLoading(false);
      }
    }
    verifyToken();
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isSignedIn) {
      if (!password || password.length < 8) {
        setError("Password must be at least 8 characters.");
        return;
      }
      if (password !== confirmPassword) {
        setError("Passwords do not match.");
        return;
      }
    }

    setSubmitting(true);
    setError(null);

    try {
      const res = await adminApiRequest<any>("/auth/accept-invitation", {
        method: "POST",
        body: JSON.stringify({
          invitation_token: token,
          full_name: fullName,
          password: isSignedIn ? undefined : password,
        }),
      });

      if (res.success && res.data) {
        localStorage.setItem("admin_auth_token", res.data.access_token);
        if (res.data.college_id) {
          localStorage.setItem("admin_college_id", res.data.college_id);
        }
        setSuccess(true);
        setTimeout(() => {
          router.push("/college-admin/onboarding");
        }, 1500);
      } else {
        setError(res.error || "The invitation could not be accepted.");
      }
    } catch (acceptError) {
      setError(
        acceptError instanceof Error
          ? acceptError.message
          : "Failed to establish administrator account."
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0B0B0D] flex items-center justify-center text-xs text-[#A1A1AA]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-6 h-6 border-2 border-[#6366F1] border-t-transparent rounded-full animate-spin" />
          <span>Verifying administrator invitation token...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0B0B0D] py-12 px-4 sm:px-6 lg:px-8 flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="text-center mb-6">
          <div className="h-12 w-12 rounded-2xl bg-[#6366F1]/10 border border-[#6366F1]/30 flex items-center justify-center text-[#6366F1] mx-auto mb-3">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#F5F5F5]">
            Accept Administrator Invitation
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1 max-w-sm mx-auto">
            You have been granted institutional governance authority on AI FAQ Colleges Chatbot.
          </p>
        </div>

        <div className="p-8 rounded-2xl border border-[#2A2A30] bg-[#111114] shadow-2xl space-y-6">
          {/* Institutional Assignment Card */}
          {inviteInfo && (
            <div className="p-4 rounded-xl bg-[#1F1F23]/60 border border-[#2A2A30] text-xs space-y-2">
              <div className="flex items-center gap-2 text-[#818CF8] font-semibold">
                <Building2 className="h-4 w-4" />
                <span>{inviteInfo.college_name}</span>
              </div>
              <div className="text-[#A1A1AA] space-y-1 text-[11px]">
                <div>
                  Email: <span className="text-[#F5F5F5] font-mono">{inviteInfo.email}</span>
                </div>
                <div>
                  Role: <span className="text-[#10B981] font-semibold">{inviteInfo.role_in_college}</span>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="p-3 rounded-xl bg-[#EF4444]/10 border border-[#EF4444]/30 text-xs text-[#EF4444] flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success ? (
            <div className="p-4 rounded-xl bg-[#10B981]/10 border border-[#10B981]/30 text-xs text-[#10B981] text-center space-y-2">
              <CheckCircle2 className="h-6 w-6 mx-auto" />
              <div className="font-bold">Account Established Successfully!</div>
              <div className="text-[11px] text-[#A1A1AA]">
                Redirecting to your College Onboarding Wizard...
              </div>
            </div>
          ) : inviteInfo ? (
            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              {isSignedIn && (
                <p className="text-[#A1A1AA]">
                  Your signed-in account will be linked to this invitation.
                </p>
              )}
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1.5">Full Legal Name</label>
                <div className="relative">
                  <User className="absolute left-3.5 top-3 h-4 w-4 text-[#A1A1AA]" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Dr. R. K. Patel"
                    className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                  />
                </div>
              </div>

              {!isSignedIn && (
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1.5">Set Administrator Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-3 h-4 w-4 text-[#A1A1AA]" />
                    <input
                      type="password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Min 8 characters"
                      className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                    />
                  </div>
                </div>
              )}

              {!isSignedIn && (
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1.5">Confirm Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-3 h-4 w-4 text-[#A1A1AA]" />
                    <input
                      type="password"
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Re-enter password"
                      className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                    />
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="w-full py-2.5 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] text-white font-medium transition shadow-lg shadow-[#6366F1]/20 flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {submitting ? (
                  <span>Activating Account...</span>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    <span>Activate Administrator Account</span>
                  </>
                )}
              </button>
            </form>
          ) : null}

          <div className="text-center pt-2 text-xs text-[#A1A1AA]">
            Already have administrator credentials?{" "}
            <Link href="/login" className="text-[#818CF8] hover:underline font-medium">
              Sign In &rarr;
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AcceptInvitationPage() {
  return (
    <Suspense fallback={<div className="p-12 text-center text-xs text-[#A1A1AA]">Loading invitation...</div>}>
      <AcceptInvitationContent />
    </Suspense>
  );
}

