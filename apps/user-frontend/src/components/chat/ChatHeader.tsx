"use client";

import Link from "next/link";
import { Building2, Globe, Trash2, ArrowLeftRight, LifeBuoy } from "lucide-react";
import { SupportedLanguage } from "@/hooks/use-translation";

interface ChatHeaderProps {
  collegeName: string;
  currentLang: SupportedLanguage;
  onLanguageChange: (lang: SupportedLanguage) => void;
  onClearSession: () => void;
  onOpenSupport?: () => void;
}

export function ChatHeader({
  collegeName,
  currentLang,
  onLanguageChange,
  onClearSession,
  onOpenSupport,
}: ChatHeaderProps) {
  return (
    <div className="px-5 py-3.5 border-b border-[#2A2A30] bg-[#111114] flex flex-wrap items-center justify-between gap-3 shrink-0">
      {/* College Info */}
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded-lg bg-[#6366F1]/10 flex items-center justify-center text-[#6366F1] shrink-0">
          <Building2 className="h-4 w-4" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-[#F5F5F5]">{collegeName}</span>
            <span className="text-[10px] text-[#10B981] bg-[#10B981]/10 px-2 py-0.5 rounded-full border border-[#10B981]/20 font-medium">
              Verified Tenant
            </span>
          </div>
          <Link
            href="/colleges"
            className="text-[11px] text-[#A1A1AA] hover:text-[#6366F1] transition flex items-center gap-1"
          >
            <ArrowLeftRight className="h-3 w-3" />
            Switch College Institution
          </Link>
        </div>
      </div>

      {/* Language Selector & Controls */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[#2A2A30] bg-[#1F1F23]">
          <Globe className="h-3.5 w-3.5 text-[#6366F1]" />
          <select
            value={currentLang}
            onChange={(e) => onLanguageChange(e.target.value as SupportedLanguage)}
            className="bg-transparent text-xs text-[#F5F5F5] focus:outline-none cursor-pointer"
          >
            <option value="en" className="bg-[#111114]">English</option>
            <option value="hi" className="bg-[#111114]">हिन्दी (Hindi)</option>
            <option value="gu" className="bg-[#111114]">ગુજરાતી (Gujarati)</option>
          </select>
        </div>

        {onOpenSupport && (
          <button
            onClick={onOpenSupport}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[#2A2A30] bg-[#1F1F23] text-xs text-[#A1A1AA] hover:text-[#F5F5F5] hover:border-[#6366F1] transition"
            title="Contact college helpdesk"
          >
            <LifeBuoy className="h-3.5 w-3.5 text-[#6366F1]" />
            <span className="hidden sm:inline">Helpdesk</span>
          </button>
        )}

        <button
          onClick={onClearSession}
          className="p-1.5 rounded-lg border border-[#2A2A30] text-[#A1A1AA] hover:text-[#EF4444] hover:bg-[#EF4444]/10 transition"
          title="Clear current messages"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

