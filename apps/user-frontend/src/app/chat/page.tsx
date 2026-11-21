"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  chatService,
  ChatSessionData,
  ChatMessageData,
  generateUUID,
  hasVisitorToken,
} from "@/services/chat-service";
import { collegeService } from "@/services/college-service";
import { College } from "@/types/college";
import { AUTH_SESSION_INVALID_KEY } from "@/lib/auth-session";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { SupportModal } from "@/components/chat/SupportModal";
import { SwitchCollegeModal } from "@/components/chat/SwitchCollegeModal";
import { useTranslation, SupportedLanguage } from "@/hooks/use-translation";

const STORAGE_PREFIX = "campusai_chat_sessions_";
const ACTIVE_SESSION_PREFIX = "campusai_chat_active_session_";

function cleanToken(str: string): string {
  return str.toLowerCase().replace(/['".,\/#!$%\^&\*;:{}=\-_`~()]/g, " ").replace(/\s+/g, " ").trim();
}

function detectCollegeInText(prompt: string, colleges: College[]): College | null {
  const norm = cleanToken(prompt);
  const words = norm.split(" ").filter(Boolean);

  for (const college of colleges) {
    const colNorm = cleanToken(college.name);
    // 1. Direct substring match of full college name
    if (norm.includes(colNorm)) {
      return college;
    }

    // 2. Acronym matching: initials of college name (e.g. "ait", "rcti")
    const initials = colNorm.split(" ").map((w) => w[0]).join("");
    if (words.includes(initials)) {
      return college;
    }

    // 3. Slug matching (e.g. "ait", "rcti")
    if (college.slug && words.includes(college.slug.toLowerCase())) {
      return college;
    }

    // 4. Common known aliases
    if (colNorm.includes("ahmedabad institute") && (words.includes("ait") || norm.includes("ahmedabad institute"))) {
      return college;
    }
    if (
      (colNorm.includes("rc technical") || colNorm.includes("r c technical")) &&
      (words.includes("rcti") || norm.includes("rc technical") || norm.includes("r c technical"))
    ) {
      return college;
    }
  }
  return null;
}

function isPureCollegeSelection(prompt: string, college: College): boolean {
  const norm = cleanToken(prompt);
  const colNorm = cleanToken(college.name);
  const initials = colNorm.split(" ").map((w) => w[0]).join("");
  const ignoredTokens = new Set([
    "hi", "hello", "hey", "connect", "select", "switch", "to", "info", "information",
    "about", "please", "college", "institute", "campus", "start", "with"
  ]);

  const tokens = norm.split(" ").filter((w) => {
    if (colNorm.includes(w)) return false;
    if (w === initials) return false;
    if (college.slug && w === college.slug.toLowerCase()) return false;
    if (ignoredTokens.has(w)) return false;
    return true;
  });

  return tokens.length === 0;
}

function hasAuthenticatedUser(): boolean {
  return typeof window !== "undefined" && Boolean(
    localStorage.getItem("auth_token") && !localStorage.getItem(AUTH_SESSION_INVALID_KEY)
  );
}

export default function ChatPage() {
  const router = useRouter();
  const { lang, changeLanguage } = useTranslation();

  const [colleges, setColleges] = useState<College[]>([]);
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
  const [isSwitchCollegeOpen, setIsSwitchCollegeOpen] = useState(false);

  const activeSessionRef = useRef<string | null>(null);
  activeSessionRef.current = activeSessionId;

  const messagesRef = useRef<ChatMessageData[]>([]);
  messagesRef.current = messages;

  const collegeIdRef = useRef("");
  collegeIdRef.current = collegeId;

  const collegesRef = useRef<College[]>([]);
  collegesRef.current = colleges;

  const historyLoadSessionRef = useRef<string | null>(null);
  const loadingCollegeIdsRef = useRef(new Set<string>());
  const initialLoadedRef = useRef(false);

  // Fetch registered colleges directory on mount
  useEffect(() => {
    collegeService.getColleges(true).then((res) => {
      if (res.success && res.data) {
        setColleges(res.data);
      }
    });
  }, []);

  // Redirect expired sessions
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

  // Session persistence helpers
  const persistSessions = (cId: string, updatedSessions: ChatSessionData[]) => {
    if (!cId) return;
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
    if (!cId) return;
    try {
      const key = `${ACTIVE_SESSION_PREFIX}${cId}`;
      if (sessionId) localStorage.setItem(key, sessionId);
      else localStorage.removeItem(key);
    } catch (e) {}
  };

  const markSessionUnavailable = (cId: string, sessionId: string) => {
    if (!cId) return;
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

  // Check saved college on mount (without forcing default or showing warning banner)
  useEffect(() => {
    const applySelectedCollege = () => {
      const savedId = localStorage.getItem("selected_college_id") || "";
      const savedName = localStorage.getItem("selected_college_name") || "";
      if (savedId && savedName) {
        setCollegeId(savedId);
        setCollegeName(savedName);
      }
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

  // Fetch Sessions for Active College
  const loadSessions = useCallback(async (cId: string) => {
    if (!cId) return;
    if (loadingCollegeIdsRef.current.has(cId)) return;
    loadingCollegeIdsRef.current.add(cId);

    try {
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
          return;
        }
        if (verified.length > 0) {
          const active = verified.find((session) => session.id === preferredId) || verified[0];
          setSessions(verified);
          historyLoadSessionRef.current = active.id;
          setActiveSessionId(active.id);
          persistActiveSession(cId, active.id);
          // Only auto-load messages into screen on initial page mount
          if (!initialLoadedRef.current) {
            initialLoadedRef.current = true;
            if (messagesRef.current.length === 0) {
              setMessages(active.messages || []);
            }
          }
          persistSessions(cId, verified);
          return;
        }
      }

      if (authenticated) {
        const res = await chatService.listSessions(cId);
        if (collegeIdRef.current !== cId) return;
        if (res.success && res.data && res.data.length > 0) {
          const preferredId = localStorage.getItem(`${ACTIVE_SESSION_PREFIX}${cId}`);
          const active = res.data.find((session) => session.id === preferredId) || res.data[0];
          setSessions(res.data);
          setActiveSessionId(active.id);
          persistActiveSession(cId, active.id);

          // Only auto-load messages into screen on initial page mount
          if (!initialLoadedRef.current) {
            initialLoadedRef.current = true;
            if (messagesRef.current.length === 0) {
              historyLoadSessionRef.current = active.id;
              const history = await chatService.getSessionHistory(active.id, cId);
              if (collegeIdRef.current === cId && history.success && history.data?.messages) {
                setMessages(history.data.messages);
              }
            }
          }
          persistSessions(cId, res.data);
        }
      }
    } finally {
      loadingCollegeIdsRef.current.delete(cId);
    }
  }, []);

  // Handle active college changes — always keep chat history on screen
  const prevCollegeIdRef = useRef<string>("");

  useEffect(() => {
    if (!collegeContextReady || !collegeId) return;

    if (prevCollegeIdRef.current && prevCollegeIdRef.current !== collegeId) {
      loadingCollegeIdsRef.current.delete(collegeId);
      historyLoadSessionRef.current = null;
      // Do NOT wipe messages here — always keep visible chat history on screen
    }

    prevCollegeIdRef.current = collegeId;
    loadSessions(collegeId);
  }, [collegeContextReady, collegeId, loadSessions]);

  // Load Message History when activeSessionId changes
  useEffect(() => {
    if (!activeSessionId || !collegeId) return;

    const currentSession = sessions.find((s) => s.id === activeSessionId);
    if (currentSession && currentSession.college_id !== collegeId) {
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
      } else {
        historyLoadSessionRef.current = null;
      }
    });
  }, [activeSessionId, sessions, collegeId]);

  // Connect current conversation to a target college
  const connectToCollege = async (targetCollege: College, pendingQuestion?: string) => {
    setChatError(null);
    setCollegeId(targetCollege.id);
    setCollegeName(targetCollege.name);
    localStorage.setItem("selected_college_id", targetCollege.id);
    localStorage.setItem("selected_college_name", targetCollege.name);
    window.dispatchEvent(new Event("selected-college-change"));

    const title = pendingQuestion
      ? pendingQuestion.slice(0, 36) + (pendingQuestion.length > 36 ? "..." : "")
      : `Conversation with ${targetCollege.name}`;

    const created = await chatService.createSession(targetCollege.id, title, lang);
    if (!created.success || !created.data) {
      setChatError(withRequestId(created.error || "Unable to start conversation session.", created.requestId));
      return null;
    }

    const newSession: ChatSessionData = { ...created.data, messages: [] };
    let cachedTargetSessions: ChatSessionData[] = [];
    try {
      const raw = localStorage.getItem(`${STORAGE_PREFIX}${targetCollege.id}`);
      if (raw) cachedTargetSessions = JSON.parse(raw);
    } catch (e) {}
    if (!Array.isArray(cachedTargetSessions)) cachedTargetSessions = [];

    const updatedSessions = [newSession, ...cachedTargetSessions.filter((s) => s.id !== newSession.id)];
    setSessions(updatedSessions);
    setActiveSessionId(newSession.id);
    persistActiveSession(targetCollege.id, newSession.id);
    persistSessions(targetCollege.id, updatedSessions);

    return newSession.id;
  };

  // Main Send Message Handler with Automatic College Detection and Switching
  const handleSendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setChatError(null);

    // Case 1: No college is currently connected
    if (!collegeId) {
      const detectedCollege = detectCollegeInText(trimmed, colleges);

      // Append user's question first
      const userMsgId = generateUUID();
      const userMsg: ChatMessageData = {
        id: userMsgId,
        session_id: activeSessionRef.current || "pending",
        sender_role: "user",
        message_text: trimmed,
        is_verified: false,
        answer_source_type: "OFFICIAL_WEBSITE",
        source_citations: [],
        token_count: trimmed.split(" ").length,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);

      // If college name was detected in user's query:
      if (detectedCollege) {
        setIsLoading(true);
        const newSessionId = await connectToCollege(detectedCollege, trimmed);
        if (!newSessionId) {
          setIsLoading(false);
          return;
        }

        userMsg.session_id = newSessionId;

        // If user typed only the college name / greeting:
        if (isPureCollegeSelection(trimmed, detectedCollege)) {
          setIsLoading(false);
          const welcomeMsg: ChatMessageData = {
            id: generateUUID(),
            session_id: newSessionId,
            sender_role: "assistant",
            message_text: `Connected to **${detectedCollege.name}**. Ask anything about your college, like fees, admission, facilities and more.`,
            is_verified: true,
            answer_source_type: "ADMIN_VERIFIED",
            source_citations: [],
            token_count: 24,
            created_at: new Date().toISOString(),
          };
          const allMsgs = [userMsg, welcomeMsg];
          setMessages(allMsgs);
          const refreshed = sessions.map((s) =>
            s.id === newSessionId ? { ...s, messages: allMsgs } : s
          );
          setSessions(refreshed);
          persistSessions(detectedCollege.id, refreshed);
          return;
        }

        // User asked a specific question containing the college name
        try {
          const res = await chatService.sendMessage(newSessionId, trimmed, detectedCollege.id, lang, detectedCollege.name);
          setIsLoading(false);
          if (res.success && res.data) {
            const assistantMsg = res.data;
            const allMsgs = [userMsg, assistantMsg];
            setMessages(allMsgs);
            const refreshed = sessions.map((s) =>
              s.id === newSessionId ? { ...s, messages: allMsgs } : s
            );
            setSessions(refreshed);
            persistSessions(detectedCollege.id, refreshed);
          } else {
            setChatError(withRequestId(res.error || "Unable to get an answer.", res.requestId));
          }
        } catch (err: any) {
          setIsLoading(false);
          setChatError(err?.message || "Failed to communicate with college knowledge base.");
        }
        return;
      }

      // No college detected and no college connected -> Ask user to clarify
      const promptClarifyMsg: ChatMessageData = {
        id: generateUUID(),
        session_id: "pending",
        sender_role: "assistant",
        message_text: "Which college information do you want? Please specify the name of your college (such as **Ahmedabad Institute of Technology** or **RC Technical Institute**), and I'll be glad to help.",
        is_verified: false,
        answer_source_type: "AI_GUIDANCE",
        source_citations: [],
        token_count: 30,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, promptClarifyMsg]);
      return;
    }

    // Case 2: A college IS already connected
    const currentCollegeId = collegeId;
    const currentCollegeName = collegeName;
    const detectedDifferentCollege = detectCollegeInText(trimmed, colleges);

    // If query is about a DIFFERENT registered college:
    if (detectedDifferentCollege && detectedDifferentCollege.id !== currentCollegeId) {
      const userMsg: ChatMessageData = {
        id: generateUUID(),
        session_id: activeSessionRef.current || "session",
        sender_role: "user",
        message_text: trimmed,
        is_verified: false,
        answer_source_type: "OFFICIAL_WEBSITE",
        source_citations: [],
        token_count: trimmed.split(" ").length,
        created_at: new Date().toISOString(),
      };

      const switchConfirmMsg: ChatMessageData = {
        id: generateUUID(),
        session_id: activeSessionRef.current || "session",
        sender_role: "assistant",
        message_text: `You are currently connected to ${currentCollegeName}. This question is about ${detectedDifferentCollege.name}. Would you like to switch?`,
        is_verified: true,
        answer_source_type: "ADMIN_VERIFIED",
        source_citations: [],
        token_count: 24,
        created_at: new Date().toISOString(),
        switch_action: {
          targetCollegeId: detectedDifferentCollege.id,
          targetCollegeName: detectedDifferentCollege.name,
          currentCollegeName: currentCollegeName,
          pendingQuestion: trimmed,
          status: "pending",
        },
      };

      setMessages((prev) => [...prev, userMsg, switchConfirmMsg]);
      return;
    }

    // Normal message flow with active college
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

    try {
      const res = await chatService.sendMessage(currentSessionId, trimmed, currentCollegeId, lang, currentCollegeName);
      setIsLoading(false);
      if (collegeIdRef.current !== currentCollegeId) return;

      if (res.success && res.data) {
        const assistantMsg = res.data;
        const allMessages = [...updatedWithUser, assistantMsg];
        setMessages(allMessages);

        const refreshed = currentSessions.map((s) => {
          if (s.id === currentSessionId) {
            return {
              ...s,
              session_title: s.session_title === "New Conversation"
                ? (trimmed.slice(0, 36) + (trimmed.length > 36 ? "..." : ""))
                : s.session_title,
              messages: allMessages.filter(
                (m) =>
                  m.session_id === currentSessionId ||
                  !m.session_id ||
                  m.session_id === "session" ||
                  m.session_id === "pending"
              ),
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

  // User confirmed switching to target college from in-chat card
  const handleConfirmSwitch = async (
    targetCollegeId: string,
    pendingQuestion: string,
    messageId: string
  ) => {
    const targetCollege = colleges.find((c) => c.id === targetCollegeId);
    if (!targetCollege) return;

    // 1. Mark switch action status as switched in the confirmation card
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId && msg.switch_action
          ? { ...msg, switch_action: { ...msg.switch_action, status: "switched" } }
          : msg
      )
    );

    const prevCollegeId = collegeId;

    // 2. Transition session on backend if active session exists
    let activeId = activeSessionRef.current;
    if (activeId && prevCollegeId) {
      const switchRes = await chatService.switchCollege(activeId, prevCollegeId, targetCollege.id);
      if (switchRes.success && switchRes.data) {
        activeId = switchRes.data.id;
        setActiveSessionId(activeId);
        persistActiveSession(targetCollege.id, activeId);
      } else {
        // If switching fails, start a new session for the target college
        activeId = null;
      }
    }

    // 3. Update active college state & storage — do NOT wipe messages so history stays visible
    loadingCollegeIdsRef.current.delete(targetCollege.id);
    setCollegeId(targetCollege.id);
    setCollegeName(targetCollege.name);
    localStorage.setItem("selected_college_id", targetCollege.id);
    localStorage.setItem("selected_college_name", targetCollege.name);
    window.dispatchEvent(new Event("selected-college-change"));

    if (!activeId) {
      const newSession = await chatService.createSession(targetCollege.id, pendingQuestion.slice(0, 36), lang);
      if (newSession.success && newSession.data) {
        activeId = newSession.data.id;
        setActiveSessionId(activeId);
        persistActiveSession(targetCollege.id, activeId);
      }
    }

    if (!activeId) return;

    // 4. Process pending question using new college's approved knowledge
    setIsLoading(true);
    try {
      const res = await chatService.sendMessage(activeId, pendingQuestion, targetCollege.id, lang, targetCollege.name);
      setIsLoading(false);
      if (res.success && res.data) {
        const assistantMsg = res.data;
        setMessages((prev) => [...prev, assistantMsg]);
      } else {
        setChatError(withRequestId(res.error || "Unable to answer question for the new college.", res.requestId));
      }
    } catch (err: any) {
      setIsLoading(false);
      setChatError(err?.message || "Failed to retrieve information from the new college.");
    }
  };

  // User chose to stay with current college from in-chat card
  const handleStayWithCollege = (messageId: string, currentName: string) => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId && msg.switch_action
          ? { ...msg, switch_action: { ...msg.switch_action, status: "stayed" } }
          : msg
      )
    );
    const stayNotice: ChatMessageData = {
      id: generateUUID(),
      session_id: activeSessionRef.current || "session",
      sender_role: "assistant",
      message_text: `Staying with **${currentName}**. How else can I help you today?`,
      is_verified: true,
      answer_source_type: "ADMIN_VERIFIED",
      source_citations: [],
      token_count: 14,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, stayNotice]);
  };

  // Switch college from header modal
  const handleModalSwitchCollege = async (targetCollege: College) => {
    const prevCollegeId = collegeId;
    const activeId = activeSessionRef.current;
    let newSessionId: string | null = null;

    // Transition session on backend if active session exists
    if (activeId && prevCollegeId) {
      const res = await chatService.switchCollege(activeId, prevCollegeId, targetCollege.id);
      if (res.success && res.data) {
        newSessionId = res.data.id;
        if (res.data.visitor_token && typeof window !== "undefined") {
          sessionStorage.setItem(`campusai_chat_visitor_${newSessionId}`, res.data.visitor_token);
        }
      }
    }

    if (!newSessionId) {
      const created = await chatService.createSession(targetCollege.id, "Conversation with " + targetCollege.name, lang);
      if (created.success && created.data) {
        newSessionId = created.data.id;
      }
    }

    if (newSessionId) {
      setActiveSessionId(newSessionId);
      persistActiveSession(targetCollege.id, newSessionId);
    }

    // Clear the deduplication guard so loadSessions fires for the new college
    loadingCollegeIdsRef.current.delete(targetCollege.id);

    // Update active college in state and localStorage
    setCollegeId(targetCollege.id);
    setCollegeName(targetCollege.name);
    localStorage.setItem("selected_college_id", targetCollege.id);
    localStorage.setItem("selected_college_name", targetCollege.name);
    window.dispatchEvent(new Event("selected-college-change"));

    // Append switch message while preserving all previous messages ("always show chat history")
    const switchMsg: ChatMessageData = {
      id: generateUUID(),
      session_id: newSessionId || "session",
      sender_role: "assistant",
      message_text: `Conversation switched to **${targetCollege.name}**. Ask anything about your college, like fees, admission, facilities and more.`,
      is_verified: true,
      answer_source_type: "ADMIN_VERIFIED",
      source_citations: [],
      token_count: 24,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, switchMsg]);
  };

  // Session Actions (New, Rename, Delete, Clear)
  const handleNewSession = async () => {
    setChatError(null);

    // If no college is connected, new conversation goes to welcome screen
    if (!collegeId) {
      setActiveSessionId(null);
      setMessages([]);
      return;
    }

    const currentCollegeId = collegeId;
    try {
      const res = await chatService.createSession(currentCollegeId, "New Conversation", lang);
      if (collegeIdRef.current !== currentCollegeId) return;
      if (!res.success || !res.data) {
        setChatError(withRequestId(res.error || "Unable to create a chat session.", res.requestId));
        return;
      }
      const newSession: ChatSessionData = { ...res.data, messages: [] };
      const updated = [newSession, ...sessions.filter((session) => session.id !== newSession.id && session.college_id === currentCollegeId)];
      setSessions(updated);
      historyLoadSessionRef.current = newSession.id;
      setActiveSessionId(newSession.id);
      setMessages([]);
      persistActiveSession(currentCollegeId, newSession.id);
      persistSessions(currentCollegeId, updated);
    } catch (err: any) {
      setChatError(err?.message || "Failed to create new conversation.");
    }
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
        setActiveSessionId(null);
        setMessages([]);
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
    <div className="flex h-screen overflow-hidden bg-[#0B0B0D]">
      {/* Conversation History Sidebar */}
      <ChatSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={(id) => {
          const selectedSession = sessions.find((session) => session.id === id);
          if (!selectedSession || selectedSession.college_id !== collegeId) return;
          if (activeSessionRef.current === id) return;
          historyLoadSessionRef.current = null;
          setActiveSessionId(id);
          persistActiveSession(collegeId, id);
          setMessages(selectedSession.messages || []);
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
        onOpenSwitchCollege={() => setIsSwitchCollegeOpen(true)}
        onConfirmSwitch={handleConfirmSwitch}
        onStayWithCollege={handleStayWithCollege}
      />

      {/* Global Error Banner */}
      {chatError && (
        <div
          role="alert"
          className="fixed bottom-5 right-5 z-50 max-w-md rounded-lg border border-red-500/40 bg-red-950/90 px-4 py-3 text-sm text-red-100 shadow-lg"
        >
          {chatError}
        </div>
      )}

      {/* Switch College Modal */}
      <SwitchCollegeModal
        isOpen={isSwitchCollegeOpen}
        onClose={() => setIsSwitchCollegeOpen(false)}
        currentCollegeId={collegeId}
        colleges={colleges}
        onSwitch={handleModalSwitchCollege}
      />

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
