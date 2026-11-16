"use client";

import { useState } from "react";
import { chatService, FeedbackCategory } from "@/services/chat-service";
import { ThumbsUp, ThumbsDown, X, CheckCircle, Tag } from "lucide-react";

interface FeedbackModalProps {
  messageId: string;
  sessionId?: string;
  isOpen: boolean;
  onClose: () => void;
}

const CATEGORIES: { label: string; value: FeedbackCategory }[] = [
  { label: "Accuracy / Content", value: "ACCURACY" },
  { label: "Incorrect Information", value: "INCORRECT_INFO" },
  { label: "Missing Details", value: "MISSING_INFO" },
  { label: "Technical Issue", value: "TECHNICAL_ISSUE" },
  { label: "General Feedback", value: "GENERAL" },
];

export function FeedbackModal({ messageId, sessionId, isOpen, onClose }: FeedbackModalProps) {
  const [rating, setRating] = useState<number>(1);
  const [category, setCategory] = useState<FeedbackCategory>("ACCURACY");
  const [comments, setComments] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    const res = await chatService.submitFeedback(messageId, rating, comments, category, sessionId);
    setSubmitting(false);

    if (res.success) {
      setSubmitted(true);
      setTimeout(() => {
        setSubmitted(false);
        onClose();
      }, 1500);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="w-full max-w-md rounded-2xl border border-[#2A2A30] bg-[#111114] p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-[#A1A1AA] hover:text-[#F5F5F5] transition"
        >
          <X className="h-4 w-4" />
        </button>

        <h3 className="text-base font-semibold text-[#F5F5F5] mb-1">
          Feedback on Answer Accuracy
        </h3>
        <p className="text-xs text-[#A1A1AA] mb-4">
          Your feedback helps college administrators audit and refine the institutional knowledge base.
        </p>

        {submitted ? (
          <div className="py-8 text-center text-[#10B981] flex flex-col items-center gap-2">
            <CheckCircle className="h-8 w-8" />
            <span className="text-sm font-medium">Thank you! Your feedback has been recorded.</span>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex items-center justify-center gap-4 py-2">
              <button
                type="button"
                onClick={() => {
                  setRating(1);
                  setCategory("ACCURACY");
                }}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl border text-xs font-medium transition ${
                  rating === 1
                    ? "bg-[#10B981]/10 border-[#10B981] text-[#10B981]"
                    : "border-[#2A2A30] bg-[#1F1F23] text-[#A1A1AA] hover:text-[#F5F5F5]"
                }`}
              >
                <ThumbsUp className="h-4 w-4" />
                Accurate & Helpful
              </button>

              <button
                type="button"
                onClick={() => {
                  setRating(-1);
                  setCategory("INCORRECT_INFO");
                }}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl border text-xs font-medium transition ${
                  rating === -1
                    ? "bg-[#EF4444]/10 border-[#EF4444] text-[#EF4444]"
                    : "border-[#2A2A30] bg-[#1F1F23] text-[#A1A1AA] hover:text-[#F5F5F5]"
                }`}
              >
                <ThumbsDown className="h-4 w-4" />
                Inaccurate / Unclear
              </button>
            </div>

            <div>
              <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5 flex items-center gap-1.5">
                <Tag className="h-3 w-3 text-[#6366F1]" />
                Feedback Category
              </label>
              <div className="grid grid-cols-2 gap-2">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat.value}
                    type="button"
                    onClick={() => setCategory(cat.value)}
                    className={`px-2.5 py-1.5 rounded-lg border text-[11px] text-left transition font-medium truncate ${
                      category === cat.value
                        ? "bg-[#6366F1]/15 border-[#6366F1] text-[#F5F5F5]"
                        : "border-[#2A2A30] bg-[#1F1F23] text-[#A1A1AA] hover:text-[#F5F5F5]"
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                Additional Comments or Suggestions (Optional)
              </label>
              <textarea
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder="Mention missing details, outdated fees, or formatting issues..."
                rows={3}
                className="w-full p-3 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
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
                {submitting ? "Submitting..." : "Submit Feedback"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

