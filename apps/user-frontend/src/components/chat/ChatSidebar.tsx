"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { ChatSessionData } from "@/services/chat-service";
import { useAuth } from "@/hooks/use-auth";
import { useTheme } from "@/context/ThemeContext";
import { UserProfileModal } from "@/components/chat/UserProfileModal";
import {
  MessageSquare,
  Plus,
  Search,
  Trash2,
  Edit2,
  Check,
  X,
  ChevronLeft,
  ChevronRight,
  GraduationCap,
  MoreHorizontal,
  User as UserIcon,
  Settings,
  Sun,
  Moon,
  Building2,
  Clock,
  ShieldCheck,
  LogOut,
} from "lucide-react";

interface ChatSidebarProps {
  sessions: ChatSessionData[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onRenameSession: (id: string, newTitle: string) => void;
  onDeleteSession: (id: string) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export function ChatSidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onRenameSession,
  onDeleteSession,
  isOpen,
  onToggle,
}: ChatSidebarProps) {
  const { user, isAuthenticated, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const [searchTerm, setSearchTerm] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);

  const menuRef = useRef<HTMLDivElement>(null);

  // Close floating profile menu on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsProfileMenuOpen(false);
      }
    }
    if (isProfileMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isProfileMenuOpen]);

  const filteredSessions = sessions.filter((s) =>
    s.session_title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const startEditing = (s: ChatSessionData) => {
    setEditingId(s.id);
    setEditTitle(s.session_title);
  };

  const handleSaveRename = (id: string) => {
    if (editTitle.trim()) {
      onRenameSession(id, editTitle.trim());
    }
    setEditingId(null);
  };

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed left-3 top-4 z-40 p-2.5 rounded-xl border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] hover:border-[#6366F1] shadow-xl transition cursor-pointer"
        title="Open sidebar"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    );
  }

  return (
    <>
      <div className="w-72 border-r border-[#2A2A30] bg-[#111114] flex flex-col h-full shrink-0 relative transition-all">
        {/* Top Header: CampusAI Logo + Collapse Button */}
        <div className="px-4 py-3.5 border-b border-[#2A2A30] flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 hover:opacity-90 transition">
            <div className="h-8 w-8 rounded-lg bg-[#6366F1] flex items-center justify-center text-white font-bold shadow-sm">
              <GraduationCap className="h-4 w-4" />
            </div>
            <span className="font-semibold text-sm text-[#F5F5F5] tracking-tight">
              Campus<span className="text-[#6366F1]">AI</span>
            </span>
          </Link>

          <button
            type="button"
            onClick={onToggle}
            className="p-1.5 rounded-lg text-[#A1A1AA] hover:text-[#F5F5F5] hover:bg-[#1F1F23] transition cursor-pointer"
            title="Collapse sidebar"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        </div>

        {/* New Conversation Button (ChatGPT style) */}
        <div className="p-3 pb-2">
          <button
            type="button"
            onClick={onNewSession}
            className="w-full py-2.5 px-3 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] active:scale-[0.98] text-white text-xs font-medium flex items-center justify-center gap-2 transition cursor-pointer shadow-sm select-none"
          >
            <Plus className="h-4 w-4" />
            <span>New Conversation</span>
          </button>
        </div>

        {/* Search Input */}
        <div className="px-3 pb-2 border-b border-[#2A2A30]">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-[#A1A1AA]" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search conversations..."
              className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-xs text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1] transition"
            />
          </div>
        </div>

        {/* Session Threads List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {filteredSessions.length === 0 ? (
            <div className="py-12 text-center text-xs text-[#A1A1AA]">
              {searchTerm ? "No matching conversations." : "No previous chats."}
            </div>
          ) : (
            filteredSessions.map((s) => {
              const isActive = s.id === activeSessionId;
              const isEditing = editingId === s.id;
              const isConfirming = confirmDeleteId === s.id;

              return (
                <div
                  key={s.id}
                  className={`group relative rounded-xl px-3 py-2.5 text-xs transition flex items-center justify-between ${
                    isActive
                      ? "bg-[#1F1F23] text-[#F5F5F5] font-medium border border-[#2A2A30]"
                      : "text-[#A1A1AA] hover:bg-[#1F1F23]/50 hover:text-[#F5F5F5]"
                  }`}
                >
                  {isEditing ? (
                    <div className="flex items-center gap-1.5 w-full">
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="flex-1 bg-[#0B0B0D] px-2 py-1 rounded border border-[#6366F1] text-xs text-white focus:outline-none"
                        autoFocus
                      />
                      <button
                        onClick={() => handleSaveRename(s.id)}
                        className="p-1 text-[#10B981] hover:bg-[#10B981]/10 rounded cursor-pointer"
                      >
                        <Check className="h-3 w-3" />
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="p-1 text-[#EF4444] hover:bg-[#EF4444]/10 rounded cursor-pointer"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ) : isConfirming ? (
                    <div className="flex items-center justify-between w-full py-0.5">
                      <span className="text-[11px] text-[#EF4444]">Delete thread?</span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => {
                            onDeleteSession(s.id);
                            setConfirmDeleteId(null);
                          }}
                          className="px-2 py-0.5 rounded bg-[#EF4444] text-white text-[10px] cursor-pointer"
                        >
                          Yes
                        </button>
                        <button
                          onClick={() => setConfirmDeleteId(null)}
                          className="px-2 py-0.5 rounded bg-[#2A2A30] text-[#A1A1AA] text-[10px] cursor-pointer"
                        >
                          No
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div
                        onClick={() => onSelectSession(s.id)}
                        className="flex items-center gap-2.5 truncate flex-1 cursor-pointer"
                      >
                        <MessageSquare className="h-3.5 w-3.5 shrink-0 text-[#6366F1]" />
                        <span className="truncate">{s.session_title}</span>
                      </div>

                      <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 transition">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            startEditing(s);
                          }}
                          className="p-1 rounded text-[#A1A1AA] hover:text-[#F5F5F5] cursor-pointer"
                          title="Rename"
                        >
                          <Edit2 className="h-3 w-3" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setConfirmDeleteId(s.id);
                          }}
                          className="p-1 rounded text-[#A1A1AA] hover:text-[#EF4444] cursor-pointer"
                          title="Delete"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    </>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* ChatGPT-style User Profile Row at Bottom */}
        <div className="p-3 border-t border-[#2A2A30] relative" ref={menuRef}>
          {/* Floating ChatGPT-style Menu */}
          {isProfileMenuOpen && (
            <div className="absolute bottom-full left-3 right-3 mb-2 rounded-2xl border border-[#2A2A30] bg-[#18181B] p-2 shadow-2xl z-50 animate-in fade-in slide-in-from-bottom-2 duration-150">
              {/* User Info Header (if authenticated) */}
              {isAuthenticated && user ? (
                <div className="p-2.5 mb-1.5 rounded-xl bg-[#1F1F23] border border-[#2A2A30]">
                  <div className="flex items-center gap-2.5">
                    <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-[#6366F1] to-[#8B5CF6] flex items-center justify-center text-white font-bold text-sm shadow-sm shrink-0">
                      {user.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-semibold text-[#F5F5F5] truncate flex items-center gap-1.5">
                        <span>{user.full_name}</span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#6366F1]/20 text-[#818CF8] font-medium border border-[#6366F1]/30">
                          {user.role}
                        </span>
                      </div>
                      <div className="text-[11px] text-[#A1A1AA] truncate">{user.email}</div>
                    </div>
                  </div>
                </div>
              ) : null}

              {/* Menu Items */}
              <div className="space-y-0.5 text-xs text-[#E4E4E7]">
                {isAuthenticated && (
                  <button
                    type="button"
                    onClick={() => {
                      setIsProfileMenuOpen(false);
                      setIsSettingsModalOpen(true);
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-[#27272A] hover:text-[#F5F5F5] transition text-left cursor-pointer"
                  >
                    <Settings className="h-4 w-4 text-[#A1A1AA]" />
                    <span>Settings & Profile</span>
                  </button>
                )}

                {/* Appearance Toggle */}
                <button
                  type="button"
                  onClick={() => {
                    toggleTheme();
                  }}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-[#27272A] hover:text-[#F5F5F5] transition text-left cursor-pointer"
                >
                  <div className="flex items-center gap-2.5">
                    {theme === "dark" ? (
                      <Sun className="h-4 w-4 text-[#F59E0B]" />
                    ) : (
                      <Moon className="h-4 w-4 text-[#6366F1]" />
                    )}
                    <span>Appearance</span>
                  </div>
                  <span className="text-[11px] text-[#A1A1AA] capitalize">{theme} mode</span>
                </button>

                <div className="h-px bg-[#2A2A30] my-1" />

                {/* Quick Navigation Links */}
                <Link
                  href="/colleges"
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-[#27272A] hover:text-[#F5F5F5] transition text-left cursor-pointer"
                  onClick={() => setIsProfileMenuOpen(false)}
                >
                  <Building2 className="h-4 w-4 text-[#A1A1AA]" />
                  <span>Browse Colleges</span>
                </Link>

                <Link
                  href="/registration-status"
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-[#27272A] hover:text-[#F5F5F5] transition text-left cursor-pointer"
                  onClick={() => setIsProfileMenuOpen(false)}
                >
                  <Clock className="h-4 w-4 text-[#A1A1AA]" />
                  <span>Track Status</span>
                </Link>

                <Link
                  href="/register-college"
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-[#27272A] hover:text-[#F5F5F5] transition text-left cursor-pointer"
                  onClick={() => setIsProfileMenuOpen(false)}
                >
                  <ShieldCheck className="h-4 w-4 text-[#A1A1AA]" />
                  <span>Register College</span>
                </Link>

                <div className="h-px bg-[#2A2A30] my-1" />

                {/* Log out / Log in */}
                {isAuthenticated ? (
                  <button
                    type="button"
                    onClick={() => {
                      setIsProfileMenuOpen(false);
                      logout();
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-red-950/40 text-red-400 hover:text-red-300 transition text-left cursor-pointer"
                  >
                    <LogOut className="h-4 w-4" />
                    <span>Log out</span>
                  </button>
                ) : (
                  <Link
                    href="/login"
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-[#27272A] text-[#6366F1] hover:text-[#818CF8] font-medium transition text-left cursor-pointer"
                    onClick={() => setIsProfileMenuOpen(false)}
                  >
                    <UserIcon className="h-4 w-4" />
                    <span>Sign In / Create Account</span>
                  </Link>
                )}
              </div>
            </div>
          )}

          {/* User Profile Pill Trigger */}
          <button
            type="button"
            onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
            className={`w-full flex items-center justify-between p-2 rounded-xl transition cursor-pointer select-none ${
              isProfileMenuOpen
                ? "bg-[#1F1F23] border border-[#2A2A30]"
                : "hover:bg-[#1F1F23]/60"
            }`}
          >
            <div className="flex items-center gap-2.5 min-w-0">
              {isAuthenticated && user ? (
                <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-[#6366F1] to-[#8B5CF6] flex items-center justify-center text-white font-semibold text-xs shrink-0 shadow-sm">
                  {user.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
                </div>
              ) : (
                <div className="h-8 w-8 rounded-full bg-[#27272A] flex items-center justify-center text-[#A1A1AA] shrink-0">
                  <UserIcon className="h-4 w-4" />
                </div>
              )}
              <div className="text-left min-w-0 truncate">
                <div className="text-xs font-medium text-[#F5F5F5] truncate">
                  {isAuthenticated && user ? user.full_name : "Guest User"}
                </div>
                <div className="text-[10px] text-[#A1A1AA] truncate">
                  {isAuthenticated && user ? (user.email || user.role) : "Click for options"}
                </div>
              </div>
            </div>
            <MoreHorizontal className="h-4 w-4 text-[#A1A1AA] shrink-0 ml-1" />
          </button>
        </div>
      </div>

      {/* ChatGPT-style Settings & Profile Modal */}
      <UserProfileModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
        user={user}
        onLogout={logout}
      />
    </>
  );
}

