"use client";

import { Globe, Trash2, ArrowLeftRight, LifeBuoy } from "lucide-react";
import { SupportedLanguage } from "@/hooks/use-translation";
import { ThemeToggle } from "@/components/ThemeToggle";

interface ChatHeaderProps {
  collegeName: string;
  currentLang: SupportedLanguage;
  onLanguageChange: (lang: SupportedLanguage) => void;
  onClearSession: () => void;
  onOpenSupport?: () => void;
  onOpenSwitchCollege?: () => void;
}

export function ChatHeader({
  collegeName,
  currentLang,
  onLanguageChange,
  onClearSession,
  onOpenSupport,
  onOpenSwitchCollege,
}: ChatHeaderProps) {
  // If no college is connected yet (initial welcome state), do not display the college subheader row
  if (!collegeName) {
    return null;
  }

  return (
    <div className="px-5 py-3 border-b border-[#2A2A30] bg-[#111114] flex flex-wrap items-center justify-between gap-3 shrink-0">
      {/* Connected College Name & Clean Switch College Button */}
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold text-[#F5F5F5] tracking-tight">
          {collegeName}
        </span>
        {onOpenSwitchCollege && (
          <button
            onClick={onOpenSwitchCollege}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium text-[#A1A1AA] hover:text-[#F5F5F5] hover:bg-[#1F1F23] border border-[#2A2A30] transition"
            title="Switch College"
          >
            <ArrowLeftRight className="h-3.5 w-3.5 text-[#6366F1]" />
            <span>Switch College</span>
          </button>
        )}
      </div>

      {/* Language Selector & Utility Controls */}
      <div className="flex items-center gap-2.5">
        <ThemeToggle />
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
