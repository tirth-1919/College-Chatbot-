"use client";

import { useState, useRef, useEffect } from "react";
import { Send, CornerDownLeft } from "lucide-react";
import { VoiceInput } from "./VoiceInput";
import { SupportedLanguage } from "@/hooks/use-translation";

interface ChatInputProps {
  onSendMessage: (text: string) => void;
  isLoading: boolean;
  lang: SupportedLanguage;
  placeholder?: string;
}

export function ChatInput({
  onSendMessage,
  isLoading,
  lang,
  placeholder = "Ask any question about admissions, fees, syllabus, or hostel...",
}: ChatInputProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!text.trim() || isLoading) return;
    onSendMessage(text.trim());
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleVoiceTranscript = (transcript: string) => {
    setText(transcript);
  };

  // Auto-resize textarea up to 150px
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [text]);

  return (
    <div className="p-4 border-t border-[#2A2A30] bg-[#111114] shrink-0">
      <form onSubmit={handleSubmit} className="flex items-end gap-2 max-w-4xl mx-auto">
        {/* Voice Input Microphone */}
        <VoiceInput onTranscript={handleVoiceTranscript} lang={lang} />

        {/* Text Input Box */}
        <div className="relative flex-1 rounded-2xl border border-[#2A2A30] bg-[#1F1F23] focus-within:border-[#6366F1] transition">
          <textarea
            ref={textareaRef}
            rows={1}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading}
            className="w-full pl-4 pr-10 py-3 bg-transparent text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 resize-none focus:outline-none"
          />
          <div className="absolute right-3 bottom-3 text-[10px] text-[#A1A1AA] hidden sm:flex items-center gap-1 opacity-40">
            <span>Enter</span>
            <CornerDownLeft className="h-3 w-3" />
          </div>
        </div>

        {/* Send Button */}
        <button
          type="submit"
          disabled={!text.trim() || isLoading}
          className="p-3 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] text-white disabled:opacity-30 transition flex items-center justify-center shrink-0 shadow-md shadow-[#6366F1]/20"
          title="Send inquiry"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
      <div className="text-center text-[11px] text-[#A1A1AA]/60 mt-2">
        CampusAI provides verified college facts. Never rely on unverified guidance for official admission payments.
      </div>
    </div>
  );
}

