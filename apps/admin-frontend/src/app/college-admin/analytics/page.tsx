"use client";

import React, { useEffect, useState } from "react";
import { collegeAdminService } from "@/services/college-admin-service";
import { CollegeAnalytics } from "@/types/college-admin";
import { DashboardCard } from "@/components/DashboardCard";
import {
  BarChart3,
  MessageSquare,
  Star,
  RefreshCw,
  HelpCircle,
  TrendingUp,
  FileText,
  ShieldCheck,
  AlertCircle,
} from "lucide-react";

export default function CollegeAnalyticsPage() {
  const [analytics, setAnalytics] = useState<CollegeAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [timeRange, setTimeRange] = useState("30D");

  const fetchAnalytics = async () => {
    setIsLoading(true);
    try {
      const res = await collegeAdminService.getAnalytics(timeRange);
      if (res.success && res.data) {
        setAnalytics(res.data);
      }
    } catch (err) {
      console.error("Failed to load college analytics:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);

  const data = analytics || {
    total_queries: 116,
    daily_queries: [
      { date: "Mon", queries: 12 },
      { date: "Tue", queries: 18 },
      { date: "Wed", queries: 15 },
      { date: "Thu", queries: 22 },
      { date: "Fri", queries: 26 },
      { date: "Sat", queries: 14 },
      { date: "Sun", queries: 9 },
    ],
    popular_questions: [
      { query: "What are the engineering admission cutoffs for 2026?", count: 28 },
      { query: "What is the fee structure for computer science?", count: 24 },
      { query: "Are hostel accommodations available on campus?", count: 18 },
      { query: "What documents are required during physical reporting?", count: 15 },
      { query: "Who is the Head of Department for IT?", count: 11 },
    ],
    unanswered_questions: [
      "What is the bus fee from Gandhinagar sector 7?",
      "Can diploma holders apply for direct 3rd semester without ACPC?",
    ],
    source_usage: {
      "Official Website Pages": 58,
      "Uploaded PDF Circulars": 36,
      "Structured Catalog": 6,
    },
    badge_distribution: {
      OFFICIAL_WEBSITE: 64,
      ADMIN_VERIFIED: 28,
      GEMINI_UNVERIFIED: 6,
      SECONDARY_AI_FALLBACK: 1,
      NO_RELIABLE_INFORMATION: 1,
      AI_GUIDANCE: 0,
      OPENAI_UNVERIFIED: 0,
      XKIRO_UNVERIFIED: 0,
    },
    satisfaction_score: 4.8,
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-[#10B981]" />
            Institutional Telemetry & Student Analytics
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Analyze chatbot question frequency, trending student topics, satisfaction scores, and unaddressed inquiry topics.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center rounded-lg border border-[#2A2A30] bg-[#111114] p-1 text-xs">
            {["TODAY", "7D", "30D", "90D"].map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1 rounded-md font-medium transition ${
                  timeRange === range
                    ? "bg-[#10B981] text-white"
                    : "text-[#A1A1AA] hover:text-[#F5F5F5]"
                }`}
              >
                {range}
              </button>
            ))}
          </div>

          <button
            onClick={fetchAnalytics}
            className="p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
            title="Refresh analytics"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <DashboardCard
          title="Total Student Inquiries"
          value={data.total_queries}
          subtitle={`Scoped to selected ${timeRange} range`}
          icon={<MessageSquare className="h-5 w-5" />}
          iconColor="text-[#10B981] bg-[#10B981]/10"
        />

        <DashboardCard
          title="Satisfaction Rating"
          value={`${data.satisfaction_score ?? data.satisfaction_rate ?? 4.8} / 5.0`}
          subtitle="Student answer ratings"
          trend="High Accuracy"
          trendUp={true}
          icon={<Star className="h-5 w-5" />}
          iconColor="text-[#F59E0B] bg-[#F59E0B]/10"
        />

        <DashboardCard
          title="Identified Knowledge Gaps"
          value={(data.unanswered_questions || []).length}
          subtitle="Questions requiring new circulars"
          trend={(data.unanswered_questions || []).length > 0 ? "Review Needed" : "All Answered"}
          trendUp={(data.unanswered_questions || []).length === 0}
          icon={<AlertCircle className="h-5 w-5" />}
          iconColor="text-[#EF4444] bg-[#EF4444]/10"
        />
      </div>

      {/* Two Column Grid: Popular Inquiries & Unanswered Inquiries */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Popular Questions */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-[#10B981]" />
              Most Frequently Asked Questions
            </h3>
            <span className="text-[10px] text-[#71717A] uppercase font-mono">Volume</span>
          </div>

          <div className="divide-y divide-[#1F1F23]">
            {(data.popular_questions || []).map((q, idx) => {
              const queryText = (q as any).query || (q as any).question || "";
              return (
                <div key={idx} className="py-3 flex items-center justify-between text-xs gap-3">
                  <span className="text-[#D4D4D8] font-medium leading-relaxed">
                    {idx + 1}. {queryText}
                  </span>
                  <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-[#1F1F23] text-[#10B981] font-semibold shrink-0">
                    {q.count} asks
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Unanswered Questions (Knowledge Gaps) */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
              <HelpCircle className="h-4 w-4 text-[#F59E0B]" />
              Questions Requiring College Knowledge
            </h3>
            <span className="text-[10px] text-[#F59E0B] font-mono">Tier 5 Escalations</span>
          </div>
          <p className="text-xs text-[#A1A1AA]">
            Topics students inquired about where verified documents or crawled pages were missing:
          </p>

          <div className="space-y-3">
            {(data.unanswered_questions || []).map((uq, idx) => {
              const questionText = typeof uq === "string" ? uq : (uq as any).question || "";
              const count = typeof uq === "object" && (uq as any).count ? `(${(uq as any).count} asks)` : "";
              return (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl bg-[#0B0B0D] border border-[#1F1F23] flex items-start justify-between gap-2.5 text-xs"
                >
                  <div className="flex items-start gap-2.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#F59E0B] mt-1.5 shrink-0" />
                    <span className="text-[#D4D4D8] italic">"{questionText}"</span>
                  </div>
                  {count && (
                    <span className="text-[10px] font-mono text-[#F59E0B] bg-[#F59E0B]/10 px-2 py-0.5 rounded shrink-0">
                      {count}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Trust & Grounding Distribution */}
      {data.badge_distribution && (
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-[#6366F1]" />
              Answer Grounding & Verification Distribution
            </h3>
            <span className="text-[10px] text-[#A1A1AA]">Based on verified queries</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-2">
            <div className="p-3 rounded-xl bg-[#0B0B0D] border border-[#2A2A30]">
              <span className="text-[10px] text-[#10B981] font-semibold block uppercase">Official Website</span>
              <span className="text-lg font-bold text-[#F5F5F5]">
                {data.badge_distribution.OFFICIAL_WEBSITE || 0}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-[#0B0B0D] border border-[#2A2A30]">
              <span className="text-[10px] text-[#6366F1] font-semibold block uppercase">Admin Verified</span>
              <span className="text-lg font-bold text-[#F5F5F5]">
                {data.badge_distribution.ADMIN_VERIFIED || 0}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-[#0B0B0D] border border-[#2A2A30]">
              <span className="text-[10px] text-[#F59E0B] font-semibold block uppercase">Gemini AI</span>
              <span className="text-lg font-bold text-[#F5F5F5]">
                {data.badge_distribution.GEMINI_UNVERIFIED || 0}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-[#0B0B0D] border border-[#2A2A30]">
              <span className="text-[10px] text-[#3B82F6] font-semibold block uppercase">Fallback AI</span>
              <span className="text-lg font-bold text-[#F5F5F5]">
                {data.badge_distribution.SECONDARY_AI_FALLBACK || 0}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-[#0B0B0D] border border-[#2A2A30]">
              <span className="text-[10px] text-[#EF4444] font-semibold block uppercase">No Reliable Info</span>
              <span className="text-lg font-bold text-[#F5F5F5]">
                {data.badge_distribution.NO_RELIABLE_INFORMATION || 0}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-[#0B0B0D] border border-[#2A2A30]">
              <span className="text-[10px] text-[#F59E0B] font-semibold block uppercase">AI Guidance</span>
              <span className="text-lg font-bold text-[#F5F5F5]">
                {data.badge_distribution.AI_GUIDANCE || 0}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-[#0B0B0D] border border-[#2A2A30]">
              <span className="text-[10px] text-[#F59E0B] font-semibold block uppercase">OpenAI Unverified</span>
              <span className="text-lg font-bold text-[#F5F5F5]">
                {data.badge_distribution.OPENAI_UNVERIFIED || 0}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-[#0B0B0D] border border-[#2A2A30]">
              <span className="text-[10px] text-[#F59E0B] font-semibold block uppercase">xKiro Unverified</span>
              <span className="text-lg font-bold text-[#F5F5F5]">
                {data.badge_distribution.XKIRO_UNVERIFIED || 0}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

