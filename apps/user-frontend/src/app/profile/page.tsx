"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { useTranslation, SupportedLanguage } from "@/hooks/use-translation";
import {
  User as UserIcon,
  Mail,
  Shield,
  Building2,
  Globe,
  LogOut,
  HelpCircle,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
} from "lucide-react";

export default function ProfilePage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const { lang, changeLanguage, t } = useTranslation();
  const [selectedCollegeName, setSelectedCollegeName] = useState("No college selected");

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
    const stored = localStorage.getItem("selected_college_name");
    if (stored) setSelectedCollegeName(stored);
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return <div className="text-center py-24 text-[#A1A1AA]">Loading your profile...</div>;
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[#F5F5F5] mb-1">Student Account Profile</h1>
        <p className="text-xs text-[#A1A1AA]">
          Manage your personal details, institutional context, and language preferences.
        </p>
      </div>

      <div className="space-y-6">
        {/* Account Details Card */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
          <h2 className="text-sm font-semibold text-[#F5F5F5] mb-4 flex items-center gap-2">
            <UserIcon className="h-4 w-4 text-[#6366F1]" />
            Personal Details
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-3.5 rounded-xl bg-[#1F1F23] border border-[#2A2A30]">
              <span className="text-[#A1A1AA] block mb-1">Full Legal Name</span>
              <span className="font-medium text-[#F5F5F5] text-sm">{user?.full_name}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#1F1F23] border border-[#2A2A30]">
              <span className="text-[#A1A1AA] block mb-1">Email Address</span>
              <span className="font-medium text-[#F5F5F5] text-sm font-mono">{user?.email}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#1F1F23] border border-[#2A2A30]">
              <span className="text-[#A1A1AA] block mb-1">Account Role</span>
              <div className="flex items-center gap-1.5 mt-0.5">
                <Shield className="h-3.5 w-3.5 text-[#6366F1]" />
                <span className="font-medium text-[#F5F5F5] uppercase tracking-wider text-xs">
                  {user?.role}
                </span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-[#1F1F23] border border-[#2A2A30]">
              <span className="text-[#A1A1AA] block mb-1">Email Verification</span>
              <div className="flex items-center gap-1.5 mt-0.5">
                {user?.is_verified ? (
                  <span className="text-[#10B981] flex items-center gap-1 font-medium">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Verified
                  </span>
                ) : (
                  <span className="text-[#F59E0B] flex items-center gap-1 font-medium">
                    <AlertCircle className="h-3.5 w-3.5" /> Pending Verification
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Institutional Context Card */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
              <Building2 className="h-4 w-4 text-[#6366F1]" />
              Active College Institution
            </h2>
            <Link
              href="/colleges"
              className="text-xs text-[#6366F1] hover:underline font-medium flex items-center gap-1"
            >
              Switch Institution <ExternalLink className="h-3 w-3" />
            </Link>
          </div>

          <div className="p-4 rounded-xl bg-[#1F1F23] border border-[#2A2A30] flex items-center justify-between">
            <div>
              <span className="text-xs text-[#A1A1AA] block">Currently Bound Tenant:</span>
              <span className="font-semibold text-sm text-[#F5F5F5]">{selectedCollegeName}</span>
            </div>
            <span className="text-[10px] text-[#10B981] bg-[#10B981]/10 px-2.5 py-1 rounded-full border border-[#10B981]/20 font-medium">
              Active RLS Scope
            </span>
          </div>
        </div>

        {/* Language Preference Card */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
          <h2 className="text-sm font-semibold text-[#F5F5F5] mb-4 flex items-center gap-2">
            <Globe className="h-4 w-4 text-[#6366F1]" />
            Preferred Chat Interface Language
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              { code: "en", label: "English", sub: "Default UI & Speech" },
              { code: "hi", label: "हिन्दी (Hindi)", sub: "देवनागरी लिपि" },
              { code: "gu", label: "ગુજરાતી (Gujarati)", sub: "ગુજરાતી ભાષા" },
            ].map((item) => {
              const isSelected = lang === item.code;
              return (
                <button
                  key={item.code}
                  type="button"
                  onClick={() => changeLanguage(item.code as SupportedLanguage)}
                  className={`p-3.5 rounded-xl border text-left transition ${
                    isSelected
                      ? "border-[#6366F1] bg-[#6366F1]/10 text-white"
                      : "border-[#2A2A30] bg-[#1F1F23] text-[#A1A1AA] hover:text-[#F5F5F5]"
                  }`}
                >
                  <div className="font-semibold text-xs text-[#F5F5F5]">{item.label}</div>
                  <div className="text-[10px] text-[#A1A1AA] mt-0.5">{item.sub}</div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Account Actions Card */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-[#F5F5F5]">Sign Out</h3>
            <p className="text-xs text-[#A1A1AA]">
              End your active session on this device.
            </p>
          </div>
          <button
            onClick={logout}
            className="px-4 py-2 rounded-xl bg-[#EF4444]/10 hover:bg-[#EF4444]/20 border border-[#EF4444]/30 text-[#EF4444] text-xs font-medium flex items-center gap-2 transition"
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}

