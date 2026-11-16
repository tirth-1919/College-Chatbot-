"use client";

import { HelpCircle, ArrowUpRight } from "lucide-react";

interface SuggestedQuestionsProps {
  onSelect: (question: string) => void;
  collegeName?: string;
}

const DEFAULT_SUGGESTIONS = [
  "What are the first-year engineering fees?",
  "What is the admission process and eligibility criteria?",
  "What documents are required for admission verification?",
  "Are hostel facilities available on campus?",
  "Who is the Head of the Computer Engineering department?",
  "What placement opportunities were recorded last year?",
];

export function SuggestedQuestions({ onSelect, collegeName }: SuggestedQuestionsProps) {
  return (
    <div className="my-6">
      <div className="flex items-center gap-2 text-xs font-medium text-[#A1A1AA] mb-3">
        <HelpCircle className="h-4 w-4 text-[#6366F1]" />
        <span>Popular questions {collegeName ? `for ${collegeName}` : ""}:</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {DEFAULT_SUGGESTIONS.map((q, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSelect(q)}
            className="p-3 rounded-xl border border-[#2A2A30] bg-[#111114] hover:bg-[#1F1F23] hover:border-[#6366F1]/50 text-left text-xs text-[#F5F5F5] transition flex items-center justify-between group"
          >
            <span>{q}</span>
            <ArrowUpRight className="h-3.5 w-3.5 text-[#A1A1AA] group-hover:text-[#6366F1] transition shrink-0 ml-2" />
          </button>
        ))}
      </div>
    </div>
  );
}

