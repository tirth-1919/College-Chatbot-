"use client";

import { useState } from "react";
import { chatService, SupportTicketInput } from "@/services/chat-service";
import { LifeBuoy, X, CheckCircle, AlertCircle } from "lucide-react";

interface SupportModalProps {
  collegeId: string;
  sessionId?: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export function SupportModal({ collegeId, sessionId, isOpen, onClose }: SupportModalProps) {
  const [subject, setSubject] = useState("");
  const [category, setCategory] = useState<SupportTicketInput["category"]>("CHATBOT");
  const [priority, setPriority] = useState<SupportTicketInput["priority"]>("MEDIUM");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim() || !message.trim()) return;

    setSubmitting(true);
    setErrorMsg("");

    const res = await chatService.createSupportTicket({
      college_id: collegeId,
      session_id: sessionId || undefined,
      subject: subject.trim(),
      message: message.trim(),
      category,
      priority,
    });

    setSubmitting(false);

    if (res.success) {
      setStatus("success");
      setTimeout(() => {
        setStatus("idle");
        setSubject("");
        setMessage("");
        onClose();
      }, 1800);
    } else {
      setStatus("error");
      setErrorMsg(res.error || "Failed to submit support ticket. Please try again.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="w-full max-w-lg rounded-2xl border border-[#2A2A30] bg-[#111114] p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-[#A1A1AA] hover:text-[#F5F5F5] transition"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex items-center gap-2.5 mb-1">
          <div className="h-7 w-7 rounded-lg bg-[#6366F1]/10 flex items-center justify-center text-[#6366F1]">
            <LifeBuoy className="h-4 w-4" />
          </div>
          <h3 className="text-base font-semibold text-[#F5F5F5]">
            Contact College Helpdesk
          </h3>
        </div>
        <p className="text-xs text-[#A1A1AA] mb-4">
          Need official escalation, fee clarifications, or spotted missing data? Submit an inquiry ticket directly to the college administration team.
        </p>

        {status === "success" ? (
          <div className="py-8 text-center text-[#10B981] flex flex-col items-center gap-2">
            <CheckCircle className="h-8 w-8" />
            <span className="text-sm font-medium">Ticket submitted successfully!</span>
            <span className="text-xs text-[#A1A1AA]">
              College administrators have been notified and will review your inquiry.
            </span>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3.5">
            {status === "error" && (
              <div className="p-3 rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/30 text-xs text-[#EF4444] flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-[#A1A1AA] mb-1">
                Subject
              </label>
              <input
                type="text"
                required
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="e.g., Query regarding MYSY Scholarship document submission deadline"
                className="w-full p-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-[#A1A1AA] mb-1">
                  Category
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as any)}
                  className="w-full p-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] text-xs focus:outline-none focus:border-[#6366F1] transition"
                >
                  <option value="CHATBOT">Chatbot Response Issue</option>
                  <option value="INCORRECT_ANSWER">Incorrect Information</option>
                  <option value="MISSING_INFO">Missing Institutional Info</option>
                  <option value="DOCUMENT">Admission / Circular Document</option>
                  <option value="LOGIN">Account / Access Issue</option>
                  <option value="TECHNICAL">Technical Glitch</option>
                  <option value="OTHER">Other Inquiry</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#A1A1AA] mb-1">
                  Priority
                </label>
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value as any)}
                  className="w-full p-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] text-xs focus:outline-none focus:border-[#6366F1] transition"
                >
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                  <option value="URGENT">Urgent</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-[#A1A1AA] mb-1">
                Detailed Message
              </label>
              <textarea
                required
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={4}
                placeholder="Please describe your question, student enrollment details (if applicable), or specify what is inaccurate..."
                className="w-full p-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-lg border border-[#2A2A30] text-xs font-medium text-[#A1A1AA] hover:text-[#F5F5F5] transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 rounded-lg bg-[#6366F1] hover:bg-[#4F46E5] text-xs font-medium text-white transition disabled:opacity-50"
              >
                {submitting ? "Submitting Ticket..." : "Submit Ticket"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

