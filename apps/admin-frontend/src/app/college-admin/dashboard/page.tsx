"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { collegeAdminService } from "@/services/college-admin-service";
import { CollegeAdminDashboard } from "@/types/college-admin";
import { DashboardCard } from "@/components/DashboardCard";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Globe,
  FileText,
  CheckSquare,
  Database,
  MessageSquare,
  LifeBuoy,
  Star,
  RefreshCw,
  Plus,
  ArrowRight,
  Upload,
  AlertTriangle,
  Building2,
  ExternalLink,
  ShieldCheck,
} from "lucide-react";

export default function CollegeAdminDashboardPage() {
  const [data, setData] = useState<CollegeAdminDashboard | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchDashboard = async () => {
    try {
      const res = await collegeAdminService.getDashboard();
      if (res.success && res.data) {
        setData(res.data);
      }
    } catch (err) {
      console.error("Failed to load college dashboard:", err);
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
          <div className="w-6 h-6 border-2 border-[#10B981] border-t-transparent rounded-full animate-spin" />
          <span>Loading institutional knowledge dashboard...</span>
        </div>
      </div>
    );
  }

  const college = data?.college;
  const stats = data?.stats || {
    total_website_sources: 0,
    total_crawled_pages: 0,
    total_documents: 0,
    pending_reviews: 0,
    published_chunks: 0,
    total_queries: 0,
    recent_crawls_count: 0,
    recent_documents_count: 0,
    satisfaction_score: 4.8,
    open_tickets_count: 0,
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Institutional Banner */}
      <div className="p-6 md:p-8 rounded-2xl border border-[#2A2A30] bg-gradient-to-r from-[#111114] to-[#18181B] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] bg-[#10B981]/10 text-[#10B981] font-mono uppercase px-2 py-0.5 rounded border border-[#10B981]/20">
              Institutional Admin Workspace
            </span>
            <span className="text-xs text-[#71717A]">• Tenant Isolated</span>
          </div>
          <h1 className="text-2xl font-bold text-[#F5F5F5] tracking-tight">
            {college?.name || "College Administration Dashboard"}
          </h1>
          <div className="flex items-center gap-3 mt-1 text-xs text-[#A1A1AA]">
            <span>Domain:</span>
            <a
              href={`https://${college?.official_domain}`}
              target="_blank"
              rel="noreferrer"
              className="text-[#10B981] hover:underline font-mono flex items-center gap-1"
            >
              {college?.official_domain}
              <ExternalLink className="h-3 w-3" />
            </a>
            <span>•</span>
            <span className="text-[#71717A]">
              Status: <StatusBadge status={college?.status || "APPROVED"} size="sm" />
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-xs font-medium text-[#D4D4D8] transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
            <span>Sync</span>
          </button>
          <Link
            href="/college-admin/documents"
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[#10B981] hover:bg-[#059669] text-xs font-medium text-white transition shadow-lg shadow-[#10B981]/20"
          >
            <Upload className="h-3.5 w-3.5" />
            <span>Upload PDF</span>
          </Link>
        </div>
      </div>

      {/* Pending Knowledge Alert (if any pending) */}
      {stats.pending_reviews > 0 && (
        <div className="p-4 rounded-xl bg-[#F59E0B]/10 border border-[#F59E0B]/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3 text-[#F59E0B]">
            <AlertTriangle className="h-5 w-5 shrink-0" />
            <div>
              <span className="font-bold block">
                {stats.pending_reviews} Extracted Facts Pending Human Verification
              </span>
              <span className="text-[#D4D4D8]">
                Extracted information cannot be used in verified student chatbot answers until approved by college staff.
              </span>
            </div>
          </div>
          <Link
            href="/college-admin/reviews"
            className="px-3.5 py-1.5 rounded-lg bg-[#F59E0B] text-black font-semibold hover:bg-[#D97706] transition text-xs shrink-0 self-start sm:self-auto"
          >
            Open Review Queue
          </Link>
        </div>
      )}

      {/* Onboarding Wizard Milestone Banner (Phase 6) */}
      <div className="p-4 rounded-xl bg-[#6366F1]/10 border border-[#6366F1]/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3 text-[#818CF8]">
          <ShieldCheck className="h-5 w-5 shrink-0 text-[#6366F1]" />
          <div>
            <span className="font-bold text-[#F5F5F5] block">
              Institutional Onboarding Milestones
            </span>
            <span className="text-[#A1A1AA]">
              Configure website crawler parameters, upload prospectus PDFs, and learn the human review workflow.
            </span>
          </div>
        </div>
        <Link
          href="/college-admin/onboarding"
          className="px-3.5 py-1.5 rounded-lg bg-[#6366F1] text-white font-medium hover:bg-[#4F46E5] transition text-xs shrink-0 self-start sm:self-auto flex items-center gap-1.5 shadow-md shadow-[#6366F1]/20"
        >
          <span>Open Onboarding Wizard</span>
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      {/* 8 Dashboard Metric Cards (4x2 grid) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <DashboardCard
          title="Website Sources"
          value={stats.total_website_sources}
          subtitle="Official crawler domains"
          icon={<Globe className="h-5 w-5" />}
          iconColor="text-[#3B82F6] bg-[#3B82F6]/10"
          href="/college-admin/websites"
        />

        <DashboardCard
          title="Crawled Pages"
          value={stats.total_crawled_pages}
          subtitle="Ingested web pages"
          icon={<Database className="h-5 w-5" />}
          iconColor="text-[#6366F1] bg-[#6366F1]/10"
          href="/college-admin/crawler"
        />

        <DashboardCard
          title="Uploaded Documents"
          value={stats.total_documents}
          subtitle="PDF circulars & syllabi"
          icon={<FileText className="h-5 w-5" />}
          iconColor="text-[#10B981] bg-[#10B981]/10"
          href="/college-admin/documents"
        />

        <DashboardCard
          title="Pending Reviews"
          value={stats.pending_reviews}
          subtitle="Awaiting staff approval"
          trend={stats.pending_reviews > 0 ? "Action Required" : "Up to date"}
          trendUp={stats.pending_reviews === 0}
          icon={<CheckSquare className="h-5 w-5" />}
          iconColor="text-[#F59E0B] bg-[#F59E0B]/10"
          href="/college-admin/reviews"
        />

        <DashboardCard
          title="Published Chunks"
          value={stats.published_chunks}
          subtitle="Live searchable facts"
          icon={<Database className="h-5 w-5" />}
          iconColor="text-[#8B5CF6] bg-[#8B5CF6]/10"
          href="/college-admin/knowledge"
        />

        <DashboardCard
          title="Student Questions"
          value={stats.total_queries}
          subtitle="Inquiries answered"
          trend="+22% this week"
          trendUp={true}
          icon={<MessageSquare className="h-5 w-5" />}
          iconColor="text-[#EC4899] bg-[#EC4899]/10"
          href="/college-admin/analytics"
        />

        <DashboardCard
          title="Escalated Tickets"
          value={stats.open_tickets_count}
          subtitle="Staff assistance needed"
          icon={<LifeBuoy className="h-5 w-5" />}
          iconColor="text-[#EF4444] bg-[#EF4444]/10"
          href="/college-admin/support"
        />

        <DashboardCard
          title="Student Rating"
          value={`${stats.satisfaction_score} / 5`}
          subtitle="Satisfaction score"
          trend="Positive"
          trendUp={true}
          icon={<Star className="h-5 w-5" />}
          iconColor="text-[#F59E0B] bg-[#F59E0B]/10"
          href="/college-admin/analytics"
        />
      </div>

      {/* Two Column Section: Recent Crawl Executions & Ingested Documents */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Crawls */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F5]">
                Recent Crawler Executions
              </h3>
              <p className="text-[11px] text-[#A1A1AA]">
                Playwright automated website runs
              </p>
            </div>
            <Link
              href="/college-admin/crawler"
              className="text-xs text-[#10B981] hover:underline flex items-center gap-1 font-medium"
            >
              <span>Crawler Console</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="divide-y divide-[#1F1F23]">
            {data?.recent_crawl_jobs && data.recent_crawl_jobs.length > 0 ? (
              data.recent_crawl_jobs.map((j) => (
                <div key={j.id} className="py-3 flex items-center justify-between text-xs">
                  <div>
                    <span className="font-mono text-[#F5F5F5] block truncate max-w-xs">
                      Job: {j.id.substring(0, 8)}...
                    </span>
                    <span className="text-[10px] text-[#71717A]">
                      Discovered: {j.pages_discovered} • Crawled: {j.pages_crawled}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={j.status} />
                    <span className="text-[10px] text-[#71717A]">
                      {new Date(j.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-xs text-[#71717A]">
                No crawl runs initiated yet.
              </div>
            )}
          </div>
        </div>

        {/* Recent Documents */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F5]">
                Uploaded Institutional Documents
              </h3>
              <p className="text-[11px] text-[#A1A1AA]">
                PDF circulars ingested into vector database
              </p>
            </div>
            <Link
              href="/college-admin/documents"
              className="text-xs text-[#10B981] hover:underline flex items-center gap-1 font-medium"
            >
              <span>Document Center</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="divide-y divide-[#1F1F23]">
            {data?.recent_documents && data.recent_documents.length > 0 ? (
              data.recent_documents.map((d) => (
                <div key={d.id} className="py-3 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2.5 truncate max-w-xs">
                    <FileText className="h-4 w-4 text-[#10B981] shrink-0" />
                    <div>
                      <span className="font-medium text-[#F5F5F5] block truncate">
                        {d.original_filename}
                      </span>
                      <span className="text-[10px] text-[#71717A]">
                        {Math.round(d.file_size_bytes / 1024)} KB
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={d.processing_status} />
                    <span className="text-[10px] text-[#71717A]">
                      {new Date(d.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-xs text-[#71717A]">
                No PDF circulars uploaded yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
