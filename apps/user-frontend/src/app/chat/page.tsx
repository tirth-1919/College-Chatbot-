"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { chatService, ChatSessionData, ChatMessageData, generateUUID } from "@/services/chat-service";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { SupportModal } from "@/components/chat/SupportModal";
import { useTranslation, SupportedLanguage } from "@/hooks/use-translation";

const STORAGE_PREFIX = "campusai_chat_sessions_";

export default function ChatPage() {
  const router = useRouter();
  const { lang, changeLanguage } = useTranslation();

  const [collegeId, setCollegeId] = useState<string>("11111111-1111-1111-1111-111111111111");
  const [collegeName, setCollegeName] = useState<string>("Ahmedabad Institute of Technology");
  const [sessions, setSessions] = useState<ChatSessionData[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isSupportOpen, setIsSupportOpen] = useState(false);

  const activeSessionRef = useRef<string | null>(null);
  activeSessionRef.current = activeSessionId;

  const messagesRef = useRef<ChatMessageData[]>([]);
  messagesRef.current = messages;

  // Helper to save sessions and messages to localStorage
  const persistSessions = (cId: string, updatedSessions: ChatSessionData[]) => {
    try {
      localStorage.setItem(`${STORAGE_PREFIX}${cId}`, JSON.stringify(updatedSessions));
    } catch (e) {}
  };

  // 1. Resolve Active College Context
  useEffect(() => {
    const storedId = localStorage.getItem("selected_college_id");
    const storedName = localStorage.getItem("selected_college_name");

    const resolvedId = storedId || "11111111-1111-1111-1111-111111111111";
    const resolvedName = storedName || "Ahmedabad Institute of Technology";

    setCollegeId(resolvedId);
    setCollegeName(resolvedName);
  }, []);

  // Sync saved user preferences (multilingual support)
  useEffect(() => {
    chatService.getUserPreferences().then((res) => {
      if (res.success && res.data?.preferred_language) {
        const prefLang = res.data.preferred_language as SupportedLanguage;
        if (["en", "hi", "gu"].includes(prefLang) && prefLang !== lang) {
          changeLanguage(prefLang);
        }
      }
    });
  }, [changeLanguage, lang]);

  const handleLanguageChange = (newLang: SupportedLanguage) => {
    changeLanguage(newLang);
    chatService.updateUserPreferences(newLang);
  };

  // 2. Fetch Sessions for Active College
  const loadSessions = useCallback(async (cId: string) => {
    // If we already have active messages or sessions in memory, don't clobber them
    if (messagesRef.current.length > 0) {
      return;
    }

    // Check localStorage cache first
    let cachedSessions: ChatSessionData[] = [];
    try {
      const raw = localStorage.getItem(`${STORAGE_PREFIX}${cId}`);
      if (raw) {
        cachedSessions = JSON.parse(raw);
      }
    } catch (e) {}

    if (cachedSessions.length > 0) {
      setSessions(cachedSessions);
      const active = cachedSessions[0];
      setActiveSessionId(active.id);
      if (active.messages && active.messages.length > 0) {
        setMessages(active.messages);
      }
      return;
    }

    // Attempt backend load
    const res = await chatService.listSessions(cId);
    if (res.success && res.data && res.data.length > 0) {
      setSessions(res.data);
      setActiveSessionId(res.data[0].id);
      persistSessions(cId, res.data);
    } else {
      // Create initial active conversation session with valid UUID
      const newId = generateUUID();
      const localSession: ChatSessionData = {
        id: newId,
        college_id: cId,
        session_title: "New Conversation",
        language: lang,
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        messages: [],
      };
      const created = await chatService.createSession(cId, "New Conversation", lang);
      const initial = created.success && created.data ? created.data : localSession;
      setSessions([initial]);
      setActiveSessionId(newId);
      persistSessions(cId, [initial]);
    }
  }, [lang]);

  useEffect(() => {
    if (collegeId) {
      loadSessions(collegeId);
    }
  }, [collegeId, loadSessions]);

  // 3. Load Message History when activeSessionId changes manually
  useEffect(() => {
    if (!activeSessionId) return;

    const currentSession = sessions.find((s) => s.id === activeSessionId);
    if (currentSession && currentSession.messages && currentSession.messages.length > 0) {
      setMessages(currentSession.messages);
      return;
    }

    chatService.getSessionHistory(activeSessionId).then((res) => {
      if (res.success && res.data && res.data.messages && res.data.messages.length > 0) {
        setMessages(res.data.messages);
      }
    });
  }, [activeSessionId]);

  // 4. Send Message Handler (Guaranteed to execute and respond)
  const handleSendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    const currentCollegeId = collegeId || "11111111-1111-1111-1111-111111111111";
    setChatError(null);

    // Ensure we always have an active valid UUID session ID
    let currentSessionId = activeSessionRef.current;
    let currentSessions = [...sessions];

    if (!currentSessionId || currentSessions.length === 0) {
      currentSessionId = generateUUID();
      const newSession: ChatSessionData = {
        id: currentSessionId,
        college_id: currentCollegeId,
        session_title: trimmed.slice(0, 36) + (trimmed.length > 36 ? "..." : ""),
        language: lang,
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        messages: [],
      };
      currentSessions = [newSession, ...currentSessions];
      setActiveSessionId(currentSessionId);
    }

    // Create user message turn
    const userMsg: ChatMessageData = {
      id: generateUUID(),
      session_id: currentSessionId,
      sender_role: "user",
      message_text: trimmed,
      is_verified: false,
      answer_source_type: "OFFICIAL_WEBSITE",
      source_citations: [],
      token_count: trimmed.split(" ").length,
      created_at: new Date().toISOString(),
    };

    // Optimistically update message state
    const currentMsgs = messagesRef.current;
    const updatedWithUser = [...currentMsgs, userMsg];
    setMessages(updatedWithUser);
    setIsLoading(true);

    // Save user turn immediately into session state so it's persistent
    const updatedSessionsWithUser = currentSessions.map((s) => {
      if (s.id === currentSessionId) {
        return {
          ...s,
          session_title: s.session_title === "New Conversation" ? (trimmed.slice(0, 36) + (trimmed.length > 36 ? "..." : "")) : s.session_title,
          messages: updatedWithUser,
          updated_at: new Date().toISOString(),
        };
      }
      return s;
    });
    setSessions(updatedSessionsWithUser);
    persistSessions(currentCollegeId, updatedSessionsWithUser);

    try {
      const res = await chatService.sendMessage(currentSessionId, trimmed, lang, collegeName);
      setIsLoading(false);

      if (res.success && res.data) {
        const assistantMsg = res.data;
        const allMessages = [...updatedWithUser, assistantMsg];
        setMessages(allMessages);

        const refreshed = updatedSessionsWithUser.map((s) => {
          if (s.id === currentSessionId) {
            return {
              ...s,
              messages: allMessages,
              updated_at: new Date().toISOString(),
            };
          }
          return s;
        });

        setSessions(refreshed);
        persistSessions(currentCollegeId, refreshed);
      } else {
        setChatError(res.error || "Unable to send the message.");
      }
    } catch (err) {
      setIsLoading(false);
      setChatError(err instanceof Error ? err.message : "Unable to send the message.");
    }
  };

  // 5. Session Actions (New, Rename, Delete, Clear)
  const handleNewSession = async () => {
    const currentCollegeId = collegeId || "11111111-1111-1111-1111-111111111111";
    const res = await chatService.createSession(currentCollegeId, "New Conversation", lang);
    const newSessionId = (res.success && res.data) ? res.data.id : generateUUID();
    const newSession: ChatSessionData = {
      id: newSessionId,
      college_id: currentCollegeId,
      session_title: "New Conversation",
      language: lang,
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      messages: [],
    };
    const updated = [newSession, ...sessions];
    setSessions(updated);
    setActiveSessionId(newSession.id);
    setMessages([]);
    persistSessions(currentCollegeId, updated);
  };

  const handleRenameSession = async (id: string, newTitle: string) => {
    await chatService.renameSession(id, newTitle);
    const updated = sessions.map((s) => (s.id === id ? { ...s, session_title: newTitle } : s));
    setSessions(updated);
    if (collegeId) persistSessions(collegeId, updated);
  };

  const handleDeleteSession = async (id: string) => {
    await chatService.deleteSession(id);
    const remaining = sessions.filter((s) => s.id !== id);
    setSessions(remaining);
    if (collegeId) persistSessions(collegeId, remaining);

    if (activeSessionId === id) {
      if (remaining.length > 0) {
        setActiveSessionId(remaining[0].id);
        setMessages(remaining[0].messages || []);
      } else {
        handleNewSession();
      }
    }
  };

  const handleClearSession = () => {
    setMessages([]);
    if (activeSessionId && collegeId) {
      const updated = sessions.map((s) => (s.id === activeSessionId ? { ...s, messages: [] } : s));
      setSessions(updated);
      persistSessions(collegeId, updated);
    }
  };

  const handleRegenerate = () => {
    const lastUserMsg = [...messages].reverse().find((m) => m.sender_role === "user");
    if (lastUserMsg) {
      handleSendMessage(lastUserMsg.message_text);
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden bg-[#0B0B0D]">
      {/* Conversation History Sidebar */}
      <ChatSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={(id) => {
          setActiveSessionId(id);
          const s = sessions.find((item) => item.id === id);
          if (s && s.messages) setMessages(s.messages);
        }}
        onNewSession={handleNewSession}
        onRenameSession={handleRenameSession}
        onDeleteSession={handleDeleteSession}
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
      />

      {/* Main Chat Interface Window */}
      <ChatWindow
        collegeName={collegeName}
        messages={messages}
        isLoading={isLoading}
        onSendMessage={handleSendMessage}
        onRegenerateAnswer={handleRegenerate}
        onClearSession={handleClearSession}
        currentLang={lang}
        onLanguageChange={handleLanguageChange}
        onOpenSupport={() => setIsSupportOpen(true)}
      />
      {chatError && (
        <div
          role="alert"
          className="fixed bottom-5 right-5 z-50 max-w-md rounded-lg border border-red-500/40 bg-red-950/90 px-4 py-3 text-sm text-red-100 shadow-lg"
        >
          {chatError}
        </div>
      )}

      {/* College Support & Inquiry Modal */}
      <SupportModal
        collegeId={collegeId}
        sessionId={activeSessionId}
        isOpen={isSupportOpen}
        onClose={() => setIsSupportOpen(false)}
      />
    </div>
  );
}
