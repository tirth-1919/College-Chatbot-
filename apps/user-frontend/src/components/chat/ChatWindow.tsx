"use client";

import { useEffect, useRef } from "react";
import { ChatMessageData } from "@/services/chat-service";
import { ChatHeader } from "./ChatHeader";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { TypingIndicator } from "./TypingIndicator";
import { SupportedLanguage } from "@/hooks/use-translation";

interface ChatWindowProps {
  collegeName: string;
  messages: ChatMessageData[];
  isLoading: boolean;
  onSendMessage: (text: string) => void;
  onRegenerateAnswer?: () => void;
  onClearSession: () => void;
  currentLang: SupportedLanguage;
  onLanguageChange: (lang: SupportedLanguage) => void;
  onOpenSupport?: () => void;
  onOpenSwitchCollege?: () => void;
  onConfirmSwitch?: (targetCollegeId: string, pendingQuestion: string, messageId: string) => void;
  onStayWithCollege?: (messageId: string, currentCollegeName: string) => void;
}

export function ChatWindow({
  collegeName,
  messages,
  isLoading,
  onSendMessage,
  onRegenerateAnswer,
  onClearSession,
  currentLang,
  onLanguageChange,
  onOpenSupport,
  onOpenSwitchCollege,
  onConfirmSwitch,
  onStayWithCollege,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new messages or loading state change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0B0B0D] overflow-hidden">
      {/* Chat Header - only rendered when a college is connected */}
      <ChatHeader
        collegeName={collegeName}
        currentLang={currentLang}
        onLanguageChange={onLanguageChange}
        onClearSession={onClearSession}
        onOpenSupport={onOpenSupport}
        onOpenSwitchCollege={onOpenSwitchCollege}
      />

      {/* Messages Scroll View or Centered Welcome Screen */}
      <div className="flex-1 overflow-y-auto px-4 py-6 max-w-4xl w-full mx-auto flex flex-col">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center my-auto py-10 px-4">
            {/* Professional Education Illustration: Graduation Cap & Open Book */}
            <div className="relative mb-6 flex items-center justify-center">
              {/* Soft radial backdrop glow */}
              <div className="absolute w-36 h-36 rounded-full bg-gradient-to-tr from-[#6366F1]/20 to-[#8B5CF6]/20 blur-2xl pointer-events-none" />

              <svg
                width="140"
                height="140"
                viewBox="0 0 160 160"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className="relative drop-shadow-md"
              >
                <defs>
                  <linearGradient id="capGrad" x1="20" y1="30" x2="140" y2="70" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stopColor="#818CF8" />
                    <stop offset="100%" stopColor="#6366F1" />
                  </linearGradient>
                  <linearGradient id="bookLeft" x1="24" y1="85" x2="80" y2="135" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stopColor="#A5B4FC" />
                    <stop offset="100%" stopColor="#6366F1" />
                  </linearGradient>
                  <linearGradient id="bookRight" x1="80" y1="85" x2="136" y2="135" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stopColor="#818CF8" />
                    <stop offset="100%" stopColor="#4F46E5" />
                  </linearGradient>
                  <linearGradient id="accentGrad" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#C7D2FE" />
                    <stop offset="100%" stopColor="#818CF8" />
                  </linearGradient>
                </defs>

                {/* Subtle decorative sparkle stars */}
                <path d="M28 42L30 36L36 34L30 32L28 26L26 32L20 34L26 36L28 42Z" fill="#818CF8" opacity="0.6" />
                <path d="M136 50L137.5 45L142 43.5L137.5 42L136 37L134.5 42L130 43.5L134.5 45L136 50Z" fill="#A5B4FC" opacity="0.6" />

                {/* Graduation Cap (Mortarboard) */}
                {/* Cap base skull */}
                <path
                  d="M52 54C52 64 64 71 80 71C96 71 108 64 108 54V60C108 70 96 77 80 77C64 77 52 70 52 60V54Z"
                  fill="#4338CA"
                />

                {/* Cap top diamond */}
                <path
                  d="M80 30L134 50L80 70L26 50L80 30Z"
                  fill="url(#capGrad)"
                />

                {/* Cap center button */}
                <ellipse cx="80" cy="50" rx="4.5" ry="3" fill="#EEF2FF" />

                {/* Tassel cord & band */}
                <path
                  d="M80 50C95 52 118 60 120 72"
                  stroke="#C7D2FE"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
                {/* Tassel fringe */}
                <path
                  d="M117 72L123 72L124 84L116 84L117 72Z"
                  fill="#EEF2FF"
                />

                {/* Open Book Below Cap */}
                {/* Book back cover / spine shadows */}
                <path
                  d="M26 127C50 120 75 125 80 134C85 125 110 120 134 127V129C110 122 85 127 80 136C75 127 50 122 26 129V127Z"
                  fill="#312E81"
                />

                {/* Left Page (Curved Open) */}
                <path
                  d="M28 92C52 86 74 91 80 100V131C74 123 52 118 28 124V92Z"
                  fill="url(#bookLeft)"
                />
                {/* Right Page (Curved Open) */}
                <path
                  d="M80 100C86 91 108 86 132 92V124C108 118 86 123 80 131V100Z"
                  fill="url(#bookRight)"
                />

                {/* Spine Center Line */}
                <path
                  d="M80 100V131"
                  stroke="#312E81"
                  strokeWidth="2"
                  strokeLinecap="round"
                />

                {/* Text Lines on Left Page */}
                <path d="M38 100C50 97 64 99 70 103" stroke="#EEF2FF" strokeWidth="1.8" strokeLinecap="round" opacity="0.75" />
                <path d="M38 108C50 105 64 107 70 111" stroke="#EEF2FF" strokeWidth="1.8" strokeLinecap="round" opacity="0.75" />
                <path d="M38 116C48 113 58 115 66 118" stroke="#EEF2FF" strokeWidth="1.8" strokeLinecap="round" opacity="0.6" />

                {/* Text Lines on Right Page */}
                <path d="M90 103C96 99 110 97 122 100" stroke="#EEF2FF" strokeWidth="1.8" strokeLinecap="round" opacity="0.75" />
                <path d="M90 111C96 107 110 105 122 108" stroke="#EEF2FF" strokeWidth="1.8" strokeLinecap="round" opacity="0.75" />
                <path d="M94 118C102 115 112 113 122 116" stroke="#EEF2FF" strokeWidth="1.8" strokeLinecap="round" opacity="0.6" />
              </svg>
            </div>

            {/* Exact Required Welcome Heading */}
            <h1 className="text-2xl sm:text-3xl font-bold text-[#F5F5F5] tracking-tight mb-2">
              Which college information do you want?
            </h1>

            {/* Exact Required Welcome Subtitle */}
            <p className="text-sm text-[#A1A1AA] max-w-lg mx-auto leading-relaxed">
              Ask anything about your college, like fees, admission, facilities and more.
            </p>
          </div>
        ) : (
          <div className="flex-1">
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                onRegenerate={onRegenerateAnswer}
                lang={currentLang}
                onConfirmSwitch={onConfirmSwitch}
                onStayWithCollege={onStayWithCollege}
              />
            ))}
            {isLoading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Fixed Chat Input Form at Bottom */}
      <ChatInput
        onSendMessage={onSendMessage}
        isLoading={isLoading}
        lang={currentLang}
        placeholder="Ask a question about your college..."
      />
    </div>
  );
}
