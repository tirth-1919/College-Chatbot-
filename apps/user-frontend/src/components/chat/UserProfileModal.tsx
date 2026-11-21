"use client";

import { useState } from "react";
import { User } from "@/types/auth";
import { useTheme } from "@/context/ThemeContext";
import {
  X,
  User as UserIcon,
  Sun,
  Moon,
  ShieldCheck,
  Building2,
  Clock,
  Sparkles,
  CheckCircle2,
  Mail,
  LogOut,
} from "lucide-react";
import Link from "next/link";

interface UserProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: User | null;
  onLogout: () => void;
}

export function UserProfileModal({
  isOpen,
  onClose,
  user,
  onLogout,
}: UserProfileModalProps) {
  const { theme, toggleTheme, setTheme } = useTheme();
  const [activeTab, setActiveTab] = useState<"profile" | "appearance">("profile");

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-lg rounded-2xl border border-[#2A2A30] bg-[#18181B] shadow-2xl overflow-hidden relative text-[#F5F5F5]">
        {/* Header */}
        <div className="p-5 border-b border-[#2A2A30] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-[#6366F1]/10 border border-[#6366F1]/20 flex items-center justify-center text-[#6366F1]">
              <UserIcon className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-[#F5F5F5]">Account & Settings</h2>
              <p className="text-xs text-[#A1A1AA]">Manage your CampusAI preferences</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#A1A1AA] hover:text-[#F5F5F5] hover:bg-[#27272A] transition"
            title="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-[#2A2A30] bg-[#111114] px-5 pt-2">
          <button
            type="button"
            onClick={() => setActiveTab("profile")}
            className={`pb-2.5 px-3 text-xs font-medium border-b-2 transition ${
              activeTab === "profile"
                ? "border-[#6366F1] text-[#F5F5F5]"
                : "border-transparent text-[#A1A1AA] hover:text-[#F5F5F5]"
            }`}
          >
            Profile Details
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("appearance")}
            className={`pb-2.5 px-3 text-xs font-medium border-b-2 transition ${
              activeTab === "appearance"
                ? "border-[#6366F1] text-[#F5F5F5]"
                : "border-transparent text-[#A1A1AA] hover:text-[#F5F5F5]"
            }`}
          >
            Appearance & Theme
          </button>
        </div>

        {/* Content Area */}
        <div className="p-6 space-y-4">
          {activeTab === "profile" && (
            <div className="space-y-4">
              {/* Profile Card */}
              <div className="flex items-center gap-4 p-4 rounded-xl bg-[#1F1F23] border border-[#2A2A30]">
                <div className="h-14 w-14 rounded-full bg-gradient-to-tr from-[#6366F1] to-[#8B5CF6] flex items-center justify-center text-white text-xl font-bold shadow-md shrink-0">
                  {user?.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-base font-semibold text-[#F5F5F5] truncate">
                      {user?.full_name || "Guest Student"}
                    </h3>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#6366F1]/20 text-[#818CF8] font-medium border border-[#6366F1]/30">
                      {user?.role || "STUDENT"}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-[#A1A1AA] mt-1">
                    <Mail className="h-3 w-3" />
                    <span className="truncate">{user?.email || "Signed in"}</span>
                  </div>
                </div>
              </div>

              {/* User Metadata */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-[#1F1F23]/60 border border-[#2A2A30]">
                  <div className="text-[11px] text-[#A1A1AA]">Account Status</div>
                  <div className="text-[#10B981] font-medium mt-1 flex items-center gap-1">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Active & Verified
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-[#1F1F23]/60 border border-[#2A2A30]">
                  <div className="text-[11px] text-[#A1A1AA]">Access Tier</div>
                  <div className="text-[#F5F5F5] font-medium mt-1 flex items-center gap-1">
                    <Sparkles className="h-3.5 w-3.5 text-[#6366F1]" />
                    Full Student Portal
                  </div>
                </div>
              </div>

              {/* Useful Portal Links */}
              <div className="space-y-1.5 pt-2">
                <div className="text-[11px] font-medium text-[#A1A1AA] uppercase tracking-wider px-1">
                  Quick Access
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Link
                    href="/colleges"
                    onClick={onClose}
                    className="flex items-center gap-2 p-2.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:border-[#6366F1] text-xs text-[#E4E4E7] transition"
                  >
                    <Building2 className="h-4 w-4 text-[#6366F1]" />
                    <span>Colleges Directory</span>
                  </Link>
                  <Link
                    href="/registration-status"
                    onClick={onClose}
                    className="flex items-center gap-2 p-2.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:border-[#6366F1] text-xs text-[#E4E4E7] transition"
                  >
                    <Clock className="h-4 w-4 text-[#6366F1]" />
                    <span>Track Status</span>
                  </Link>
                </div>
              </div>
            </div>
          )}

          {activeTab === "appearance" && (
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-[#A1A1AA] block mb-2">
                  Theme Appearance
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setTheme("dark")}
                    className={`p-3.5 rounded-xl border text-left transition flex items-center gap-3 cursor-pointer ${
                      theme === "dark"
                        ? "border-[#6366F1] bg-[#6366F1]/10 text-white"
                        : "border-[#2A2A30] bg-[#1F1F23] text-[#A1A1AA] hover:text-[#F5F5F5]"
                    }`}
                  >
                    <Moon className="h-5 w-5 text-[#818CF8]" />
                    <div>
                      <div className="text-xs font-semibold">Dark Theme</div>
                      <div className="text-[10px] text-[#A1A1AA]">Clean dark contrast</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setTheme("light")}
                    className={`p-3.5 rounded-xl border text-left transition flex items-center gap-3 cursor-pointer ${
                      theme === "light"
                        ? "border-[#6366F1] bg-[#6366F1]/10 text-white"
                        : "border-[#2A2A30] bg-[#1F1F23] text-[#A1A1AA] hover:text-[#F5F5F5]"
                    }`}
                  >
                    <Sun className="h-5 w-5 text-[#F59E0B]" />
                    <div>
                      <div className="text-xs font-semibold">Light Theme</div>
                      <div className="text-[10px] text-[#A1A1AA]">Bright readable palette</div>
                    </div>
                  </button>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-[#1F1F23] border border-[#2A2A30] text-xs text-[#A1A1AA] leading-relaxed">
                Theme changes take effect immediately across all chatbot dialogs, institutional profiles, and markdown citations.
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[#2A2A30] bg-[#111114] flex items-center justify-between">
          {user ? (
            <button
              type="button"
              onClick={() => {
                onClose();
                onLogout();
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-red-400 hover:text-red-300 hover:bg-red-950/40 transition cursor-pointer"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Log out</span>
            </button>
          ) : (
            <div />
          )}

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-[#27272A] hover:bg-[#3F3F46] text-xs font-medium text-white transition cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
