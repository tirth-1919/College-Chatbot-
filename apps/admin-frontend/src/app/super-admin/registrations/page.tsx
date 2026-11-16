"use client";

import React, { useEffect, useState } from "react";
import { superAdminService } from "@/services/super-admin-service";
import { CollegeRegistration, RegistrationReviewHistory } from "@/types/admin";
import { StatusBadge } from "@/components/StatusBadge";
import {
  UserCheck,
  CheckCircle,
  XCircle,
  RefreshCw,
  ExternalLink,
  Mail,
  Phone,
  Calendar,
  AlertCircle,
  HelpCircle,
  FileText,
  Building2,
  MapPin,
  Award,
  Clock,
  Eye,
  ShieldCheck,
  MessageSquare,
} from "lucide-react";

export default function RegistrationsQueuePage() {
  const [registrations, setRegistrations] = useState<CollegeRegistration[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  // Detailed View Modal
  const [detailItem, setDetailItem] = useState<CollegeRegistration | null>(null);

  // Approval / Rejection / Request-Info Action Modal
  const [selectedItem, setSelectedItem] = useState<CollegeRegistration | null>(null);
  const [actionType, setActionType] = useState<"APPROVE" | "REJECT" | "REQUEST_INFO">("APPROVE");
  const [decisionReason, setDecisionReason] = useState("");
  const [requestInfoPrompt, setRequestInfoPrompt] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchRegistrations = async () => {
    setIsLoading(true);
    try {
      const res = await superAdminService.getRegistrations(statusFilter);
      if (res.success && res.data) {
        setRegistrations(res.data);
      }
    } catch (err) {
      console.error("Failed to load registrations queue:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRegistrations();
  }, [statusFilter]);

  const handleDecision = async () => {
    if (!selectedItem) return;
    setIsSubmitting(true);

    try {
      if (actionType === "APPROVE") {
        await superAdminService.approveRegistration(selectedItem.id, decisionReason);
      } else if (actionType === "REJECT") {
        await superAdminService.rejectRegistration(selectedItem.id, decisionReason);
      } else if (actionType === "REQUEST_INFO") {
        await superAdminService.requestRegistrationInfo(
          selectedItem.id,
          requestInfoPrompt,
          decisionReason
        );
      }
      setIsModalOpen(false);
      setSelectedItem(null);
      setDetailItem(null);
      setDecisionReason("");
      setRequestInfoPrompt("");
      fetchRegistrations();
    } catch (err) {
      console.error("Failed to submit registration decision:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredRegistrations = registrations.filter((item) => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    const name = (item.college_name || item.name || "").toLowerCase();
    const domain = (item.official_domain || "").toLowerCase();
    const tracking = (item.tracking_code || "").toLowerCase();
    const slug = (item.slug || "").toLowerCase();
    return name.includes(q) || domain.includes(q) || tracking.includes(q) || slug.includes(q);
  });

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
            <UserCheck className="h-5 w-5 text-[#6366F1]" />
            College Registration Approval Queue
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Review, verify accreditation, request compliance info, and provision institutional tenants.
          </p>
        </div>

        <button
          onClick={fetchRegistrations}
          className="self-start sm:self-auto p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition flex items-center gap-1.5 text-xs"
          title="Refresh queue"
        >
          <RefreshCw className="h-4 w-4" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter Tabs & Search */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 border-b border-[#2A2A30] pb-3 text-xs">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {[
            { id: "ALL", label: "All" },
            { id: "PENDING", label: "Pending" },
            { id: "UNDER_REVIEW", label: "Under Review" },
            { id: "ADDITIONAL_INFORMATION_REQUIRED", label: "Action Required" },
            { id: "APPROVED", label: "Approved" },
            { id: "REJECTED", label: "Rejected" },
          ].map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setStatusFilter(id)}
              className={`px-3 py-1.5 rounded-lg font-medium transition whitespace-nowrap ${
                statusFilter === id
                  ? "bg-[#6366F1] text-white shadow-sm"
                  : "bg-[#18181B] text-[#A1A1AA] hover:text-[#F5F5F5]"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter by name, domain, tracking code..."
          className="px-3 py-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] text-xs text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1] min-w-[220px]"
        />
      </div>

      {/* Registrations List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20 text-xs text-[#A1A1AA]">
          <div className="flex flex-col items-center gap-2">
            <div className="w-5 h-5 border-2 border-[#6366F1] border-t-transparent rounded-full animate-spin" />
            <span>Loading registration queue...</span>
          </div>
        </div>
      ) : filteredRegistrations.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredRegistrations.map((item) => {
            const displayName = item.college_name || item.name || "College Institution";
            const isPendingAction =
              item.status === "PENDING" ||
              item.status === "UNDER_REVIEW" ||
              item.status === "ADDITIONAL_INFORMATION_REQUIRED";

            return (
              <div
                key={item.id}
                className="p-5 rounded-xl border border-[#2A2A30] bg-[#111114] hover:border-[#3F3F46] transition flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-xl bg-[#6366F1]/10 border border-[#6366F1]/20 flex items-center justify-center text-sm font-bold text-[#6366F1]">
                        {displayName.substring(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-[#F5F5F5]">{displayName}</h3>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[11px] text-[#71717A] font-mono">
                            slug: {item.slug}
                          </span>
                          {item.tracking_code && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#1F1F23] text-[#818CF8] font-mono">
                              {item.tracking_code}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <StatusBadge status={item.status} />
                  </div>

                  <div className="space-y-1.5 py-2.5 my-2 border-y border-[#1F1F23] text-xs text-[#D4D4D8]">
                    <div className="flex items-center gap-2">
                      <ExternalLink className="h-3.5 w-3.5 text-[#71717A]" />
                      <span className="text-[#A1A1AA]">Domain:</span>
                      <a
                        href={`https://${item.official_domain}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[#6366F1] hover:underline font-mono"
                      >
                        {item.official_domain}
                      </a>
                    </div>
                    <div className="flex items-center gap-2">
                      <Mail className="h-3.5 w-3.5 text-[#71717A]" />
                      <span className="text-[#A1A1AA]">Contact:</span>
                      <span className="text-[#F5F5F5] font-mono">
                        {item.contact_email || item.contact_person_email}
                      </span>
                    </div>
                    {item.contact_person_name && (
                      <div className="flex items-center gap-2">
                        <UserCheck className="h-3.5 w-3.5 text-[#71717A]" />
                        <span className="text-[#A1A1AA]">Registrar:</span>
                        <span>{item.contact_person_name}</span>
                      </div>
                    )}
                    {item.city && (
                      <div className="flex items-center gap-2">
                        <MapPin className="h-3.5 w-3.5 text-[#71717A]" />
                        <span className="text-[#A1A1AA]">Location:</span>
                        <span>
                          {item.city}, {item.state || "India"}
                        </span>
                      </div>
                    )}
                    <div className="flex items-center gap-2 text-[11px] text-[#71717A]">
                      <Calendar className="h-3.5 w-3.5" />
                      <span>Submitted: {new Date(item.created_at).toLocaleString()}</span>
                    </div>
                  </div>

                  {/* Clarification notes */}
                  {item.additional_info_requested && (
                    <div className="p-2.5 rounded-lg bg-[#F59E0B]/10 border border-[#F59E0B]/20 text-[11px] text-[#F59E0B] mb-2">
                      <strong>Requested Info:</strong> &ldquo;{item.additional_info_requested}&rdquo;
                    </div>
                  )}
                  {item.additional_info_submitted && (
                    <div className="p-2.5 rounded-lg bg-[#3B82F6]/10 border border-[#3B82F6]/20 text-[11px] text-[#3B82F6] mb-2">
                      <strong>Applicant Response:</strong> &ldquo;{item.additional_info_submitted}&rdquo;
                    </div>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="pt-2 flex flex-wrap items-center justify-between gap-2 border-t border-[#1F1F23]">
                  <button
                    onClick={() => setDetailItem(item)}
                    className="px-2.5 py-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-[#A1A1AA] hover:text-[#F5F5F5] text-xs font-medium transition flex items-center gap-1.5"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    <span>View Details</span>
                  </button>

                  <div className="flex items-center gap-2">
                    {isPendingAction ? (
                      <>
                        <button
                          onClick={() => {
                            setSelectedItem(item);
                            setActionType("REQUEST_INFO");
                            setRequestInfoPrompt("");
                            setDecisionReason("");
                            setIsModalOpen(true);
                          }}
                          className="px-2.5 py-1.5 rounded-lg border border-[#F59E0B]/30 bg-[#F59E0B]/10 hover:bg-[#F59E0B]/20 text-[#F59E0B] text-xs font-medium transition flex items-center gap-1"
                          title="Request clarification or missing documents"
                        >
                          <HelpCircle className="h-3.5 w-3.5" />
                          <span>Request Info</span>
                        </button>
                        <button
                          onClick={() => {
                            setSelectedItem(item);
                            setActionType("REJECT");
                            setDecisionReason("");
                            setIsModalOpen(true);
                          }}
                          className="px-2.5 py-1.5 rounded-lg border border-[#EF4444]/30 bg-[#EF4444]/10 hover:bg-[#EF4444]/20 text-[#EF4444] text-xs font-medium transition flex items-center gap-1"
                        >
                          <XCircle className="h-3.5 w-3.5" />
                          <span>Reject</span>
                        </button>
                        <button
                          onClick={() => {
                            setSelectedItem(item);
                            setActionType("APPROVE");
                            setDecisionReason("");
                            setIsModalOpen(true);
                          }}
                          className="px-3 py-1.5 rounded-lg bg-[#10B981] hover:bg-[#059669] text-white text-xs font-medium transition flex items-center gap-1.5 shadow-md shadow-[#10B981]/20"
                        >
                          <CheckCircle className="h-3.5 w-3.5" />
                          <span>Approve College</span>
                        </button>
                      </>
                    ) : (
                      <span className="text-[11px] text-[#71717A] italic">
                        {item.status === "APPROVED" ? "Tenant provisioned & active." : "Decision logged in audit trail."}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="p-12 text-center rounded-xl border border-[#2A2A30] bg-[#111114]">
          <div className="h-12 w-12 rounded-full bg-[#6366F1]/10 text-[#6366F1] flex items-center justify-center mx-auto mb-3">
            <CheckCircle className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-semibold text-[#F5F5F5] mb-1">
            No Registrations in "{statusFilter}" State
          </h3>
          <p className="text-xs text-[#A1A1AA] max-w-sm mx-auto">
            All onboarding applications matching this status filter have been processed.
          </p>
        </div>
      )}

      {/* Full Registration Details Modal */}
      {detailItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in overflow-y-auto">
          <div className="w-full max-w-2xl bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl space-y-4 my-8">
            <div className="flex items-start justify-between border-b border-[#2A2A30] pb-3">
              <div>
                <h3 className="text-base font-bold text-[#F5F5F5]">
                  {detailItem.college_name || detailItem.name}
                </h3>
                <div className="text-xs text-[#818CF8] font-mono mt-0.5">
                  Tracking Code: {detailItem.tracking_code || "APP-PENDING"}
                </div>
              </div>
              <StatusBadge status={detailItem.status} />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-[#1F1F23]/60 border border-[#2A2A30]">
                <span className="text-[#A1A1AA]">Official Domain:</span>
                <div className="font-mono text-[#F5F5F5] font-semibold mt-0.5">{detailItem.official_domain}</div>
              </div>
              <div className="p-3 rounded-xl bg-[#1F1F23]/60 border border-[#2A2A30]">
                <span className="text-[#A1A1AA]">Institutional Email:</span>
                <div className="font-mono text-[#F5F5F5] font-semibold mt-0.5">{detailItem.contact_email}</div>
              </div>
              <div className="p-3 rounded-xl bg-[#1F1F23]/60 border border-[#2A2A30]">
                <span className="text-[#A1A1AA]">Registrar / Contact Person:</span>
                <div className="text-[#F5F5F5] font-semibold mt-0.5">
                  {detailItem.contact_person_name || "N/A"} ({detailItem.contact_person_email || "N/A"})
                </div>
              </div>
              <div className="p-3 rounded-xl bg-[#1F1F23]/60 border border-[#2A2A30]">
                <span className="text-[#A1A1AA]">Campus Location:</span>
                <div className="text-[#F5F5F5] font-semibold mt-0.5">
                  {detailItem.city || "Ahmedabad"}, {detailItem.state || "Gujarat"}, {detailItem.country || "India"}
                </div>
              </div>
              {detailItem.accreditation_details && (
                <div className="sm:col-span-2 p-3 rounded-xl bg-[#1F1F23]/60 border border-[#2A2A30]">
                  <span className="text-[#A1A1AA]">Accreditation &amp; Affiliations:</span>
                  <div className="text-[#F5F5F5] mt-0.5">{detailItem.accreditation_details}</div>
                </div>
              )}
              {detailItem.description && (
                <div className="sm:col-span-2 p-3 rounded-xl bg-[#1F1F23]/60 border border-[#2A2A30]">
                  <span className="text-[#A1A1AA]">Institution Overview:</span>
                  <div className="text-[#D4D4D8] mt-0.5 leading-relaxed">{detailItem.description}</div>
                </div>
              )}
            </div>

            {/* Review Trail */}
            {detailItem.review_history && detailItem.review_history.length > 0 && (
              <div className="pt-2">
                <h4 className="text-xs font-semibold uppercase text-[#A1A1AA] mb-2">Previous Decision History</h4>
                <div className="space-y-2 max-h-36 overflow-y-auto pr-1">
                  {detailItem.review_history.map((h) => (
                    <div key={h.id} className="p-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-xs">
                      <div className="flex items-center justify-between text-[#F5F5F5] font-semibold mb-0.5">
                        <span>{h.action_type}</span>
                        <span className="text-[10px] text-[#A1A1AA] font-normal">{new Date(h.created_at).toLocaleString()}</span>
                      </div>
                      <div className="text-[#A1A1AA] text-[11px]">{h.comments}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex items-center justify-between pt-4 border-t border-[#2A2A30]">
              <button
                type="button"
                onClick={() => setDetailItem(null)}
                className="px-4 py-2 text-xs text-[#A1A1AA] hover:text-[#F5F5F5] bg-[#1F1F23] rounded-lg transition"
              >
                Close
              </button>

              {detailItem.status === "PENDING" || detailItem.status === "UNDER_REVIEW" ? (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setSelectedItem(detailItem);
                      setActionType("REQUEST_INFO");
                      setRequestInfoPrompt("");
                      setDecisionReason("");
                      setIsModalOpen(true);
                    }}
                    className="px-3 py-1.5 rounded-lg bg-[#F59E0B]/10 hover:bg-[#F59E0B]/20 text-[#F59E0B] text-xs font-medium transition"
                  >
                    Request Info
                  </button>
                  <button
                    onClick={() => {
                      setSelectedItem(detailItem);
                      setActionType("REJECT");
                      setDecisionReason("");
                      setIsModalOpen(true);
                    }}
                    className="px-3 py-1.5 rounded-lg bg-[#EF4444]/10 hover:bg-[#EF4444]/20 text-[#EF4444] text-xs font-medium transition"
                  >
                    Reject
                  </button>
                  <button
                    onClick={() => {
                      setSelectedItem(detailItem);
                      setActionType("APPROVE");
                      setDecisionReason("");
                      setIsModalOpen(true);
                    }}
                    className="px-3.5 py-1.5 rounded-lg bg-[#10B981] hover:bg-[#059669] text-white text-xs font-medium transition shadow-md shadow-[#10B981]/20"
                  >
                    Approve Institution
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {/* Decision Action Modal (Approve, Reject, Request Info) */}
      {isModalOpen && selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-[#F5F5F5]">
              {actionType === "APPROVE"
                ? "Approve College & Provision Tenant"
                : actionType === "REJECT"
                ? "Reject College Registration"
                : "Request Additional Information"}
            </h3>
            <p className="text-xs text-[#A1A1AA]">
              Institution:{" "}
              <span className="text-[#F5F5F5] font-semibold">
                {selectedItem.college_name || selectedItem.name}
              </span>
            </p>

            {actionType === "REQUEST_INFO" && (
              <div>
                <label className="block text-xs font-medium text-[#F59E0B] mb-1.5">
                  Information / Documents Required from Applicant *
                </label>
                <textarea
                  required
                  value={requestInfoPrompt}
                  onChange={(e) => setRequestInfoPrompt(e.target.value)}
                  rows={3}
                  placeholder="e.g. Please provide your official AICTE affiliation approval order for 2024-25..."
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg p-3 text-xs text-[#F5F5F5] focus:outline-none focus:border-[#F59E0B]"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                {actionType === "REJECT"
                  ? "Mandatory Reason for Rejection *"
                  : "Compliance Audit Remarks (Optional)"}
              </label>
              <textarea
                value={decisionReason}
                onChange={(e) => setDecisionReason(e.target.value)}
                rows={3}
                placeholder={
                  actionType === "APPROVE"
                    ? "Domain and accreditation verified."
                    : actionType === "REJECT"
                    ? "Institutional domain or accreditation verification criteria not met."
                    : "Notes for internal audit trail."
                }
                className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg p-3 text-xs text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                disabled={isSubmitting}
                className="px-4 py-2 text-xs text-[#A1A1AA] hover:text-[#F5F5F5] bg-[#1F1F23] rounded-lg transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDecision}
                disabled={isSubmitting || (actionType === "REQUEST_INFO" && !requestInfoPrompt.trim()) || (actionType === "REJECT" && !decisionReason.trim())}
                className={`px-4 py-2 text-xs font-medium rounded-lg text-white transition ${
                  actionType === "APPROVE"
                    ? "bg-[#10B981] hover:bg-[#059669]"
                    : actionType === "REQUEST_INFO"
                    ? "bg-[#F59E0B] hover:bg-[#D97706] text-black font-semibold"
                    : "bg-[#EF4444] hover:bg-[#DC2626]"
                } disabled:opacity-40`}
              >
                {isSubmitting
                  ? "Saving Decision..."
                  : actionType === "APPROVE"
                  ? "Confirm & Provision College"
                  : actionType === "REQUEST_INFO"
                  ? "Send Request to Applicant"
                  : "Confirm Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
