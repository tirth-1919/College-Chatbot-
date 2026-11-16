"use client";

import { ShieldCheck, Sparkles, RefreshCcw, HelpCircle, CheckCircle } from "lucide-react";

interface VerificationBadgeProps {
  sourceType: "OFFICIAL_WEBSITE" | "ADMIN_VERIFIED" | "GEMINI_UNVERIFIED" | "SECONDARY_AI_FALLBACK" | "NO_RELIABLE_INFORMATION" | "AI_GUIDANCE" | "OPENAI_UNVERIFIED" | "XKIRO_UNVERIFIED";
  isVerified: boolean;
}

export function VerificationBadge({ sourceType, isVerified }: VerificationBadgeProps) {
  if (sourceType === "OFFICIAL_WEBSITE") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/30">
        <ShieldCheck className="h-3.5 w-3.5 shrink-0" />
        Verified by Official Website
      </span>
    );
  }

  if (sourceType === "ADMIN_VERIFIED") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/30">
        <CheckCircle className="h-3.5 w-3.5 shrink-0" />
        Admin Verified Document
      </span>
    );
  }

  if (sourceType === "GEMINI_UNVERIFIED") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/30">
        <Sparkles className="h-3.5 w-3.5 shrink-0" />
        General AI Guidance (Unverified)
      </span>
    );
  }

  if (sourceType === "SECONDARY_AI_FALLBACK") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/30">
        <RefreshCcw className="h-3.5 w-3.5 shrink-0" />
        Fallback AI Guidance (Unverified)
      </span>
    );
  }

  if (sourceType === "AI_GUIDANCE") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/30">
        <Sparkles className="h-3.5 w-3.5 shrink-0" />
        AI Guidance — Not verified by college
      </span>
    );
  }

  if (sourceType === "OPENAI_UNVERIFIED") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/30">
        <RefreshCcw className="h-3.5 w-3.5 shrink-0" />
        OpenAI AI Guidance — Not verified by college
      </span>
    );
  }

  if (sourceType === "XKIRO_UNVERIFIED") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/30">
        <RefreshCcw className="h-3.5 w-3.5 shrink-0" />
        xKiro AI Guidance — Not verified by college
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[#2A2A30] text-[#A1A1AA] border border-[#2A2A30]">
      <HelpCircle className="h-3.5 w-3.5 shrink-0" />
      No Verified Information Available
    </span>
  );
}

