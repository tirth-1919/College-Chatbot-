"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { registrationService, RegistrationDetailData } from "@/services/registration-service";
import {
  Clock,
  Search,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Building2,
  ExternalLink,
  ShieldAlert,
  Send,
  FileText,
  Calendar,
  User,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
} from "lucide-react";

function StatusContent() {
  const searchParams = useSearchParams();
  const codeParam = searchParams.get("code") || searchParams.get("tracking_code") || "";

  const [query, setQuery] = useState(codeParam);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<RegistrationDetailData | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Additional Information Form State
  const [additionalText, setAdditionalText] = useState("");
  const [submittingInfo, setSubmittingInfo] = useState(false);
  const [infoSuccess, setInfoSuccess] = useState(false);

  const performLookup = async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    setInfoSuccess(false);

    const res = await registrationService.getStatus(q.trim());
    setLoading(false);

    if (res.success && res.data) {
      setData(res.data);
    } else {
      setData(null);
      setError(res.error || "No registration application found matching your search.");
    }
  };

  useEffect(() => {
    if (codeParam) {
      performLookup(codeParam);
    }
  }, [codeParam]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    performLookup(query);
  };

  const handleAdditionalInfoSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!data || !additionalText.trim()) return;

    setSubmittingInfo(true);
    setError(null);

    const res = await registrationService.submitAdditionalInfo(
      data.tracking_code,
      additionalText.trim()
    );
    setSubmittingInfo(false);

    if (res.success && res.data) {
      setData(res.data);
      setAdditionalText("");
      setInfoSuccess(true);
    } else {
      setError(res.error || "Failed to submit additional information. Please try again.");
    }
  };

  const getStatusBadge = (st: string) => {
    switch (st) {
      case "APPROVED":
        return {
          label: "Approved & Active",
          bg: "bg-[#10B981]/10 text-[#10B981] border-[#10B981]/30",
          icon: CheckCircle2,
          desc: "Your institution has been approved. The designated administrator can now log in to the admin portal.",
        };
      case "UNDER_REVIEW":
        return {
          label: "Under Review",
          bg: "bg-[#3B82F6]/10 text-[#3B82F6] border-[#3B82F6]/30",
          icon: Clock,
          desc: "Compliance officers are actively reviewing your institutional documentation and domain records.",
        };
      case "ADDITIONAL_INFORMATION_REQUIRED":
        return {
          label: "Action Required",
          bg: "bg-[#F59E0B]/10 text-[#F59E0B] border-[#F59E0B]/30",
          icon: AlertCircle,
          desc: "The Super Administrator has requested additional clarification or documentation from your institution.",
        };
      case "REJECTED":
        return {
          label: "Application Rejected",
          bg: "bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/30",
          icon: XCircle,
          desc: "The application could not be verified against official accreditation guidelines.",
        };
      default:
        return {
          label: "Pending Verification",
          bg: "bg-[#8B5CF6]/10 text-[#8B5CF6] border-[#8B5CF6]/30",
          icon: Clock,
          desc: "Application queued in the Global Super Admin approval queue for initial intake check.",
        };
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] py-12 px-4 sm:px-6 lg:px-8 bg-[#0B0B0D]">
      <div className="max-w-3xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#6366F1]/10 border border-[#6366F1]/30 text-[#818CF8] text-xs font-medium mb-3">
            <Clock className="h-3.5 w-3.5" />
            Institutional Governance Tracker
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-[#F5F5F5] tracking-tight">
            Track College Registration Status
          </h1>
          <p className="text-sm text-[#A1A1AA] mt-2 max-w-xl mx-auto">
            Check the real-time review progress of your college onboarding application, review comments, and submit requested documents.
          </p>
        </div>

        {/* Search Bar */}
        <div className="p-4 rounded-2xl border border-[#2A2A30] bg-[#111114] shadow-lg">
          <form onSubmit={handleSearchSubmit} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-3.5 h-4 w-4 text-[#A1A1AA]" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter Tracking Code (e.g., APP-AIT-7A9B), slug, or contact email..."
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="px-5 py-2.5 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] text-white text-xs font-medium transition flex items-center gap-2 shadow-md shadow-[#6366F1]/20 disabled:opacity-40 shrink-0"
            >
              {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              <span>{loading ? "Searching..." : "Track"}</span>
            </button>
          </form>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-4 rounded-xl bg-[#EF4444]/10 border border-[#EF4444]/30 text-[#EF4444] text-xs flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Registration Details View */}
        {data && (
          <div className="space-y-6">
            {/* Status Summary Banner */}
            {(() => {
              const badge = getStatusBadge(data.status);
              const BadgeIcon = badge.icon;
              return (
                <div className={`p-6 rounded-2xl border ${badge.bg} shadow-lg space-y-3`}>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <BadgeIcon className="h-5 w-5 shrink-0" />
                      <span className="font-bold text-base text-[#F5F5F5]">{badge.label}</span>
                    </div>
                    <div className="text-xs font-mono px-2.5 py-1 rounded bg-[#000000]/30 border border-[#FFFFFF]/10 text-[#F5F5F5]">
                      Tracking Code: {data.tracking_code}
                    </div>
                  </div>
                  <p className="text-xs opacity-90 leading-relaxed">{badge.desc}</p>

                  {data.status === "APPROVED" && (
                    <div className="pt-2">
                      <a
                        href="http://localhost:3001/login"
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#10B981] hover:bg-[#059669] text-white text-xs font-medium transition shadow-md shadow-[#10B981]/20"
                      >
                        Enter College Admin Portal
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    </div>
                  )}
                </div>
              );
            })()}

            {/* Stepper Timeline */}
            <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-[#A1A1AA] mb-4">
                Application Progression Milestones
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
                {[
                  {
                    step: 1,
                    title: "Application Submitted",
                    desc: "Details logged into queue",
                    done: true,
                  },
                  {
                    step: 2,
                    title: "Domain Verification",
                    desc: "Institutional check",
                    done: data.status !== "PENDING",
                  },
                  {
                    step: 3,
                    title: "Compliance Review",
                    desc: "Super Admin review",
                    done: data.status === "APPROVED" || data.status === "UNDER_REVIEW",
                  },
                  {
                    step: 4,
                    title: "Tenant Active",
                    desc: "Workspace ready",
                    done: data.status === "APPROVED",
                  },
                ].map(({ step, title, desc, done }) => (
                  <div
                    key={step}
                    className={`p-3 rounded-xl border transition ${
                      done
                        ? "border-[#10B981]/40 bg-[#10B981]/5 text-[#F5F5F5]"
                        : "border-[#2A2A30] bg-[#1F1F23]/50 text-[#A1A1AA]"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {done ? (
                        <CheckCircle2 className="h-4 w-4 text-[#10B981]" />
                      ) : (
                        <div className="h-4 w-4 rounded-full border border-[#A1A1AA] flex items-center justify-center text-[10px]">
                          {step}
                        </div>
                      )}
                      <span className="font-semibold">{title}</span>
                    </div>
                    <div className="text-[11px] text-[#A1A1AA]">{desc}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* ACTION REQUIRED: Submit Additional Info Form */}
            {data.status === "ADDITIONAL_INFORMATION_REQUIRED" && (
              <div className="p-6 rounded-2xl border border-[#F59E0B]/50 bg-[#F59E0B]/5 shadow-xl space-y-4">
                <div className="flex items-start gap-3">
                  <ShieldAlert className="h-5 w-5 text-[#F59E0B] shrink-0 mt-0.5" />
                  <div>
                    <h3 className="text-sm font-bold text-[#F5F5F5]">
                      Super Administrator Remarks &amp; Requested Clarification
                    </h3>
                    <p className="text-xs text-[#F59E0B] font-medium mt-1">
                      &ldquo;{data.additional_info_requested || data.review_comments}&rdquo;
                    </p>
                  </div>
                </div>

                {infoSuccess ? (
                  <div className="p-3.5 rounded-xl bg-[#10B981]/20 border border-[#10B981]/40 text-[#10B981] text-xs flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 shrink-0" />
                    <span>Your response has been submitted to the Super Administrator. Status is now Under Review.</span>
                  </div>
                ) : (
                  <form onSubmit={handleAdditionalInfoSubmit} className="space-y-3 pt-2">
                    <label className="block text-xs font-medium text-[#F5F5F5]">
                      Submit Your Response / Additional Information:
                    </label>
                    <textarea
                      rows={3}
                      required
                      value={additionalText}
                      onChange={(e) => setAdditionalText(e.target.value)}
                      placeholder="Provide the requested institutional documents, affiliation details, or clarification..."
                      className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#F59E0B] resize-none"
                    />
                    <button
                      type="submit"
                      disabled={submittingInfo || !additionalText.trim()}
                      className="px-5 py-2.5 rounded-xl bg-[#F59E0B] hover:bg-[#D97706] text-black font-semibold text-xs transition flex items-center gap-1.5 shadow-md shadow-[#F59E0B]/20 disabled:opacity-40"
                    >
                      <Send className="h-3.5 w-3.5" />
                      <span>{submittingInfo ? "Submitting..." : "Submit Response to Reviewer"}</span>
                    </button>
                  </form>
                )}
              </div>
            )}

            {/* Institution Profile Summary Card */}
            <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-[#A1A1AA]">
                Application Details
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="text-[#A1A1AA]">College Name:</span>
                  <div className="font-semibold text-[#F5F5F5] text-sm mt-0.5">{data.college_name}</div>
                </div>

                <div>
                  <span className="text-[#A1A1AA]">Official Domain:</span>
                  <div className="font-mono font-medium text-[#818CF8] text-xs mt-0.5">{data.official_domain}</div>
                </div>

                <div>
                  <span className="text-[#A1A1AA]">Contact Person:</span>
                  <div className="text-[#F5F5F5] mt-0.5">{data.contact_person_name} ({data.contact_person_email})</div>
                </div>

                <div>
                  <span className="text-[#A1A1AA]">Location:</span>
                  <div className="text-[#F5F5F5] mt-0.5">{data.city || "Ahmedabad"}, {data.state || "Gujarat"}, {data.country || "India"}</div>
                </div>

                <div>
                  <span className="text-[#A1A1AA]">Submission Date:</span>
                  <div className="text-[#F5F5F5] mt-0.5">{new Date(data.created_at).toLocaleDateString()}</div>
                </div>

                {data.reviewed_at && (
                  <div>
                    <span className="text-[#A1A1AA]">Last Reviewed:</span>
                    <div className="text-[#F5F5F5] mt-0.5">{new Date(data.reviewed_at).toLocaleDateString()}</div>
                  </div>
                )}
              </div>
            </div>

            {/* Review History Trail */}
            {data.review_history && data.review_history.length > 0 && (
              <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-[#A1A1AA]">
                  Review &amp; Audit Trail
                </h3>
                <div className="space-y-2.5">
                  {data.review_history.map((rev) => (
                    <div
                      key={rev.id}
                      className="p-3 rounded-xl border border-[#2A2A30] bg-[#1F1F23]/60 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-1.5"
                    >
                      <div>
                        <span className="font-semibold text-[#F5F5F5]">{rev.action_type}: </span>
                        <span className="text-[#A1A1AA]">{rev.comments || "No remarks"}</span>
                      </div>
                      <div className="text-[11px] text-[#A1A1AA]/60 shrink-0">
                        {new Date(rev.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} &bull; {new Date(rev.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Footer Navigation */}
        <div className="text-center pt-4 text-xs text-[#A1A1AA]">
          Need to register another institution?{" "}
          <Link href="/register-college" className="text-[#818CF8] hover:underline font-medium">
            Start New Institutional Application &rarr;
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function RegistrationStatusPage() {
  return (
    <Suspense fallback={<div className="p-12 text-center text-xs text-[#A1A1AA]">Loading status tracker...</div>}>
      <StatusContent />
    </Suspense>
  );
}

