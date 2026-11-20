"use client";

import { useEffect, useRef } from "react";
import { ChatMessageData } from "@/services/chat-service";
import { ChatHeader } from "./ChatHeader";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { TypingIndicator } from "./TypingIndicator";
import { SuggestedQuestions } from "./SuggestedQuestions";
import { SupportedLanguage } from "@/hooks/use-translation";
import Link from "next/link";
import { Building2 } from "lucide-react";

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
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new messages or loading state change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0B0B0D] overflow-hidden">
      {/* Chat Header */}
      <ChatHeader
        collegeName={collegeName}
        currentLang={currentLang}
        onLanguageChange={onLanguageChange}
        onClearSession={onClearSession}
        onOpenSupport={onOpenSupport}
      />

      {/* Messages Scroll View */}
      <div className="flex-1 overflow-y-auto px-4 py-6 max-w-4xl w-full mx-auto">
        {messages.length === 0 ? (
          <div className="py-8">
            <div className="text-center max-w-md mx-auto mb-6">
              <h2 className="text-xl font-bold text-[#F5F5F5] mb-2">
                {collegeName ? `Ask ${collegeName} Anything` : "Choose a college to start"}
              </h2>
              <p className="text-xs text-[#A1A1AA] leading-relaxed">
                {collegeName
                  ? "Our AI answers are grounded strictly in the official website, verified admission notifications, and fee brochures."
                  : "Select an institution once. You can switch colleges anytime from the chat header or this page."}
              </p>
              {!collegeName && (
                <Link
                  href="/colleges"
                  className="mt-4 inline-flex items-center gap-2 rounded-lg bg-[#6366F1] px-4 py-2.5 text-xs font-semibold text-white hover:bg-[#4F46E5]"
                >
                  <Building2 className="h-4 w-4" />
                  Select College Institution
                </Link>
              )}
            </div>
            <SuggestedQuestions
              onSelect={onSendMessage}
              collegeName={collegeName}
            />
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                onRegenerate={onRegenerateAnswer}
                lang={currentLang}
              />
            ))}
            {isLoading && <TypingIndicator />}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      {/* Input Form */}
      <ChatInput
        onSendMessage={onSendMessage}
        isLoading={isLoading}
        lang={currentLang}
      />
    </div>
  );
}

