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
  const [loadError, setLoadError] = useState<string | null>(null);

  const fetchAnalytics = async () => {
    setIsLoading(true);
    setAnalytics(null);
    setLoadError(null);
    try {
      const res = await collegeAdminService.getAnalytics(timeRange);
      if (res.success && res.data) {
        setAnalytics(res.data);
      } else {
        setLoadError(res.message || "Analytics could not be loaded.");
      }
    } catch (err) {
      console.error("Failed to load college analytics:", err);
      setLoadError("Analytics could not be loaded. Please refresh and try again.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);

  const data = analytics || {
    total_queries: 0,
    popular_questions: [],
    frequent_questions: [],
    unanswered_questions: [],
    source_usage: {},
    source_distribution: {},
    badge_distribution: {},
    satisfaction_score: 0,
    positive_feedback_count: 0,
    negative_feedback_count: 0,
  };
  const popularQuestions = data.popular_questions || data.frequent_questions || [];
  const unansweredQuestions = data.unanswered_questions || [];
  const hasFeedback = (data.positive_feedback_count || 0) + (data.negative_feedback_count || 0) > 0;
  const answerDistribution = data.badge_distribution || data.source_distribution || {};

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

      {isLoading && <div className="text-xs text-[#A1A1AA]" role="status">Loading analytics for {timeRange}…</div>}
      {loadError && <div className="p-3 rounded-lg border border-[#EF4444]/30 bg-[#EF4444]/10 text-xs text-[#FCA5A5]" role="alert">{loadError}</div>}

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
          value={hasFeedback ? `${data.satisfaction_score ?? data.satisfaction_rate ?? 0} / 5.0` : "No ratings"}
          subtitle="Ratings in selected date range"
          trend={hasFeedback ? "Based on student feedback" : "No feedback in range"}
          trendUp={hasFeedback}
          icon={<Star className="h-5 w-5" />}
          iconColor="text-[#F59E0B] bg-[#F59E0B]/10"
        />

        <DashboardCard
          title="Identified Knowledge Gaps"
          value={unansweredQuestions.length}
          subtitle="Questions requiring new circulars"
          trend={unansweredQuestions.length > 0 ? "Review Needed" : "None in range"}
          trendUp={unansweredQuestions.length === 0}
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
            {popularQuestions.length > 0 ? popularQuestions.map((q, idx) => {
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
            }) : <p className="py-6 text-xs text-[#71717A]">No student questions in this date range.</p>}
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
            {unansweredQuestions.length > 0 ? unansweredQuestions.map((uq, idx) => {
              const questionText = typeof uq === "string" ? uq : (uq as any).query || (uq as any).question || "";
              const occurrenceCount = typeof uq === "object" ? (uq as any).count || (uq as any).occurrence_count : 0;
              const count = occurrenceCount ? `(${occurrenceCount} asks)` : "";
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
            }) : <p className="py-4 text-xs text-[#71717A]">No unanswered questions in this date range.</p>}
          </div>
        </div>
      </div>

      {/* Trust & Grounding Distribution */}
      {Object.keys(answerDistribution).length > 0 && (
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-[#6366F1]" />
              Answer Grounding & Verification Distribution
            </h3>
            <span className="text-[10px] text-[#A1A1AA]">Based on verified queries</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-2">
            {Object.entries(answerDistribution).map(([label, count]) => (
              <div key={label} className="p-3 rounded-xl bg-[#0B0B0D] border border-[#2A2A30]">
                <span className="text-[10px] text-[#A1A1AA] font-semibold block uppercase">{label.replaceAll("_", " ")}</span>
                <span className="text-lg font-bold text-[#F5F5F5]">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

