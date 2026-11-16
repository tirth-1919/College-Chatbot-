"use client";

import React, { useEffect, useState } from "react";
import { collegeAdminService } from "@/services/college-admin-service";
import { KnowledgeChunk } from "@/types/college-admin";
import { StatusBadge } from "@/components/StatusBadge";
import {
  CheckSquare,
  CheckCircle,
  XCircle,
  RefreshCw,
  Globe,
  FileText,
  Edit,
  ExternalLink,
  UploadCloud,
  X,
  AlertTriangle,
} from "lucide-react";

export default function KnowledgeReviewQueuePage() {
  const [reviews, setReviews] = useState<KnowledgeChunk[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Edit chunk modal
  const [editingChunk, setEditingChunk] = useState<KnowledgeChunk | null>(null);
  const [editText, setEditText] = useState("");
  const [isSubmittingEdit, setIsSubmittingEdit] = useState(false);

  // Decision state
  const [actionChunk, setActionChunk] = useState<KnowledgeChunk | null>(null);
  const [decisionType, setDecisionType] = useState<"APPROVE" | "REJECT">("APPROVE");
  const [comments, setComments] = useState("");
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);

  const fetchReviews = async () => {
    setIsLoading(true);
    try {
      const res = await collegeAdminService.getPendingReviews();
      if (res.success && res.data) {
        setReviews(res.data);
      }
    } catch (err) {
      console.error("Failed to load review queue:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReviews();
  }, []);

  const handleDecisionSubmit = async () => {
    if (!actionChunk) return;
    setIsSubmittingDecision(true);

    try {
      await collegeAdminService.submitReviewDecision(
        actionChunk.id,
        decisionType,
        comments
      );
      setActionChunk(null);
      setComments("");
      fetchReviews();
    } catch (err) {
      console.error("Failed to submit review decision:", err);
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingChunk) return;
    setIsSubmittingEdit(true);

    try {
      await collegeAdminService.updateKnowledgeText(editingChunk.id, editText);
      setEditingChunk(null);
      fetchReviews();
    } catch (err) {
      console.error("Failed to update chunk text:", err);
    } finally {
      setIsSubmittingEdit(false);
    }
  };

  const handlePublish = async (chunkId: string) => {
    try {
      await collegeAdminService.publishKnowledgeChunk(chunkId);
      fetchReviews();
    } catch (err) {
      console.error("Failed to publish chunk:", err);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
            <CheckSquare className="h-5 w-5 text-[#F59E0B]" />
            Human-in-the-Loop Knowledge Review Queue
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Zero-hallucination safeguard: Verify extracted website chunks and document paragraphs before granting student citation badges.
          </p>
        </div>

        <button
          onClick={fetchReviews}
          className="self-start sm:self-auto p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
          title="Refresh review queue"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {/* Review Queue Cards */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20 text-xs text-[#A1A1AA]">
          <div className="flex flex-col items-center gap-2">
            <div className="w-5 h-5 border-2 border-[#10B981] border-t-transparent rounded-full animate-spin" />
            <span>Loading pending knowledge items...</span>
          </div>
        </div>
      ) : reviews.length > 0 ? (
        <div className="space-y-4">
          {reviews.map((chunk) => (
            <div
              key={chunk.id}
              className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] hover:border-[#3F3F46] transition space-y-4"
            >
              {/* Card Header: Source Citation */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#1F1F23]">
                <div className="flex items-center gap-2.5 text-xs">
                  <div
                    className={`p-1.5 rounded-lg ${
                      chunk.source_type === "WEBSITE" || chunk.source_type === "OFFICIAL_WEBSITE"
                        ? "bg-[#3B82F6]/10 text-[#3B82F6]"
                        : "bg-[#10B981]/10 text-[#10B981]"
                    }`}
                  >
                    {chunk.source_type === "WEBSITE" || chunk.source_type === "OFFICIAL_WEBSITE" ? (
                      <Globe className="h-3.5 w-3.5" />
                    ) : (
                      <FileText className="h-3.5 w-3.5" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[#A1A1AA]">Source:</span>{" "}
                      {chunk.source_url ? (
                        <a
                          href={chunk.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[#10B981] hover:underline font-mono inline-flex items-center gap-1"
                        >
                          {chunk.source_url}
                          <ExternalLink className="h-2.5 w-2.5" />
                        </a>
                      ) : (
                        <span className="font-mono text-[#F5F5F5]">
                          Document ID: {chunk.source_id.substring(0, 8)}... (Page {chunk.page_number || 1})
                        </span>
                      )}
                      {chunk.category && (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-[#1F1F23] border border-[#2A2A30] text-[#A1A1AA] font-medium">
                          {chunk.category}
                        </span>
                      )}
                    </div>
                    {chunk.heading && (
                      <div className="text-[11px] text-[#A1A1AA] mt-0.5 font-medium truncate max-w-md">
                        {chunk.heading}
                      </div>
                    )}
                  </div>
                </div>

                <StatusBadge status={chunk.status} />
              </div>

              {/* Chunk Content */}
              <div className="p-4 rounded-xl bg-[#0B0B0D] border border-[#1F1F23]">
                <p className="text-xs text-[#F5F5F5] leading-relaxed whitespace-pre-wrap font-sans">
                  "{chunk.chunk_text}"
                </p>
              </div>

              {/* Actions Bar */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                <span className="text-[11px] text-[#71717A]">
                  Ingested on {new Date(chunk.created_at).toLocaleString()}
                </span>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setEditingChunk(chunk);
                      setEditText(chunk.chunk_text);
                    }}
                    className="px-3 py-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-xs font-medium text-[#D4D4D8] transition flex items-center gap-1.5"
                  >
                    <Edit className="h-3.5 w-3.5" />
                    <span>Edit Text</span>
                  </button>

                  <button
                    onClick={() => {
                      setActionChunk(chunk);
                      setDecisionType("REJECT");
                    }}
                    className="px-3 py-1.5 rounded-lg border border-[#EF4444]/30 bg-[#EF4444]/10 hover:bg-[#EF4444]/20 text-[#EF4444] text-xs font-medium transition flex items-center gap-1.5"
                  >
                    <XCircle className="h-3.5 w-3.5" />
                    <span>Reject</span>
                  </button>

                  <button
                    onClick={() => {
                      setActionChunk(chunk);
                      setDecisionType("APPROVE");
                    }}
                    className="px-3.5 py-1.5 rounded-lg bg-[#10B981] hover:bg-[#059669] text-white text-xs font-medium transition flex items-center gap-1.5 shadow-md shadow-[#10B981]/20"
                  >
                    <CheckCircle className="h-3.5 w-3.5" />
                    <span>Approve as Verified</span>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-12 text-center rounded-2xl border border-[#2A2A30] bg-[#111114]">
          <div className="h-12 w-12 rounded-full bg-[#10B981]/10 text-[#10B981] flex items-center justify-center mx-auto mb-3">
            <CheckCircle className="h-6 w-6" />
          </div>
          <h3 className="text-base font-semibold text-[#F5F5F5] mb-1">
            Review Queue Clean & Verified
          </h3>
          <p className="text-xs text-[#A1A1AA] max-w-md mx-auto">
            All extracted website pages and document paragraphs have been reviewed. Verified knowledge is published for student inquiries.
          </p>
        </div>
      )}

      {/* Decision Confirmation Modal */}
      {actionChunk && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl">
            <h3 className="text-base font-bold text-[#F5F5F5] mb-1">
              {decisionType === "APPROVE" ? "Approve Extracted Knowledge" : "Reject Knowledge Chunk"}
            </h3>
            <p className="text-xs text-[#A1A1AA] mb-4">
              {decisionType === "APPROVE"
                ? "Approving confirms factuality and unlocks Tier 2 ADMIN_VERIFIED citation for student chatbot answers."
                : "Rejecting removes this chunk from live RAG vector search to prevent hallucinations."}
            </p>

            <div className="mb-4">
              <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                Reviewer Notes (Optional)
              </label>
              <textarea
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                rows={3}
                placeholder="e.g. Verified against 2026 academic calendar."
                className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg p-2.5 text-xs text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
              />
            </div>

            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setActionChunk(null)}
                disabled={isSubmittingDecision}
                className="px-4 py-2 text-xs text-[#A1A1AA] hover:text-[#F5F5F5] bg-[#1F1F23] rounded-lg transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDecisionSubmit}
                disabled={isSubmittingDecision}
                className={`px-4 py-2 text-xs font-medium rounded-lg text-white transition ${
                  decisionType === "APPROVE"
                    ? "bg-[#10B981] hover:bg-[#059669]"
                    : "bg-[#EF4444] hover:bg-[#DC2626]"
                }`}
              >
                {isSubmittingDecision
                  ? "Saving Decision..."
                  : decisionType === "APPROVE"
                  ? "Confirm Approval"
                  : "Confirm Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Chunk Text Modal */}
      {editingChunk && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-lg bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl relative">
            <button
              onClick={() => setEditingChunk(null)}
              className="absolute top-4 right-4 text-[#71717A] hover:text-[#F5F5F5]"
            >
              <X className="h-4 w-4" />
            </button>

            <h3 className="text-base font-bold text-[#F5F5F5] mb-1">
              Edit Extracted Text
            </h3>
            <p className="text-xs text-[#A1A1AA] mb-4">
              Fix OCR scanning errors or refine phrasing before approving this fact.
            </p>

            <form onSubmit={handleEditSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1.5">
                  Knowledge Chunk Text *
                </label>
                <textarea
                  required
                  rows={6}
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg p-3 text-xs text-[#F5F5F5] leading-relaxed focus:outline-none focus:border-[#10B981]"
                />
              </div>

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-[#2A2A30]">
                <button
                  type="button"
                  onClick={() => setEditingChunk(null)}
                  className="px-4 py-2 text-[#A1A1AA] hover:text-[#F5F5F5] bg-[#1F1F23] rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingEdit}
                  className="px-4 py-2 bg-[#10B981] hover:bg-[#059669] text-white rounded-lg transition font-medium"
                >
                  {isSubmittingEdit ? "Saving..." : "Save Corrections"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

