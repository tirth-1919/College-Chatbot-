"use client";

import { useState } from "react";
import { ChatMessageData } from "@/services/chat-service";
import { VerificationBadge } from "./VerificationBadge";
import { SourceCitation } from "./SourceCitation";
import { FeedbackModal } from "./FeedbackModal";
import { useVoice } from "@/hooks/use-voice";
import { SupportedLanguage } from "@/hooks/use-translation";
import {
  Copy,
  Check,
  Volume2,
  VolumeX,
  RotateCcw,
  ThumbsUp,
  Sparkles,
  ArrowLeftRight,
} from "lucide-react";

interface ChatMessageProps {
  message: ChatMessageData;
  onRegenerate?: () => void;
  lang: SupportedLanguage;
  onConfirmSwitch?: (targetCollegeId: string, pendingQuestion: string, messageId: string) => void;
  onStayWithCollege?: (messageId: string, currentCollegeName: string) => void;
}

export function ChatMessage({
  message,
  onRegenerate,
  lang,
  onConfirmSwitch,
  onStayWithCollege,
}: ChatMessageProps) {
  const isUser = message.sender_role === "user";
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
        <div className="whitespace-pre-wrap">{message.message_text}</div>

        {!isUser && message.source_citations?.some((citation) => citation.image_url) && (
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
            {message.source_citations.filter((citation) => citation.image_url).map((image, index) => (
              <a key={`${image.image_url}-${index}`} href={image.image_url} target="_blank" rel="noreferrer" className="group overflow-hidden rounded-xl border border-[#2A2A30] bg-[#1F1F23]">
                <img src={image.image_url} alt={image.title} loading="lazy" className="w-full aspect-[4/3] object-cover group-hover:scale-[1.02] transition-transform" />
                <div className="p-2.5">
                  <div className="text-xs font-semibold">{image.title}</div>
                  {image.image_category && <div className="mt-1 text-[10px] uppercase tracking-wide text-[#A1A1AA]">{image.image_category.replaceAll("_", " ")}</div>}
                  {image.image_description && <div className="mt-1 text-xs text-[#A1A1AA]">{image.image_description}</div>}
                  {image.event_name && <div className="mt-1 text-xs text-[#A1A1AA]">{image.event_name}{image.event_date ? ` · ${image.event_date}` : ""}</div>}
                  {image.url && <div className="mt-1 text-[10px] text-[#818CF8]">Source</div>}
                </div>
              </a>
            ))}
          </div>
        )}

        {/* In-Chat College Switch Confirmation Card */}
        {message.switch_action && (
          <div className="mt-3 p-3.5 rounded-xl border border-[#6366F1]/30 bg-[#6366F1]/5">
            <div className="flex items-start gap-2.5 mb-3">
              <ArrowLeftRight className="h-4 w-4 text-[#6366F1] mt-0.5 shrink-0" />
              <p className="text-xs text-[#F5F5F5] leading-relaxed">
                You are currently connected to{" "}
                <strong className="text-white font-semibold">
                  {message.switch_action.currentCollegeName}
                </strong>
                . This question is about{" "}
                <strong className="text-white font-semibold">
                  {message.switch_action.targetCollegeName}
                </strong>
                . Would you like to switch?
              </p>
            </div>

            {message.switch_action.status === "switched" ? (
              <div className="inline-flex items-center gap-1.5 text-xs text-[#10B981] font-medium bg-[#10B981]/10 px-2.5 py-1 rounded-lg border border-[#10B981]/20">
                <Check className="h-3.5 w-3.5" />
                Switched to {message.switch_action.targetCollegeName}
              </div>
            ) : message.switch_action.status === "stayed" ? (
              <div className="inline-flex items-center gap-1.5 text-xs text-[#A1A1AA] font-medium bg-[#1F1F23] px-2.5 py-1 rounded-lg border border-[#2A2A30]">
                Stayed with {message.switch_action.currentCollegeName}
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={() =>
                    onConfirmSwitch?.(
                      message.switch_action!.targetCollegeId,
                      message.switch_action!.pendingQuestion,
                      message.id
                    )
                  }
                  className="px-3 py-1.5 rounded-lg bg-[#6366F1] hover:bg-[#4F46E5] text-white text-xs font-semibold transition flex items-center gap-1.5 shadow-sm"
                >
                  <ArrowLeftRight className="h-3.5 w-3.5" />
                  Switch to {message.switch_action.targetCollegeName}
                </button>
                <button
                  type="button"
                  onClick={() =>
                    onStayWithCollege?.(
                      message.id,
                      message.switch_action!.currentCollegeName
                    )
                  }
                  className="px-3 py-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-[#A1A1AA] hover:text-[#F5F5F5] text-xs font-medium transition"
                >
                  Stay with {message.switch_action.currentCollegeName}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Source Citations */}
        {!isUser && message.source_citations && message.source_citations.length > 0 && (
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
                  title="Regenerate response"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                </button>
              )}

              <button
                onClick={() => setIsFeedbackOpen(true)}
                className="p-1.5 rounded-md hover:bg-[#1F1F23] hover:text-[#F5F5F5] transition"
                title="Give feedback"
              >
                <ThumbsUp className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>

      {isFeedbackOpen && (
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
