"use client";

import { useState, useEffect, useCallback } from "react";
import en from "@/locales/en.json";
import hi from "@/locales/hi.json";
import gu from "@/locales/gu.json";

export type SupportedLanguage = "en" | "hi" | "gu";

const translations: Record<SupportedLanguage, any> = {
  en,
  hi,
  gu,
};

export function useTranslation() {
  const [lang, setLang] = useState<SupportedLanguage>("en");

  useEffect(() => {
    const saved = localStorage.getItem("preferred_language") as SupportedLanguage;
    if (saved && ["en", "hi", "gu"].includes(saved)) {
      setLang(saved);
    }
  }, []);

  const changeLanguage = (newLang: SupportedLanguage) => {
    setLang(newLang);
    localStorage.setItem("preferred_language", newLang);
    window.dispatchEvent(new Event("languagechange"));
  };

  useEffect(() => {
    const handleLangChange = () => {
      const saved = localStorage.getItem("preferred_language") as SupportedLanguage;
      if (saved && ["en", "hi", "gu"].includes(saved)) {
        setLang(saved);
      }
    };
    window.addEventListener("languagechange", handleLangChange);
    return () => window.removeEventListener("languagechange", handleLangChange);
  }, []);

  const t = useCallback(
    (keyPath: string): string => {
      const keys = keyPath.split(".");
      let current: any = translations[lang];

      for (const k of keys) {
        if (current && typeof current === "object" && k in current) {
          current = current[k];
        } else {
          // Fallback to English
          let fallback: any = translations["en"];
          for (const fk of keys) {
            if (fallback && typeof fallback === "object" && fk in fallback) {
              fallback = fallback[fk];
            } else {
              return keyPath;
            }
          }
          return typeof fallback === "string" ? fallback : keyPath;
        }
      }

      return typeof current === "string" ? current : keyPath;
    },
    [lang]
  );

  return { lang, changeLanguage, t };
}

