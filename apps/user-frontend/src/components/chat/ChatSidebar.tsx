"use client";

import { useState } from "react";
import { ChatSessionData } from "@/services/chat-service";
import {
  MessageSquare,
  Plus,
  Search,
  Trash2,
  Edit2,
  Check,
  X,
  Clock,
  ChevronLeft,
  ChevronRight,
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
  const [searchTerm, setSearchTerm] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

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
        className="fixed left-3 top-20 z-40 p-2 rounded-xl border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
        title="Open conversation history"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    );
  }

  return (
    <div className="w-72 border-r border-[#2A2A30] bg-[#111114] flex flex-col h-full shrink-0 relative transition-all">
      {/* Sidebar Header */}
      <div className="p-4 border-b border-[#2A2A30] flex items-center justify-between">
        <button
          onClick={onNewSession}
          className="flex-1 py-2 px-3 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] text-white text-xs font-medium flex items-center justify-center gap-2 transition"
        >
          <Plus className="h-4 w-4" />
          New Conversation
        </button>
        <button
          onClick={onToggle}
          className="ml-2 p-2 rounded-lg text-[#A1A1AA] hover:text-[#F5F5F5] transition"
          title="Collapse sidebar"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
      </div>

      {/* Search Input */}
      <div className="p-3 border-b border-[#2A2A30]">
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
                      className="p-1 text-[#10B981] hover:bg-[#10B981]/10 rounded"
                    >
                      <Check className="h-3 w-3" />
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="p-1 text-[#EF4444] hover:bg-[#EF4444]/10 rounded"
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
                        className="px-2 py-0.5 rounded bg-[#EF4444] text-white text-[10px]"
                      >
                        Yes
                      </button>
                      <button
                        onClick={() => setConfirmDeleteId(null)}
                        className="px-2 py-0.5 rounded bg-[#2A2A30] text-[#A1A1AA] text-[10px]"
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
                        className="p-1 rounded text-[#A1A1AA] hover:text-[#F5F5F5]"
                        title="Rename"
                      >
                        <Edit2 className="h-3 w-3" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setConfirmDeleteId(s.id);
                        }}
                        className="p-1 rounded text-[#A1A1AA] hover:text-[#EF4444]"
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
    </div>
  );
}

