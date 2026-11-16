"use client";

import { useState, useEffect, useRef } from "react";
import { SupportedLanguage } from "./use-translation";

export function useVoice() {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        setIsSupported(true);
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;

        recognition.onresult = (event: any) => {
          let currentTranscript = "";
          for (let i = event.resultIndex; i < event.results.length; i++) {
            currentTranscript += event.results[i][0].transcript;
          }
          setTranscript(currentTranscript);
        };

        recognition.onerror = (event: any) => {
          setIsRecording(false);
          if (event.error === "not-allowed") {
            setVoiceError("Microphone access was denied. Please grant permission in browser settings.");
          } else if (event.error === "no-speech") {
            setVoiceError("No speech detected. Please speak clearly into your microphone.");
          } else {
            setVoiceError(`Voice error: ${event.error}`);
          }
        };

        recognition.onend = () => {
          setIsRecording(false);
        };

        recognitionRef.current = recognition;
      }
    }
  }, []);

  const startRecording = (lang: SupportedLanguage = "en") => {
    setVoiceError(null);
    setTranscript("");

    if (!recognitionRef.current) {
      setVoiceError("Speech recognition is not supported in this browser.");
      return;
    }

    try {
      const langCodes: Record<SupportedLanguage, string> = {
        en: "en-US",
        hi: "hi-IN",
        gu: "gu-IN",
      };
      recognitionRef.current.lang = langCodes[lang] || "en-US";
      recognitionRef.current.start();
      setIsRecording(true);
    } catch (err: any) {
      setVoiceError(err.message || "Failed to start microphone.");
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current && isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    }
  };

  const speak = (text: string, lang: SupportedLanguage = "en") => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      return;
    }

    // Stop existing speech if any
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    const langCodes: Record<SupportedLanguage, string> = {
      en: "en-US",
      hi: "hi-IN",
      gu: "gu-IN",
    };
    utterance.lang = langCodes[lang] || "en-US";
    utterance.rate = 1.0;

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
  };

  const stopSpeaking = () => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  };

  return {
    isRecording,
    transcript,
    voiceError,
    isSupported,
    isSpeaking,
    startRecording,
    stopRecording,
    speak,
    stopSpeaking,
  };
}

