"use client";

import React, { useEffect, useState } from "react";
import { collegeAdminService } from "@/services/college-admin-service";
import { CollegeSupportTicket, CollegeSupportTicketReply, CollegeFeedback } from "@/types/college-admin";
import { DataTable, Column } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import {
  LifeBuoy,
  RefreshCw,
  Edit,
  X,
  MessageSquare,
  Star,
  CheckCircle,
  Clock,
  Send,
  Lock,
  User,
  Shield,
  Tag,
} from "lucide-react";

export default function CollegeSupportAndFeedbackPage() {
  const [activeTab, setActiveTab] = useState<"TICKETS" | "FEEDBACK">("TICKETS");
  const [tickets, setTickets] = useState<CollegeSupportTicket[]>([]);
  const [feedbacks, setFeedbacks] = useState<CollegeFeedback[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("ALL");

  // Threaded conversation modal state
  const [selectedTicket, setSelectedTicket] = useState<CollegeSupportTicket | null>(null);
  const [replies, setReplies] = useState<CollegeSupportTicketReply[]>([]);
  const [loadingReplies, setLoadingReplies] = useState(false);
  const [replyText, setReplyText] = useState("");
  const [isInternal, setIsInternal] = useState(false);
  const [resolutionStatus, setResolutionStatus] = useState("RESOLVED");
  const [responseNotes, setResponseNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [ticketsRes, feedbackRes] = await Promise.all([
        collegeAdminService.getSupportTickets(statusFilter === "ALL" ? undefined : statusFilter),
        collegeAdminService.getFeedback(),
      ]);

      if (ticketsRes.success && ticketsRes.data) setTickets(ticketsRes.data);
      if (feedbackRes.success && feedbackRes.data) setFeedbacks(feedbackRes.data);
    } catch (err) {
      console.error("Failed to load support inquiries:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [statusFilter]);

  const openTicketModal = async (ticket: CollegeSupportTicket) => {
    setSelectedTicket(ticket);
    setResolutionStatus(ticket.status);
    setResponseNotes(ticket.resolution_notes || "");
    setReplyText("");
    setIsInternal(false);
    setLoadingReplies(true);

    try {
      const res = await collegeAdminService.getTicketDetail(ticket.id);
      if (res.success && res.data && res.data.replies) {
        setReplies(res.data.replies);
      } else {
        setReplies(ticket.replies || []);
      }
    } catch (e) {
      setReplies(ticket.replies || []);
    } finally {
      setLoadingReplies(false);
    }
  };

  const handleResolveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket) return;
    setIsSubmitting(true);

    try {
      await collegeAdminService.resolveSupportTicket(
        selectedTicket.id,
        resolutionStatus,
        responseNotes
      );
      setSelectedTicket((prev) => prev ? { ...prev, status: resolutionStatus as any, resolution_notes: responseNotes } : null);
      fetchData();
    } catch (err) {
      console.error("Failed to resolve ticket:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim() || !selectedTicket) return;
    setIsSubmitting(true);

    try {
      const res = await collegeAdminService.addTicketReply(selectedTicket.id, replyText.trim(), isInternal);
      if (res.success) {
        const newReply: CollegeSupportTicketReply = (res as any).data || {
          id: "reply-" + Date.now(),
          ticket_id: selectedTicket.id,
          sender_user_id: "admin",
          sender_name: "Staff Admin",
          sender_role: "COLLEGE_ADMIN",
          message_text: replyText.trim(),
          is_internal: isInternal,
          created_at: new Date().toISOString(),
        };
        setReplies((prev) => [...prev, newReply]);
        setReplyText("");
        setIsInternal(false);
        fetchData();
      }
    } catch (err) {
      console.error("Failed to add reply:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const ticketColumns: Column<CollegeSupportTicket>[] = [
    {
      header: "Student Inquirer",
      cell: (item) => (
        <div>
          <span className="font-semibold text-[#F5F5F5] block text-xs">
            {item.student_name || item.user_name || "Student"}
          </span>
          <span className="text-[11px] text-[#71717A] font-mono">
            {item.student_email || item.user_email || "student@campus.edu"}
          </span>
        </div>
      ),
    },
    {
      header: "Inquiry Subject & Message",
      cell: (item) => (
        <div className="max-w-md sm:max-w-lg py-1">
          <span className="font-semibold text-xs text-[#F5F5F5] block truncate">
            {item.subject}
          </span>
          <p className="text-[11px] text-[#A1A1AA] line-clamp-1">
            {item.message}
          </p>
        </div>
      ),
    },
    {
      header: "Category & Priority",
      cell: (item) => (
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#1F1F23] text-[#A1A1AA] border border-[#2A2A30] w-fit">
            {item.category || "GENERAL"}
          </span>
          <span
            className={`text-[10px] font-semibold px-2 py-0.5 rounded w-fit ${
              item.priority === "URGENT"
                ? "bg-[#EF4444]/15 text-[#EF4444] border border-[#EF4444]/30"
                : item.priority === "HIGH"
                ? "bg-[#F59E0B]/15 text-[#F59E0B] border border-[#F59E0B]/30"
                : "bg-[#1F1F23] text-[#A1A1AA]"
            }`}
          >
            {item.priority || "MEDIUM"}
          </span>
        </div>
      ),
    },
    {
      header: "Status",
      cell: (item) => <StatusBadge status={item.status} />,
    },
    {
      header: "Submitted",
      cell: (item) => (
        <span className="text-[11px] text-[#71717A]">
          {new Date(item.created_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      header: "Action",
      className: "text-right",
      cell: (item) => (
        <button
          onClick={() => openTicketModal(item)}
          className="p-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-[#A1A1AA] hover:text-[#10B981] transition"
          title="Open conversation thread"
        >
          <Edit className="h-3.5 w-3.5" />
        </button>
      ),
    },
  ];

  const feedbackColumns: Column<CollegeFeedback>[] = [
    {
      header: "Rating",
      cell: (item) => (
        <div className="flex items-center gap-1 text-[#F59E0B]">
          <Star className="h-3.5 w-3.5 fill-current" />
          <span className="font-bold text-xs">{item.rating} / 5</span>
        </div>
      ),
    },
    {
      header: "Category",
      cell: (item) => (
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#1F1F23] text-[#A1A1AA] border border-[#2A2A30]">
          {item.category || "ACCURACY"}
        </span>
      ),
    },
    {
      header: "Student Comments",
      cell: (item) => (
        <p className="text-xs text-[#D4D4D8] italic">
          {item.comments || item.comment ? `"${item.comments || item.comment}"` : "No comment left."}
        </p>
      ),
    },
    {
      header: "Student Account",
      cell: (item) => (
        <span className="font-mono text-[11px] text-[#71717A]">
          {item.user_email || "Anonymous Student"}
        </span>
      ),
    },
    {
      header: "Date",
      cell: (item) => (
        <span className="text-[11px] text-[#71717A]">
          {new Date(item.created_at).toLocaleDateString()}
        </span>
      ),
    },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
            <LifeBuoy className="h-5 w-5 text-[#10B981]" />
            Student Inquiries & Chatbot Feedback
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Official student support tickets with multi-turn conversation threads, internal staff notes, and ratings.
          </p>
        </div>

        <button
          onClick={fetchData}
          className="self-start sm:self-auto p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
          title="Refresh support inquiries"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {/* Main Mode Tabs */}
      <div className="flex items-center gap-2 border-b border-[#2A2A30] pb-3 text-xs">
        <button
          onClick={() => setActiveTab("TICKETS")}
          className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
            activeTab === "TICKETS"
              ? "bg-[#10B981] text-white"
              : "bg-[#18181B] text-[#A1A1AA] hover:text-[#F5F5F5]"
          }`}
        >
          <LifeBuoy className="h-3.5 w-3.5" />
          <span>Escalated Support Inquiries ({tickets.length})</span>
        </button>
        <button
          onClick={() => setActiveTab("FEEDBACK")}
          className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
            activeTab === "FEEDBACK"
              ? "bg-[#10B981] text-white"
              : "bg-[#18181B] text-[#A1A1AA] hover:text-[#F5F5F5]"
          }`}
        >
          <Star className="h-3.5 w-3.5" />
          <span>Student Rating Feedback ({feedbacks.length})</span>
        </button>
      </div>

      {activeTab === "TICKETS" ? (
        <DataTable
          data={tickets}
          columns={ticketColumns}
          searchPlaceholder="Search support inquiries by student, category or message..."
          emptyMessage="No escalated support inquiries found."
        />
      ) : (
        <DataTable
          data={feedbacks}
          columns={feedbackColumns}
          searchPlaceholder="Search feedback comments..."
          emptyMessage="No student feedback recorded yet."
        />
      )}

      {/* Threaded Conversation & Resolution Modal */}
      {selectedTicket && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-2xl bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl relative max-h-[90vh] flex flex-col">
            <button
              onClick={() => setSelectedTicket(null)}
              className="absolute top-4 right-4 text-[#71717A] hover:text-[#F5F5F5]"
            >
              <X className="h-4 w-4" />
            </button>

            {/* Modal Header */}
            <div className="pb-3 border-b border-[#2A2A30]">
              <div className="flex items-center gap-2">
                <StatusBadge status={selectedTicket.status} />
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#1F1F23] text-[#A1A1AA] border border-[#2A2A30]">
                  {selectedTicket.category || "GENERAL"}
                </span>
                <span className="text-[11px] font-semibold text-[#10B981]">
                  Priority: {selectedTicket.priority || "MEDIUM"}
                </span>
              </div>
              <h3 className="text-base font-bold text-[#F5F5F5] mt-1.5">
                {selectedTicket.subject}
              </h3>
              <p className="text-xs text-[#A1A1AA]">
                Student: <span className="text-[#F5F5F5] font-semibold">{selectedTicket.student_name || selectedTicket.user_name || "Student"}</span> ({selectedTicket.student_email || selectedTicket.user_email || "student@campus.edu"})
              </p>
            </div>

            {/* Conversation Messages Container */}
            <div className="flex-1 overflow-y-auto py-4 space-y-3.5 pr-1">
              {/* Original Inquiry */}
              <div className="p-3.5 rounded-xl bg-[#1F1F23] border border-[#2A2A30]">
                <div className="flex items-center justify-between text-[11px] text-[#A1A1AA] mb-1">
                  <span className="font-semibold text-[#F5F5F5] flex items-center gap-1.5">
                    <User className="h-3 w-3 text-[#6366F1]" />
                    {selectedTicket.student_name || "Student"}
                  </span>
                  <span>{new Date(selectedTicket.created_at).toLocaleString()}</span>
                </div>
                <p className="text-xs text-[#D4D4D8] leading-relaxed whitespace-pre-wrap">
                  {selectedTicket.message}
                </p>
              </div>

              {/* Threaded Replies */}
              {loadingReplies ? (
                <div className="py-4 text-center text-xs text-[#A1A1AA]">
                  Loading conversation history...
                </div>
              ) : replies.length === 0 ? (
                <div className="py-3 text-center text-xs text-[#71717A] italic">
                  No replies on this ticket yet.
                </div>
              ) : (
                replies.map((reply) => (
                  <div
                    key={reply.id}
                    className={`p-3.5 rounded-xl border text-xs leading-relaxed ${
                      reply.is_internal
                        ? "bg-[#F59E0B]/10 border-[#F59E0B]/30"
                        : "bg-[#0B0B0D] border-[#2A2A30]"
                    }`}
                  >
                    <div className="flex items-center justify-between text-[11px] mb-1.5">
                      <div className="flex items-center gap-1.5">
                        {reply.is_internal ? (
                          <span className="flex items-center gap-1 text-[#F59E0B] font-semibold text-[10px] uppercase tracking-wide">
                            <Lock className="h-3 w-3" />
                            Internal Staff Note (Staff Only)
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-[#10B981] font-semibold">
                            <Shield className="h-3 w-3" />
                            {reply.sender_name || "Official Admin"}
                          </span>
                        )}
                        <span className="text-[#71717A] text-[10px] font-mono">
                          ({reply.sender_role})
                        </span>
                      </div>
                      <span className="text-[#71717A] text-[10px]">
                        {new Date(reply.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                    <p className={`whitespace-pre-wrap ${reply.is_internal ? "text-[#FDE68A]" : "text-[#D4D4D8]"}`}>
                      {reply.message_text}
                    </p>
                  </div>
                ))
              )}
            </div>

            {/* Post Reply Box */}
            <form onSubmit={handleAddReply} className="pt-3 border-t border-[#2A2A30] space-y-2.5">
              <textarea
                rows={2}
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                placeholder="Post an official reply to the student or leave an internal staff note..."
                className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg p-2.5 text-xs text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#10B981] transition"
              />

              <div className="flex items-center justify-between text-xs">
                <label className="flex items-center gap-2 cursor-pointer text-[#A1A1AA] hover:text-[#F5F5F5]">
                  <input
                    type="checkbox"
                    checked={isInternal}
                    onChange={(e) => setIsInternal(e.target.checked)}
                    className="rounded border-[#2A2A30] bg-[#1F1F23] text-[#F59E0B] focus:ring-0 cursor-pointer"
                  />
                  <span className="flex items-center gap-1 text-[11px]">
                    <Lock className="h-3 w-3 text-[#F59E0B]" />
                    Internal note only (Hidden from student)
                  </span>
                </label>

                <button
                  type="submit"
                  disabled={!replyText.trim() || isSubmitting}
                  className="px-3.5 py-1.5 rounded-lg bg-[#10B981] hover:bg-[#059669] text-white font-medium text-xs flex items-center gap-1.5 disabled:opacity-40 transition"
                >
                  <Send className="h-3 w-3" />
                  <span>Send Reply</span>
                </button>
              </div>
            </form>

            {/* Resolution Status Bar */}
            <form onSubmit={handleResolveSubmit} className="pt-3 mt-2 border-t border-[#2A2A30] flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2">
                <label className="text-[#A1A1AA] font-medium">Status:</label>
                <select
                  value={resolutionStatus}
                  onChange={(e) => setResolutionStatus(e.target.value)}
                  className="bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-2.5 py-1 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                >
                  <option value="OPEN">OPEN (Awaiting Staff)</option>
                  <option value="IN_PROGRESS">IN_PROGRESS (Reviewing)</option>
                  <option value="WAITING_FOR_USER">WAITING_FOR_USER (Student response needed)</option>
                  <option value="RESOLVED">RESOLVED (Inquiry Answered)</option>
                  <option value="CLOSED">CLOSED (Archived)</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedTicket(null)}
                  className="px-3 py-1.5 text-[#A1A1AA] hover:text-[#F5F5F5] bg-[#1F1F23] rounded-lg transition"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-3 py-1.5 bg-[#6366F1] hover:bg-[#4F46E5] text-white rounded-lg transition font-medium"
                >
                  Update Status
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

