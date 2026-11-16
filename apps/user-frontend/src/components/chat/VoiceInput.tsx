"use client";

import { useEffect } from "react";
import { Mic, MicOff, AlertCircle } from "lucide-react";
import { useVoice } from "@/hooks/use-voice";
import { SupportedLanguage } from "@/hooks/use-translation";

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  lang: SupportedLanguage;
}

export function VoiceInput({ onTranscript, lang }: VoiceInputProps) {
  const {
    isRecording,
    transcript,
    voiceError,
    isSupported,
    startRecording,
    stopRecording,
  } = useVoice();

  useEffect(() => {
    if (transcript) {
      onTranscript(transcript);
    }
  }, [transcript, onTranscript]);

  if (!isSupported) {
    return (
      <button
        type="button"
        disabled
        className="p-2.5 rounded-xl bg-[#1F1F23] border border-[#2A2A30] text-[#A1A1AA]/40 cursor-not-allowed"
        title="Speech recognition not supported in this browser"
      >
        <MicOff className="h-4 w-4" />
      </button>
    );
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => {
          if (isRecording) {
            stopRecording();
          } else {
            startRecording(lang);
          }
        }}
        className={`p-2.5 rounded-xl border transition flex items-center justify-center ${
          isRecording
            ? "bg-[#EF4444] border-[#EF4444] text-white animate-pulse"
            : "bg-[#1F1F23] border-[#2A2A30] text-[#A1A1AA] hover:text-[#F5F5F5] hover:border-[#6366F1]"
        }`}
        title={isRecording ? "Click to stop recording" : "Click to speak your question"}
      >
        <Mic className="h-4 w-4" />
      </button>

      {isRecording && (
        <div className="absolute bottom-12 left-1/2 -translate-x-1/2 px-3 py-1.5 rounded-lg bg-[#EF4444] text-white text-[11px] whitespace-nowrap shadow-lg flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-white animate-ping"></span>
          <span>Listening in {lang.toUpperCase()}...</span>
        </div>
      )}

      {voiceError && (
        <div className="absolute bottom-12 left-1/2 -translate-x-1/2 px-3 py-1.5 rounded-lg bg-[#EF4444]/90 text-white text-[11px] whitespace-nowrap shadow-lg flex items-center gap-1.5">
          <AlertCircle className="h-3 w-3" />
          <span>{voiceError}</span>
        </div>
      )}
    </div>
  );
}

