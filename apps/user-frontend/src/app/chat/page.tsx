"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { chatService, ChatSessionData, ChatMessageData, generateUUID, hasVisitorToken } from "@/services/chat-service";
import { AUTH_SESSION_INVALID_KEY } from "@/lib/auth-session";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { SupportModal } from "@/components/chat/SupportModal";
import { useTranslation, SupportedLanguage } from "@/hooks/use-translation";

const STORAGE_PREFIX = "campusai_chat_sessions_";
const ACTIVE_SESSION_PREFIX = "campusai_chat_active_session_";

function detectRequestedCollege(prompt: string, currentCollegeName: string): string | null {
  const normalizedPrompt = prompt.toLowerCase();
  const normalizedCurrent = currentCollegeName.toLowerCase();

  const colleges: Array<{ name: string; aliases: string[] }> = [
    {
      name: "Ahmedabad Institute of Technology",
      aliases: ["ait", "ahmedabad institute of technology"],
    },
    {
      name: "RC Technical Institute",
      aliases: ["rcti", "rc technical institute", "r.c. technical institute"],
    },
  ];

  for (const college of colleges) {
    if (normalizedCurrent.includes(college.name.toLowerCase())) continue;
    if (college.aliases.some((alias) => normalizedPrompt.includes(alias))) {
      return college.name;
    }
  }
  return null;
}

function hasAuthenticatedUser(): boolean {
  return typeof window !== "undefined" && Boolean(
    localStorage.getItem("auth_token") && !localStorage.getItem(AUTH_SESSION_INVALID_KEY)
  );
}

export default function ChatPage() {
  const router = useRouter();
  const { lang, changeLanguage } = useTranslation();

  const [collegeId, setCollegeId] = useState<string>("");
  const [collegeName, setCollegeName] = useState<string>("");
  const [collegeContextReady, setCollegeContextReady] = useState(false);
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

  const collegeIdRef = useRef("");
  const historyLoadSessionRef = useRef<string | null>(null);
  const loadingCollegeIdsRef = useRef(new Set<string>());

  useEffect(() => {
    const redirectToLogin = () => {
      const destination = `${window.location.pathname}${window.location.search}`;
      router.replace(`/login?session_expired=1&redirect=${encodeURIComponent(destination)}`);
    };

    window.addEventListener("auth-session-invalid", redirectToLogin);
    if (localStorage.getItem(AUTH_SESSION_INVALID_KEY)) {
      redirectToLogin();
    }

    return () => window.removeEventListener("auth-session-invalid", redirectToLogin);
  }, [router]);

  // Helper to save sessions and messages to localStorage
  const persistSessions = (cId: string, updatedSessions: ChatSessionData[]) => {
    try {
      const key = `${STORAGE_PREFIX}${cId}`;
      const previous = JSON.parse(localStorage.getItem(key) || "[]") as ChatSessionData[];
      const activeIds = new Set(updatedSessions.map((session) => session.id));
      const unavailable = Array.isArray(previous)
        ? previous.filter((session) => session.local_state === "unavailable" && !activeIds.has(session.id))
        : [];
      localStorage.setItem(key, JSON.stringify([...unavailable, ...updatedSessions]));
    } catch (e) {}
  };

  const persistActiveSession = (cId: string, sessionId: string | null) => {
    try {
      const key = `${ACTIVE_SESSION_PREFIX}${cId}`;
      if (sessionId) localStorage.setItem(key, sessionId);
      else localStorage.removeItem(key);
    } catch (e) {}
  };

  const markSessionUnavailable = (cId: string, sessionId: string) => {
    try {
      const key = `${STORAGE_PREFIX}${cId}`;
      const cached = JSON.parse(localStorage.getItem(key) || "[]") as ChatSessionData[];
      if (!Array.isArray(cached)) return;
      const updated = cached.map((session) =>
        session.id === sessionId ? { ...session, local_state: "unavailable" as const } : session
      );
      localStorage.setItem(key, JSON.stringify(updated));
    } catch (e) {}
    sessionStorage.removeItem(`campusai_chat_visitor_${sessionId}`);
  };

  const withRequestId = (message: string, requestId?: string) =>
    requestId ? `${message} (Request ID: ${requestId})` : message;

  // 1. Resolve the active college and discard state from the previous tenant.
  useEffect(() => {
    const applySelectedCollege = () => {
      const nextId = localStorage.getItem("selected_college_id") || "";
      const nextName = localStorage.getItem("selected_college_name") || "";

      if (collegeIdRef.current !== nextId) {
        collegeIdRef.current = nextId;
        activeSessionRef.current = null;
        historyLoadSessionRef.current = null;
        messagesRef.current = [];
        setChatError(null);
        setSessions([]);
        setActiveSessionId(null);
        setMessages([]);
      }
      setCollegeId(nextId);
      setCollegeName(nextName);
      setCollegeContextReady(true);
    };

    applySelectedCollege();
    window.addEventListener("selected-college-change", applySelectedCollege);
    window.addEventListener("storage", applySelectedCollege);
    return () => {
      window.removeEventListener("selected-college-change", applySelectedCollege);
      window.removeEventListener("storage", applySelectedCollege);
    };
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
    if (!cId || collegeIdRef.current !== cId) return;
    if (loadingCollegeIdsRef.current.has(cId)) return;
    loadingCollegeIdsRef.current.add(cId);
    try {
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

    cachedSessions = Array.isArray(cachedSessions)
      ? cachedSessions.filter((session) => session.college_id === cId && session.local_state !== "unavailable")
      : [];
    const authenticated = hasAuthenticatedUser();
    if (!authenticated && cachedSessions.length > 0) {
      const preferredId = localStorage.getItem(`${ACTIVE_SESSION_PREFIX}${cId}`);
      const candidates = [...cachedSessions].sort((a, b) =>
        a.id === preferredId ? -1 : b.id === preferredId ? 1 : 0
      );
      const verified: ChatSessionData[] = [];
      for (const candidate of candidates) {
        if (!hasVisitorToken(candidate.id)) {
          markSessionUnavailable(cId, candidate.id);
          continue;
        }
        const history = await chatService.getSessionHistory(candidate.id, cId);
        if (collegeIdRef.current !== cId) return;
        if (history.success && history.data?.id === candidate.id && history.data.college_id === cId) {
          verified.push({ ...candidate, ...history.data, messages: history.data.messages || [] });
          continue;
        }
        if (history.status === 403 || history.status === 404) {
          markSessionUnavailable(cId, candidate.id);
          continue;
        }
        setChatError(withRequestId(history.error || "Unable to verify the saved conversation.", history.requestId));
        return;
      }
      if (verified.length > 0) {
        const active = verified.find((session) => session.id === preferredId) || verified[0];
        setSessions(verified);
        historyLoadSessionRef.current = active.id;
        setActiveSessionId(active.id);
        persistActiveSession(cId, active.id);
        setMessages(active.messages || []);
        persistSessions(cId, verified);
        return;
      }
    }

    if (authenticated) {
      const res = await chatService.listSessions(cId);
      if (collegeIdRef.current !== cId) return;
      if (!res.success || !res.data) {
        setChatError(withRequestId(res.error || "Unable to load chat sessions.", res.requestId));
        return;
      }
      if (res.data.length > 0) {
        const preferredId = localStorage.getItem(`${ACTIVE_SESSION_PREFIX}${cId}`);
        const active = res.data.find((session) => session.id === preferredId) || res.data[0];
        setSessions(res.data);
        setActiveSessionId(active.id);
        persistActiveSession(cId, active.id);
        setMessages([]);
        persistSessions(cId, res.data);
        return;
      }
    }

    const created = await chatService.createSession(cId, "New Conversation", lang);
    if (collegeIdRef.current !== cId) return;
    if (!created.success || !created.data) {
      setChatError(withRequestId(created.error || "Unable to create a chat session.", created.requestId));
      return;
    }
    const initial = { ...created.data, messages: [] };
    setSessions([initial]);
    setActiveSessionId(initial.id);
    persistActiveSession(cId, initial.id);
    setMessages([]);
    persistSessions(cId, [initial]);
    } finally {
      loadingCollegeIdsRef.current.delete(cId);
    }
  }, [lang]);

  useEffect(() => {
    if (collegeContextReady && collegeId) {
      loadSessions(collegeId);
    }
  }, [collegeContextReady, collegeId, loadSessions]);

  // 3. Load Message History when activeSessionId changes manually
  useEffect(() => {
    if (!activeSessionId) return;

    const currentSession = sessions.find((s) => s.id === activeSessionId);
    if (currentSession && currentSession.college_id !== collegeId) {
      setChatError("This conversation belongs to a different college. Select a current-college conversation.");
      return;
    }

    if (historyLoadSessionRef.current === activeSessionId) return;
    historyLoadSessionRef.current = activeSessionId;
    const requestedCollegeId = collegeId;
    chatService.getSessionHistory(activeSessionId, requestedCollegeId).then((res) => {
      if (collegeIdRef.current !== requestedCollegeId || activeSessionRef.current !== activeSessionId) return;
      if (res.success && res.data?.id === activeSessionId && res.data.college_id === requestedCollegeId) {
        setMessages(res.data.messages || []);
        return;
      }
      if (res.status === 403 || res.status === 404) {
        markSessionUnavailable(requestedCollegeId, activeSessionId);
        const remaining = sessions.filter((session) => session.id !== activeSessionId);
        setSessions(remaining);
        persistSessions(requestedCollegeId, remaining);
        setActiveSessionId(null);
        persistActiveSession(requestedCollegeId, null);
        setMessages([]);
        setChatError("This conversation is no longer available. Start a new chat to continue.");
      } else {
        historyLoadSessionRef.current = null;
        setChatError(withRequestId(res.error || "Unable to reload this conversation.", res.requestId));
      }
    });
  }, [activeSessionId, sessions, collegeId]);

  // 4. Send Message Handler (Guaranteed to execute and respond)
  const handleSendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!collegeContextReady || !collegeId || !trimmed) {
      if (collegeContextReady && !collegeId) setChatError("Select a college before starting a chat.");
      return;
    }

    const currentCollegeId = collegeId;
    setChatError(null);

    let currentSessions = sessions.filter((session) =>
      session.college_id === currentCollegeId && session.local_state !== "unavailable"
    );
    let currentSessionId = currentSessions.some((session) => session.id === activeSessionRef.current)
      ? activeSessionRef.current
      : null;

    const activeSessionHasAccess = currentSessionId &&
      (hasAuthenticatedUser() || hasVisitorToken(currentSessionId));
    if (!currentSessionId || currentSessions.length === 0 || !activeSessionHasAccess) {
      const title = trimmed.slice(0, 36) + (trimmed.length > 36 ? "..." : "");
      const created = await chatService.createSession(currentCollegeId, title, lang);
      if (collegeIdRef.current !== currentCollegeId) return;
      if (!created.success || !created.data) {
        setChatError(withRequestId(created.error || "Unable to create a chat session.", created.requestId));
        return;
      }
      const newSession: ChatSessionData = { ...created.data, messages: [] };
      currentSessionId = newSession.id;
      currentSessions = [newSession, ...currentSessions];
      persistActiveSession(currentCollegeId, newSession.id);
      setActiveSessionId(currentSessionId);
      setMessages([]);
      persistSessions(currentCollegeId, currentSessions);
    }
    if (!currentSessionId) return;

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

    const currentMsgs = messagesRef.current;
    const updatedWithUser = [...currentMsgs, userMsg];
    setMessages(updatedWithUser);
    setIsLoading(true);

    const sessionCollegeId = currentCollegeId;

    try {
      const res = await chatService.sendMessage(currentSessionId, trimmed, sessionCollegeId, lang, collegeName);
      setIsLoading(false);
      if (collegeIdRef.current !== currentCollegeId) return;

      if (res.success && res.data) {
        let assistantMsg = res.data;
        if (assistantMsg.session_id !== currentSessionId) {
          setMessages(currentMsgs);
          setChatError("The server returned a response for a different chat session.");
          return;
        }
        const requestedCollege = detectRequestedCollege(trimmed, collegeName);
        if (requestedCollege) {
          assistantMsg = {
            ...assistantMsg,
            message_text:
              `${assistantMsg.message_text}\n\n__CAMPUSAI_SWITCH_COLLEGE__:${requestedCollege}`,
          };
        }
        const allMessages = [...updatedWithUser, assistantMsg];
        setMessages(allMessages);

        const refreshed = currentSessions.map((s) => {
          if (s.id === currentSessionId) {
            return {
              ...s,
              session_title: s.session_title === "New Conversation"
                ? (trimmed.slice(0, 36) + (trimmed.length > 36 ? "..." : ""))
                : s.session_title,
              messages: allMessages,
              updated_at: new Date().toISOString(),
            };
          }
          return s;
        });

        setSessions(refreshed);
        persistSessions(currentCollegeId, refreshed);
      } else {
        setMessages(currentMsgs);
        if (res.status === 403 || res.status === 404) {
          markSessionUnavailable(currentCollegeId, currentSessionId);
          const remaining = currentSessions.filter((session) => session.id !== currentSessionId);
          setSessions(remaining);
          persistSessions(currentCollegeId, remaining);
          setActiveSessionId(null);
          persistActiveSession(currentCollegeId, null);
          setChatError("This conversation is no longer available. Start a new chat to continue.");
        } else {
          setChatError(withRequestId(res.error || "Unable to send the message.", res.requestId));
        }
      }
    } catch (err) {
      setIsLoading(false);
      setMessages(currentMsgs);
      setChatError(err instanceof Error ? err.message : "Unable to send the message.");
    }
  };

  // 5. Session Actions (New, Rename, Delete, Clear)
  const handleNewSession = async () => {
    if (!collegeContextReady || !collegeId) return;
    const currentCollegeId = collegeId;
    setChatError(null);
    const res = await chatService.createSession(currentCollegeId, "New Conversation", lang);
    if (collegeIdRef.current !== currentCollegeId) return;
    if (!res.success || !res.data) {
      setChatError(withRequestId(res.error || "Unable to create a chat session.", res.requestId));
      return;
    }
    const newSession: ChatSessionData = { ...res.data, messages: [] };
    const updated = [newSession, ...sessions.filter((session) => session.college_id === currentCollegeId)];
    setSessions(updated);
    setActiveSessionId(newSession.id);
    setMessages([]);
    persistActiveSession(currentCollegeId, newSession.id);
    persistSessions(currentCollegeId, updated);
  };

  const handleRenameSession = async (id: string, newTitle: string) => {
    const targetSession = sessions.find((session) => session.id === id);
    if (!targetSession || targetSession.college_id !== collegeId) {
      setChatError("This conversation does not belong to the selected college.");
      return;
    }
    const result = await chatService.renameSession(id, newTitle, collegeId);
    if (!result.success) {
      setChatError(result.error || "Unable to rename the chat session.");
      return;
    }
    const updated = sessions.map((s) => (s.id === id ? { ...s, session_title: newTitle } : s));
    setSessions(updated);
    if (collegeId) persistSessions(collegeId, updated);
  };

  const handleDeleteSession = async (id: string) => {
    const targetSession = sessions.find((session) => session.id === id);
    if (!targetSession || targetSession.college_id !== collegeId) {
      setChatError("This conversation does not belong to the selected college.");
      return;
    }
    const result = await chatService.deleteSession(id, collegeId);
    if (!result.success) {
      setChatError(result.error || "Unable to delete the chat session.");
      return;
    }
    const remaining = sessions.filter((s) => s.id !== id);
    setSessions(remaining);
    if (collegeId) persistSessions(collegeId, remaining);

    if (activeSessionId === id) {
      if (remaining.length > 0) {
        setActiveSessionId(remaining[0].id);
        persistActiveSession(collegeId, remaining[0].id);
        setMessages([]);
      } else {
        persistActiveSession(collegeId, null);
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
          const selectedSession = sessions.find((session) => session.id === id);
          if (!selectedSession || selectedSession.college_id !== collegeId) return;
          if (activeSessionRef.current === id) return;
          setActiveSessionId(id);
          persistActiveSession(collegeId, id);
          setMessages([]);
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
      {collegeContextReady && !collegeId && (
        <div role="alert" className="fixed bottom-5 right-5 z-50 rounded-lg border border-amber-500/40 bg-amber-950/90 px-4 py-3 text-sm text-amber-100 shadow-lg">
          Select a college before starting a chat.
        </div>
      )}
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
