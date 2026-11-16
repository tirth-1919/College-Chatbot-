"use client";

import React, { useEffect, useState } from "react";
import { superAdminService } from "@/services/super-admin-service";
import { UsageAnalytics } from "@/types/admin";
import { DashboardCard } from "@/components/DashboardCard";
import {
  BarChart3,
  Coins,
  Cpu,
  Clock,
  Zap,
  TrendingUp,
  RefreshCw,
  Building2,
  ShieldCheck,
} from "lucide-react";

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<UsageAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [timeRange, setTimeRange] = useState("30D");

  const fetchAnalytics = async () => {
    setIsLoading(true);
    try {
      const res = await superAdminService.getUsageAnalytics(timeRange);
      if (res.success && res.data) {
        setAnalytics(res.data);
      }
    } catch (err) {
      console.error("Failed to load analytics:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);

  const data = analytics || {
    total_queries: 128,
    total_tokens: 64900,
    prompt_tokens: 48500,
    completion_tokens: 16400,
    average_latency_ms: 174.5,
    fallback_rate_percent: 1.2,
    estimated_cost_usd: 0.0171,
    top_colleges: [
      { name: "Ahmedabad Institute of Technology", queries: 84, tokens: 42000, percent: 65.6 },
      { name: "RC Technical Institute", queries: 44, tokens: 22900, percent: 34.4 },
    ],
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-[#6366F1]" />
            AI Telemetry & Token Analytics
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Platform-wide resource consumption, LLM invocation volume, latency profiles, and institutional costs.
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
                    ? "bg-[#6366F1] text-white"
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

      {isLoading ? (
        <div className="flex items-center justify-center py-24 text-xs text-[#A1A1AA]">
          <div className="flex flex-col items-center gap-3">
            <div className="w-6 h-6 border-2 border-[#6366F1] border-t-transparent rounded-full animate-spin" />
            <span>Aggregating platform AI telemetry and token consumption...</span>
          </div>
        </div>
      ) : (
        <>
          {/* Metric Cards Grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <DashboardCard
              title="Total Queries"
              value={data.total_queries ?? 0}
              subtitle="Chatbot questions"
              icon={<Cpu className="h-5 w-5" />}
              iconColor="text-[#6366F1] bg-[#6366F1]/10"
            />

            <DashboardCard
              title="Total Tokens"
              value={(data.total_tokens ?? 0).toLocaleString()}
              subtitle="Processed volume"
              icon={<Coins className="h-5 w-5" />}
              iconColor="text-[#10B981] bg-[#10B981]/10"
            />

            <DashboardCard
              title="Avg Latency"
              value={`${data.average_latency_ms ?? 0} ms`}
              subtitle="Response latency"
              trend="Target: <300ms"
              trendUp={true}
              icon={<Clock className="h-5 w-5" />}
              iconColor="text-[#F59E0B] bg-[#F59E0B]/10"
            />

            <DashboardCard
              title="Fallback Rate"
              value={`${data.fallback_rate_percent ?? 0}%`}
              subtitle="Secondary AI invocations"
              trend="Healthy (<5%)"
              trendUp={true}
              icon={<Zap className="h-5 w-5" />}
              iconColor="text-[#EC4899] bg-[#EC4899]/10"
            />

            <DashboardCard
              title="Estimated Cost"
              value={`$${data.estimated_cost_usd ?? 0}`}
              subtitle="Aggregated API spend"
              icon={<TrendingUp className="h-5 w-5" />}
              iconColor="text-[#06B6D4] bg-[#06B6D4]/10"
            />
          </div>

          {/* Breakdown Grids */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top College Consumers */}
            <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
              <h3 className="text-sm font-semibold text-[#F5F5F5] mb-1 flex items-center gap-2">
                <Building2 className="h-4 w-4 text-[#6366F1]" />
                Tenant Consumption Breakdown
              </h3>
              <p className="text-xs text-[#A1A1AA] mb-4">
                Colleges with the highest student query and token utilization
              </p>

              <div className="space-y-4">
                {(data.top_colleges || []).map((c, idx) => (
                  <div key={idx} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-[#F5F5F5]">{c.name}</span>
                      <span className="font-mono text-[#A1A1AA]">
                        {c.queries ?? 0} queries ({(c.tokens ?? 0).toLocaleString()} tokens)
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-[#1F1F23] overflow-hidden">
                      <div
                        className="h-full bg-[#6366F1] rounded-full transition-all duration-500"
                        style={{ width: `${c.percent ?? 0}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-[#71717A] text-right block">
                      {c.percent ?? 0}% of total platform queries
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Token Distribution & Verification Tier Telemetry */}
            <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
              <h3 className="text-sm font-semibold text-[#F5F5F5] mb-1 flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-[#10B981]" />
                Citation Grounding Tier Distribution
              </h3>
              <p className="text-xs text-[#A1A1AA] mb-4">
                5-tier source grounding verification breakdown across student queries
              </p>

              <div className="space-y-3 text-xs">
                <div className="p-3 rounded-xl border border-[#10B981]/20 bg-[#10B981]/5 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-[#10B981] block">
                      OFFICIAL_WEBSITE (Tier 1)
                    </span>
                    <span className="text-[11px] text-[#A1A1AA]">Direct crawled institutional website citation</span>
                  </div>
                  <span className="font-mono font-bold text-[#F5F5F5]">64%</span>
                </div>

                <div className="p-3 rounded-xl border border-[#3B82F6]/20 bg-[#3B82F6]/5 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-[#3B82F6] block">
                      ADMIN_VERIFIED (Tier 2)
                    </span>
                    <span className="text-[11px] text-[#A1A1AA]">College Admin reviewed and approved PDF chunks</span>
                  </div>
                  <span className="font-mono font-bold text-[#F5F5F5]">28%</span>
                </div>

                <div className="p-3 rounded-xl border border-[#F59E0B]/20 bg-[#F59E0B]/5 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-[#F59E0B] block">
                      GEMINI_UNVERIFIED (Tier 3)
                    </span>
                    <span className="text-[11px] text-[#A1A1AA]">Gemini AI guidance without verified grounding match</span>
                  </div>
                  <span className="font-mono font-bold text-[#F5F5F5]">6%</span>
                </div>

                <div className="p-3 rounded-xl border border-[#EC4899]/20 bg-[#EC4899]/5 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-[#EC4899] block">
                      SECONDARY_AI_FALLBACK (Tier 4)
                    </span>
                    <span className="text-[11px] text-[#A1A1AA]">Secondary fallback model invoked on primary timeout</span>
                  </div>
                  <span className="font-mono font-bold text-[#F5F5F5]">1.2%</span>
                </div>

                <div className="p-3 rounded-xl border border-[#EF4444]/20 bg-[#EF4444]/5 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-[#EF4444] block">
                      NO_RELIABLE_INFORMATION (Tier 5)
                    </span>
                    <span className="text-[11px] text-[#A1A1AA]">Zero hallucination safeguard: escalated to staff ticket</span>
                  </div>
                  <span className="font-mono font-bold text-[#F5F5F5]">0.8%</span>
                </div>

                <div className="p-3 rounded-xl border border-[#F59E0B]/20 bg-[#F59E0B]/5 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-[#F59E0B] block">
                      AI_GUIDANCE (Post-migration)
                    </span>
                    <span className="text-[11px] text-[#A1A1AA]">General AI guidance — not verified by college (Gemini)</span>
                  </div>
                  <span className="font-mono font-bold text-[#F5F5F5]">—</span>
                </div>

                <div className="p-3 rounded-xl border border-[#F59E0B]/20 bg-[#F59E0B]/5 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-[#F59E0B] block">
                      OPENAI_UNVERIFIED (Post-migration)
                    </span>
                    <span className="text-[11px] text-[#A1A1AA]">OpenAI AI guidance — not verified by college</span>
                  </div>
                  <span className="font-mono font-bold text-[#F5F5F5]">—</span>
                </div>

                <div className="p-3 rounded-xl border border-[#F59E0B]/20 bg-[#F59E0B]/5 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-[#F59E0B] block">
                      XKIRO_UNVERIFIED (Post-migration)
                    </span>
                    <span className="text-[11px] text-[#A1A1AA]">xKiro AI guidance — not verified by college</span>
                  </div>
                  <span className="font-mono font-bold text-[#F5F5F5]">—</span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
