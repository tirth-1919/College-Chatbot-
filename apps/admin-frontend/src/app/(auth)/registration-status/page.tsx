"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { adminApiRequest } from "@/lib/api-client";
import {
  Search,
  Building2,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Shield,
  Globe,
} from "lucide-react";

interface StatusRecord {
  id: string;
  college_id: string | null;
  college_name: string;
  slug: string;
  official_domain: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "SUSPENDED" | string;
  tracking_code: string;
  created_at: string;
  updated_at?: string;
  additional_info_requested?: string | null;
}

function RegistrationStatusContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("query") || "";

  const [query, setQuery] = useState(initialQuery);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<StatusRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (searchTerm: string) => {
    const q = searchTerm.trim();
    if (!q) return;

    setError(null);
    setLoading(true);
    setResult(null);

    try {
      const res = await adminApiRequest<StatusRecord>(
        `/colleges/onboarding/status?query=${encodeURIComponent(q)}`
      );
      if (!res.success || !res.data) {
        setError(res.error || "No application was found for that tracking code.");
        return;
      }
      setResult(res.data);
    } catch (searchError) {
      setError(
        searchError instanceof Error
          ? searchError.message
          : "Unable to retrieve application status. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialQuery) {
      handleSearch(initialQuery);
    }
  }, [initialQuery]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>APPROVED &amp; ACTIVE</span>
          </span>
        );
      case "UNDER_REVIEW":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30">
            <Clock className="h-3.5 w-3.5" />
            <span>UNDER REVIEW</span>
          </span>
        );
      case "ADDITIONAL_INFORMATION_REQUIRED":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <AlertTriangle className="h-3.5 w-3.5" />
            <span>ACTION REQUIRED</span>
          </span>
        );
      case "PENDING":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/30">
            <Clock className="h-3.5 w-3.5" />
            <span>PENDING VERIFICATION</span>
          </span>
        );
      case "REJECTED":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/30">
            <XCircle className="h-3.5 w-3.5" />
            <span>APPLICATION REJECTED</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-[#2A2A30] text-[#A1A1AA]">
            <AlertTriangle className="h-3.5 w-3.5" />
            <span>{status}</span>
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0B0D] py-12 px-4 sm:px-6 lg:px-8 flex items-center justify-center">
      <div className="w-full max-w-xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex h-12 w-12 rounded-2xl bg-[#6366F1]/10 border border-[#6366F1]/30 items-center justify-center text-[#6366F1] mb-3">
            <Shield className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#F5F5F5]">
            Application Status Tracker
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1 max-w-sm mx-auto">
            Check the review and verification status of your college onboarding application.
          </p>
        </div>

        {/* Tracker Box */}
        <div className="p-8 rounded-2xl border border-[#2A2A30] bg-[#111114] shadow-2xl mb-6">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSearch(query);
            }}
            className="flex gap-2 mb-6"
          >
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-3 h-4 w-4 text-[#A1A1AA]" />
              <input
                type="text"
                required
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Private registration tracking code"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="py-2.5 px-5 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] text-white text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50 shadow-lg shadow-[#6366F1]/20 cursor-pointer"
            >
              {loading ? "Searching..." : "Track Status"}
            </button>
          </form>

          {/* Error Message */}
          {error && (
            <div className="p-4 rounded-xl bg-[#EF4444]/10 border border-[#EF4444]/30 text-[#EF4444] text-xs leading-relaxed mb-4">
              {error}
            </div>
          )}

          {/* Status Result Card */}
          {result && (
            <div className="space-y-5 pt-2 border-t border-[#2A2A30]">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-base font-bold text-[#F5F5F5] flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-[#6366F1]" />
                    <span>{result.college_name}</span>
                  </h3>
                  <div className="flex items-center gap-3 text-xs text-[#A1A1AA] mt-1">
                    <span className="flex items-center gap-1 font-mono">
                      <Globe className="h-3 w-3" />
                      {result.official_domain}
                    </span>
                    <span>•</span>
                    <span className="font-mono">slug: {result.slug}</span>
                  </div>
                </div>
                {getStatusBadge(result.status)}
              </div>

              {/* Review Notes */}
              <div className="p-4 rounded-xl bg-[#1F1F23] border border-[#2A2A30] text-xs">
                <span className="text-[10px] uppercase tracking-wider font-semibold text-[#A1A1AA] block mb-1">
                  Verification &amp; Compliance Notes
                </span>
                <p className="text-[#F5F5F5] leading-relaxed">
                  {result.additional_info_requested ||
                    (result.status === "APPROVED"
                      ? "Approval is complete. The designated administrator can activate access using the invitation email."
                      : "Your application is under institutional verification.")}
                </p>
              </div>

              {/* Administrative Details */}
              <div className="grid grid-cols-2 gap-3 text-xs p-3 rounded-xl bg-[#1F1F23]/40 border border-[#2A2A30]/50">
                <div>
                  <span className="text-[11px] text-[#A1A1AA]">Tracking code:</span>
                  <p className="text-[#F5F5F5] font-medium truncate">{result.tracking_code}</p>
                </div>
                <div>
                  <span className="text-[11px] text-[#A1A1AA]">Submitted Date:</span>
                  <p className="text-[#F5F5F5] font-medium">
                    {new Date(result.created_at).toLocaleDateString([], {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })}
                  </p>
                </div>
              </div>

              {/* Context Action */}
            </div>
          )}

        </div>

        {/* Footer Navigation */}
        <div className="flex items-center justify-between text-xs text-[#A1A1AA]">
          <Link href="/register-college" className="text-[#6366F1] hover:underline">
            ← Apply for New College
          </Link>
          <Link href="/login" className="hover:text-[#F5F5F5] transition">
            Admin Portal Login →
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function RegistrationStatusPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#0B0B0D] flex items-center justify-center text-xs text-[#A1A1AA]">Loading...</div>}>
      <RegistrationStatusContent />
    </Suspense>
  );
}

