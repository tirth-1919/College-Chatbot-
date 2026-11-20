"use client";

import { useState } from "react";
import { ChatMessageData } from "@/services/chat-service";
import { VerificationBadge } from "./VerificationBadge";
import { SourceCitation } from "./SourceCitation";
import { FeedbackModal } from "./FeedbackModal";
import { useVoice } from "@/hooks/use-voice";
import { SupportedLanguage } from "@/hooks/use-translation";
import Link from "next/link";
import {
  Copy,
  Check,
  Volume2,
  VolumeX,
  RotateCcw,
  ThumbsUp,
  User,
  Sparkles,
  ArrowLeftRight,
} from "lucide-react";

interface ChatMessageProps {
  message: ChatMessageData;
  onRegenerate?: () => void;
  lang: SupportedLanguage;
}

export function ChatMessage({ message, onRegenerate, lang }: ChatMessageProps) {
  const isUser = message.sender_role === "user";
  const switchCollegeMatch = !isUser
    ? message.message_text.match(/__CAMPUSAI_SWITCH_COLLEGE__:([^\n]+)/)
    : null;
  const switchCollegeName = switchCollegeMatch?.[1]?.trim() || null;
  const displayText = switchCollegeName
    ? message.message_text.replace(/__CAMPUSAI_SWITCH_COLLEGE__:[^\n]+/, "").trim()
    : message.message_text;
  const [copied, setCopied] = useState(false);
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);
  const { isSpeaking, speak, stopSpeaking } = useVoice();

  const handleCopy = () => {
    navigator.clipboard.writeText(message.message_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleToggleSpeak = () => {
    if (isSpeaking) {
      stopSpeaking();
    } else {
      // Strip markdown markers for smooth audio readout
      const cleanText = message.message_text
        .replace(/[*_#`~>]/g, "")
        .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
        .trim();
      speak(cleanText, lang);
    }
  };

  const formattedTime = new Date(message.created_at).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className={`flex gap-3.5 my-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="h-8 w-8 rounded-full bg-[#6366F1]/10 border border-[#6366F1]/30 flex items-center justify-center text-[#6366F1] shrink-0 mt-1">
          <Sparkles className="h-4 w-4" />
        </div>
      )}

      <div
        className={`max-w-2xl rounded-2xl p-4 text-sm leading-relaxed ${
          isUser
            ? "bg-[#6366F1] text-white rounded-br-xs"
            : "bg-[#111114] border border-[#2A2A30] text-[#F5F5F5] rounded-bl-xs shadow-md"
        }`}
      >
        {/* Verification Status Header for Assistant */}
        {!isUser && (
          <div className="flex items-center justify-between gap-2 mb-2.5 pb-2 border-b border-[#2A2A30]">
            <VerificationBadge
              sourceType={message.answer_source_type}
              isVerified={message.is_verified}
            />
            {message.model_used && (
              <span className="text-[10px] text-[#A1A1AA] font-mono">
                {message.model_used}
              </span>
            )}
          </div>
        )}

        {/* Message Content */}
        <div className="whitespace-pre-wrap">{displayText}</div>

        {switchCollegeName && (
          <Link
            href="/colleges"
            className="mt-3 inline-flex items-center gap-2 rounded-lg border border-[#6366F1]/50 bg-[#6366F1]/10 px-3 py-2 text-xs font-semibold text-[#A5B4FC] hover:bg-[#6366F1]/20"
          >
            <ArrowLeftRight className="h-3.5 w-3.5" />
            Switch to {switchCollegeName}
          </Link>
        )}

        {/* Source Citations */}
        {!isUser && message.source_citations && (
          <SourceCitation citations={message.source_citations} />
        )}

        {/* Message Footer & Action Toolbar */}
        <div
          className={`flex items-center justify-between gap-3 mt-3 pt-2 text-[11px] ${
            isUser ? "text-white/70" : "text-[#A1A1AA] border-t border-[#2A2A30]/60"
          }`}
        >
          <span>{formattedTime}</span>

          {!isUser && (
            <div className="flex items-center gap-1">
              <button
                onClick={handleCopy}
                className="p-1.5 rounded-md hover:bg-[#1F1F23] hover:text-[#F5F5F5] transition"
                title="Copy response"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-[#10B981]" /> : <Copy className="h-3.5 w-3.5" />}
              </button>

              <button
                onClick={handleToggleSpeak}
                className={`flex items-center gap-1 px-1.5 py-1 rounded-md transition ${
                  isSpeaking ? "bg-[#6366F1]/20 text-[#6366F1] font-medium" : "hover:bg-[#1F1F23] hover:text-[#F5F5F5]"
                }`}
                title={isSpeaking ? "Stop reading" : "Read aloud"}
              >
                {isSpeaking ? (
                  <>
                    <VolumeX className="h-3.5 w-3.5 animate-pulse text-[#6366F1]" />
                    <span className="text-[10px] text-[#6366F1]">Playing</span>
                  </>
                ) : (
                  <Volume2 className="h-3.5 w-3.5" />
                )}
              </button>

              {onRegenerate && (
                <button
                  onClick={onRegenerate}
                  className="p-1.5 rounded-md hover:bg-[#1F1F23] hover:text-[#F5F5F5] transition"
                  title="Regenerate answer"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                </button>
              )}

              <button
                onClick={() => setIsFeedbackOpen(true)}
                className="p-1.5 rounded-md hover:bg-[#1F1F23] hover:text-[#10B981] transition"
                title="Rate answer"
              >
                <ThumbsUp className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>

      {isUser && (
        <div className="h-8 w-8 rounded-full bg-[#1F1F23] border border-[#2A2A30] flex items-center justify-center text-[#A1A1AA] shrink-0 mt-1">
          <User className="h-4 w-4" />
        </div>
      )}

      {/* Feedback Modal */}
      {!isUser && (
        <FeedbackModal
          messageId={message.id}
          sessionId={message.session_id}
          isOpen={isFeedbackOpen}
          onClose={() => setIsFeedbackOpen(false)}
        />
      )}
    </div>
  );
}

