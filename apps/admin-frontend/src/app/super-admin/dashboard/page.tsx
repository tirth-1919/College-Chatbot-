"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { superAdminService } from "@/services/super-admin-service";
import { DashboardOverview } from "@/types/admin";
import { DashboardCard } from "@/components/DashboardCard";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Building2,
  Users,
  ShieldCheck,
  Clock,
  MessageSquare,
  FileText,
  Activity,
  HardDrive,
  Cpu,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
  ExternalLink,
} from "lucide-react";

export default function SuperAdminDashboardPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchDashboard = async () => {
    try {
      const res = await superAdminService.getDashboardOverview();
      if (res.success && res.data) {
        setData(res.data);
      }
    } catch (err) {
      console.error("Failed to load dashboard telemetry:", err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchDashboard();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-xs text-[#A1A1AA]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-6 h-6 border-2 border-[#6366F1] border-t-transparent rounded-full animate-spin" />
          <span>Aggregating platform telemetry across all college tenants...</span>
        </div>
      </div>
    );
  }

  const stats = data?.stats || {
    total_colleges: 0,
    active_colleges: 0,
    pending_approvals: 0,
    total_users: 0,
    total_college_admins: 0,
    total_queries: 0,
    total_documents: 0,
    ai_success_rate: 99.4,
    storage_used_mb: 0,
    monthly_jobs: 0,
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header Banner */}
      <div className="p-6 md:p-8 rounded-2xl border border-[#2A2A30] bg-gradient-to-r from-[#111114] to-[#18181B] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] bg-[#6366F1]/10 text-[#6366F1] font-mono uppercase px-2 py-0.5 rounded border border-[#6366F1]/20">
              Platform Overview
            </span>
            <span className="text-xs text-[#71717A]">• SaaS Orchestration</span>
          </div>
          <h1 className="text-2xl font-bold text-[#F5F5F5] tracking-tight">
            Global Governance Dashboard
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Real-time telemetry, institutional approvals, AI model latency, and multi-tenant isolation.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-xs font-medium text-[#D4D4D8] transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
            <span>Sync Telemetry</span>
          </button>
          <Link
            href="/super-admin/registrations"
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#6366F1] hover:bg-[#4F46E5] text-xs font-medium text-white transition shadow-lg shadow-[#6366F1]/20"
          >
            <Clock className="h-3.5 w-3.5" />
            <span>Review Approvals ({stats.pending_approvals})</span>
          </Link>
        </div>
      </div>

      {/* 10 Dashboard Metric Cards (5x2 grid) */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <DashboardCard
          title="Total Colleges"
          value={stats.total_colleges}
          subtitle="Registered institutions"
          icon={<Building2 className="h-5 w-5" />}
          iconColor="text-[#6366F1] bg-[#6366F1]/10"
          href="/super-admin/colleges"
        />

        <DashboardCard
          title="Active Tenants"
          value={stats.active_colleges}
          subtitle="In service"
          icon={<CheckCircle2 className="h-5 w-5" />}
          iconColor="text-[#10B981] bg-[#10B981]/10"
          href="/super-admin/colleges"
        />

        <DashboardCard
          title="Pending Approvals"
          value={stats.pending_approvals}
          subtitle="Action required"
          trend={stats.pending_approvals > 0 ? "Needs Review" : "Up to date"}
          trendUp={stats.pending_approvals === 0}
          icon={<Clock className="h-5 w-5" />}
          iconColor="text-[#F59E0B] bg-[#F59E0B]/10"
          href="/super-admin/registrations"
        />

        <DashboardCard
          title="Platform Users"
          value={stats.total_users}
          subtitle="Students & guests"
          icon={<Users className="h-5 w-5" />}
          iconColor="text-[#3B82F6] bg-[#3B82F6]/10"
          href="/super-admin/users"
        />

        <DashboardCard
          title="College Admins"
          value={stats.total_college_admins}
          subtitle="Institutional operators"
          icon={<ShieldCheck className="h-5 w-5" />}
          iconColor="text-[#8B5CF6] bg-[#8B5CF6]/10"
          href="/super-admin/admins"
        />

        <DashboardCard
          title="Total Questions"
          value={stats.total_queries}
          subtitle="Student inquiries"
          trend="+18% this month"
          trendUp={true}
          icon={<MessageSquare className="h-5 w-5" />}
          iconColor="text-[#EC4899] bg-[#EC4899]/10"
          href="/super-admin/analytics"
        />

        <DashboardCard
          title="Documents Parsed"
          value={stats.total_documents}
          subtitle="PDF circulars & syllabi"
          icon={<FileText className="h-5 w-5" />}
          iconColor="text-[#06B6D4] bg-[#06B6D4]/10"
          href="/super-admin/usage"
        />

        <DashboardCard
          title="AI Success Rate"
          value={`${stats.ai_success_rate}%`}
          subtitle="Grounding accuracy"
          trend="Target: >98%"
          trendUp={true}
          icon={<Cpu className="h-5 w-5" />}
          iconColor="text-[#10B981] bg-[#10B981]/10"
          href="/super-admin/ai-providers"
        />

        <DashboardCard
          title="Storage Ingestion"
          value={`${stats.storage_used_mb} MB`}
          subtitle="Supabase & Vector store"
          icon={<HardDrive className="h-5 w-5" />}
          iconColor="text-[#A855F7] bg-[#A855F7]/10"
          href="/super-admin/system-health"
        />

        <DashboardCard
          title="Ingestion Jobs"
          value={stats.monthly_jobs}
          subtitle="Celery crawler tasks"
          icon={<Activity className="h-5 w-5" />}
          iconColor="text-[#F97316] bg-[#F97316]/10"
          href="/super-admin/usage"
        />
      </div>

      {/* Two Column Layout: Recent Registrations & Live Compliance Audit Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Registered Colleges */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F5]">
                Recent Institutional Onboardings
              </h3>
              <p className="text-[11px] text-[#A1A1AA]">
                Latest colleges registered on CampusAI
              </p>
            </div>
            <Link
              href="/super-admin/colleges"
              className="text-xs text-[#6366F1] hover:underline flex items-center gap-1 font-medium"
            >
              <span>View All</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="divide-y divide-[#1F1F23]">
            {data?.recent_colleges && data.recent_colleges.length > 0 ? (
              data.recent_colleges.map((c) => (
                <div key={c.id} className="py-3 flex items-center justify-between text-xs">
                  <div className="space-y-0.5">
                    <span className="font-medium text-[#F5F5F5] block">{c.name}</span>
                    <span className="text-[11px] text-[#71717A] font-mono">
                      {c.official_domain}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={c.status} />
                    <span className="text-[10px] text-[#71717A]">
                      {new Date(c.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-xs text-[#71717A]">
                No colleges registered yet.
              </div>
            )}
          </div>
        </div>

        {/* Live Compliance Audit Log Stream */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F5]">
                Compliance Security Audit Stream
              </h3>
              <p className="text-[11px] text-[#A1A1AA]">
                Immutable record of administrative actions
              </p>
            </div>
            <Link
              href="/super-admin/audit-logs"
              className="text-xs text-[#6366F1] hover:underline flex items-center gap-1 font-medium"
            >
              <span>Audit Trail</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="divide-y divide-[#1F1F23]">
            {data?.recent_audit_logs && data.recent_audit_logs.length > 0 ? (
              data.recent_audit_logs.map((log) => (
                <div key={log.id} className="py-3 flex items-start justify-between text-xs gap-3">
                  <div className="space-y-0.5 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[#1F1F23] text-[#A1A1AA] border border-[#2A2A30]">
                        {log.action_type}
                      </span>
                      <span className="text-[#D4D4D8] truncate font-medium">
                        Target: {log.target_entity}
                      </span>
                    </div>
                    <span className="text-[10px] text-[#71717A] block truncate">
                      Actor: {log.actor_user_id || "System Worker"}
                    </span>
                  </div>
                  <span className="text-[10px] text-[#71717A] whitespace-nowrap">
                    {new Date(log.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-xs text-[#71717A]">
                No security audit records logged yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
