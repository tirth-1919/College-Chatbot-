"use client";

import { useState, useRef, useEffect } from "react";
import { Send, CornerDownLeft, Paperclip, X, FileText } from "lucide-react";
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
  placeholder = "Ask a question about your college...",
}: ChatInputProps) {
  const [text, setText] = useState("");
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if ((!text.trim() && !attachedFile) || isLoading) return;
    
    let submission = text.trim();
    if (attachedFile) {
      submission = submission
        ? `${submission} [Attached Document: ${attachedFile.name}]`
        : `Please analyze this attached document: ${attachedFile.name}`;
    }

    onSendMessage(submission);
    setText("");
    setAttachedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
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
    setText((prev) => (prev ? `${prev} ${transcript}` : transcript));
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setAttachedFile(e.target.files[0]);
    }
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
      {/* Attached File Preview Pill */}
      {attachedFile && (
        <div className="max-w-4xl mx-auto mb-2 flex items-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-xs text-[#A1A1AA]">
            <FileText className="h-3.5 w-3.5 text-[#6366F1]" />
            <span className="font-medium text-[#F5F5F5] truncate max-w-xs">{attachedFile.name}</span>
            <span className="text-[10px] text-[#A1A1AA]">({(attachedFile.size / 1024).toFixed(0)} KB)</span>
            <button
              type="button"
              onClick={() => {
                setAttachedFile(null);
                if (fileInputRef.current) fileInputRef.current.value = "";
              }}
              className="p-0.5 rounded hover:bg-[#2A2A30] text-[#A1A1AA] hover:text-[#EF4444] transition"
              title="Remove attachment"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex items-end gap-2 max-w-4xl mx-auto">
        {/* Hidden File Input for Attachment */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.txt"
          onChange={handleFileSelect}
          className="hidden"
        />

        {/* Attachment Button */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isLoading}
          className="p-3 rounded-xl border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-[#A1A1AA] hover:text-[#F5F5F5] transition flex items-center justify-center shrink-0 disabled:opacity-40"
          title="Attach document or syllabus"
        >
          <Paperclip className="h-4 w-4" />
        </button>

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
          disabled={(!text.trim() && !attachedFile) || isLoading}
          className="p-3 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] text-white disabled:opacity-30 transition flex items-center justify-center shrink-0 shadow-md shadow-[#6366F1]/20"
          title="Send question"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
      <div className="text-center text-[11px] text-[#A1A1AA]/60 mt-2">
        AI FAQ Colleges Chatbot provides verified college facts. Never rely on unverified guidance for official admission payments.
      </div>
    </div>
  );
}
