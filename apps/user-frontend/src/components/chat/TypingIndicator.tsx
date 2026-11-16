"use client";

import { Sparkles } from "lucide-react";

export function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 my-2">
      <div className="h-8 w-8 rounded-full bg-[#6366F1]/10 border border-[#6366F1]/30 flex items-center justify-center text-[#6366F1] shrink-0">
        <Sparkles className="h-4 w-4" />
      </div>
      <div className="p-3.5 rounded-2xl bg-[#111114] border border-[#2A2A30] text-sm text-[#A1A1AA] flex items-center gap-2">
        <span>Retrieving verified college facts</span>
        <div className="flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-[#6366F1] animate-bounce [animation-delay:-0.3s]"></span>
          <span className="h-1.5 w-1.5 rounded-full bg-[#6366F1] animate-bounce [animation-delay:-0.15s]"></span>
          <span className="h-1.5 w-1.5 rounded-full bg-[#6366F1] animate-bounce"></span>
        </div>
      </div>
    </div>
  );
}

