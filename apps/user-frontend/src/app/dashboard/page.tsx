"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { chatService, ChatSessionData } from "@/services/chat-service";
import {
  MessageSquare,
  Building2,
  User,
  Clock,
  ArrowRight,
  HelpCircle,
  ShieldCheck,
  ChevronRight,
  Sparkles,
} from "lucide-react";

export default function StudentDashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [selectedCollegeName, setSelectedCollegeName] = useState<string>("Ahmedabad Institute of Technology");
  const [recentSessions, setRecentSessions] = useState<ChatSessionData[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(true);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
      return;
    }

    const storedCollege = localStorage.getItem("selected_college_name");
    if (storedCollege) setSelectedCollegeName(storedCollege);

    const storedId = localStorage.getItem("selected_college_id");
    chatService
      .listSessions(storedId || undefined)
      .then((res) => {
        if (res.success && res.data) {
          setRecentSessions(res.data.slice(0, 5));
        }
      })
      .finally(() => setLoadingSessions(false));
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return <div className="text-center py-24 text-[#A1A1AA]">Loading student dashboard...</div>;
  }

  const SUGGESTED_QUERIES = [
    "What are the semester tuition fees for Computer Engineering?",
    "What is the complete admission schedule and document checklist?",
    "What hostel facilities and food options are available?",
    "What were the campus placement statistics last year?",
  ];

  return (
    <div className="max-w-6xl mx-auto px-4 py-10">
      {/* Welcome Banner */}
      <div className="p-8 rounded-2xl border border-[#2A2A30] bg-[#111114] mb-8 relative overflow-hidden">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-[#2A2A30] bg-[#1F1F23] text-xs text-[#10B981] mb-2 font-medium">
              <ShieldCheck className="h-3.5 w-3.5" />
              Verified Student Account
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-[#F5F5F5] mb-1">
              Welcome back, {user?.full_name}!
            </h1>
            <p className="text-xs sm:text-sm text-[#A1A1AA]">
              Your AI College Intelligence Portal. Active institution:{" "}
              <span className="text-[#6366F1] font-semibold">{selectedCollegeName}</span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/chat"
              className="px-5 py-2.5 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] text-white text-xs font-medium flex items-center gap-2 transition shadow-lg shadow-[#6366F1]/20"
            >
              <MessageSquare className="h-4 w-4" />
              Open Chatbot
            </Link>
            <Link
              href="/profile"
              className="px-4 py-2.5 rounded-xl bg-[#1F1F23] hover:bg-[#2A2A30] border border-[#2A2A30] text-[#F5F5F5] text-xs font-medium flex items-center gap-1.5 transition"
            >
              <User className="h-4 w-4" />
              Profile
            </Link>
          </div>
        </div>
      </div>

      {/* Grid: Selected College & Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
          <div className="flex items-center justify-between mb-4">
            <div className="h-10 w-10 rounded-xl bg-[#6366F1]/10 flex items-center justify-center text-[#6366F1]">
              <Building2 className="h-5 w-5" />
            </div>
            <Link
              href="/colleges"
              className="text-[11px] text-[#6366F1] hover:underline font-medium"
            >
              Switch College
            </Link>
          </div>
          <span className="text-xs text-[#A1A1AA] block mb-1">Active College Scope</span>
          <h3 className="text-base font-semibold text-[#F5F5F5] leading-tight mb-3">
            {selectedCollegeName}
          </h3>
          <p className="text-[11px] text-[#A1A1AA]">
            Chat queries are strictly verified against official documents belonging to this college.
          </p>
        </div>

        <Link
          href="/chat"
          className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] hover:border-[#6366F1] transition group"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="h-10 w-10 rounded-xl bg-[#10B981]/10 flex items-center justify-center text-[#10B981]">
              <MessageSquare className="h-5 w-5" />
            </div>
            <ArrowRight className="h-4 w-4 text-[#A1A1AA] group-hover:text-[#6366F1] group-hover:translate-x-1 transition" />
          </div>
          <span className="text-xs text-[#A1A1AA] block mb-1">AI Assistant</span>
          <h3 className="text-base font-semibold text-[#F5F5F5] mb-2">Ask a Question</h3>
          <p className="text-[11px] text-[#A1A1AA]">
            Get answers grounded in official college brochures, websites, and verified facts.
          </p>
        </Link>

        <Link
          href="/profile"
          className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] hover:border-[#6366F1] transition group"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="h-10 w-10 rounded-xl bg-[#F59E0B]/10 flex items-center justify-center text-[#F59E0B]">
              <User className="h-5 w-5" />
            </div>
            <ArrowRight className="h-4 w-4 text-[#A1A1AA] group-hover:text-[#F59E0B] group-hover:translate-x-1 transition" />
          </div>
          <span className="text-xs text-[#A1A1AA] block mb-1">Student Account</span>
          <h3 className="text-base font-semibold text-[#F5F5F5] mb-2">Preferences & Voice</h3>
          <p className="text-[11px] text-[#A1A1AA]">
            Switch languages between English, Hindi, and Gujarati, and configure audio settings.
          </p>
        </Link>
      </div>

      {/* Two Column Layout: Recent Conversations & Suggested Questions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-10">
        {/* Recent Conversations */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
              <Clock className="h-4 w-4 text-[#6366F1]" />
              Recent Conversations
            </h3>
            <Link href="/chat" className="text-xs text-[#6366F1] hover:underline">
              View all
            </Link>
          </div>

          {loadingSessions ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-12 rounded-xl bg-[#1F1F23] animate-pulse"></div>
              ))}
            </div>
          ) : recentSessions.length === 0 ? (
            <div className="text-center py-8 text-xs text-[#A1A1AA] border border-dashed border-[#2A2A30] rounded-xl">
              No recent conversations yet. Start your first inquiry!
            </div>
          ) : (
            <div className="space-y-2">
              {recentSessions.map((s) => (
                <Link
                  key={s.id}
                  href="/chat"
                  className="p-3 rounded-xl bg-[#1F1F23]/60 hover:bg-[#1F1F23] border border-[#2A2A30] flex items-center justify-between transition group"
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <MessageSquare className="h-3.5 w-3.5 text-[#6366F1] shrink-0" />
                    <span className="text-xs font-medium text-[#F5F5F5] truncate">
                      {s.session_title}
                    </span>
                  </div>
                  <ChevronRight className="h-3.5 w-3.5 text-[#A1A1AA] group-hover:text-[#6366F1] transition shrink-0 ml-2" />
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Suggested Queries */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
          <h3 className="text-sm font-semibold text-[#F5F5F5] mb-4 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-[#F59E0B]" />
            Frequently Asked Questions
          </h3>

          <div className="space-y-2.5">
            {SUGGESTED_QUERIES.map((q, idx) => (
              <Link
                key={idx}
                href="/chat"
                className="p-3 rounded-xl bg-[#1F1F23]/60 hover:bg-[#1F1F23] border border-[#2A2A30] flex items-center justify-between text-xs text-[#F5F5F5] transition group"
              >
                <span>{q}</span>
                <ArrowRight className="h-3.5 w-3.5 text-[#A1A1AA] group-hover:text-[#6366F1] transition shrink-0 ml-2" />
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Help & Support Banner */}
      <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-[#1F1F23] flex items-center justify-center text-[#6366F1] shrink-0">
            <HelpCircle className="h-5 w-5" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[#F5F5F5]">Need Official Human Assistance?</h4>
            <p className="text-xs text-[#A1A1AA]">
              If the AI cannot verify your specific query, you can submit an official inquiry ticket to the admissions office.
            </p>
          </div>
        </div>
        <Link
          href="/chat"
          className="px-4 py-2 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-xs font-medium text-[#F5F5F5] hover:border-[#6366F1] transition whitespace-nowrap"
        >
          Contact College Staff
        </Link>
      </div>
    </div>
  );
}
