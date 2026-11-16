"use client";

import React, { useEffect, useState } from "react";
import { superAdminService } from "@/services/super-admin-service";
import { JobOverview } from "@/types/admin";
import { DataTable, Column } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Activity,
  Globe,
  FileText,
  RefreshCw,
  Building2,
  AlertCircle,
} from "lucide-react";

export default function BackgroundJobsMonitorPage() {
  const [jobs, setJobs] = useState<JobOverview[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const fetchJobs = async () => {
    setIsLoading(true);
    try {
      const res = await superAdminService.getBackgroundJobs();
      if (res.success && res.data) {
        setJobs(res.data);
      }
    } catch (err) {
      console.error("Failed to load background ingestion jobs:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const filteredJobs = jobs.filter((j) => {
    if (typeFilter !== "ALL" && j.job_type !== typeFilter) return false;
    if (statusFilter !== "ALL" && j.status !== statusFilter) return false;
    return true;
  });

  const columns: Column<JobOverview>[] = [
    {
      header: "Job Type & Target",
      cell: (item) => (
        <div className="flex items-center gap-3">
          <div
            className={`p-2 rounded-lg ${
              item.job_type === "CRAWLER"
                ? "bg-[#3B82F6]/10 text-[#3B82F6]"
                : "bg-[#8B5CF6]/10 text-[#8B5CF6]"
            }`}
          >
            {item.job_type === "CRAWLER" ? (
              <Globe className="h-4 w-4" />
            ) : (
              <FileText className="h-4 w-4" />
            )}
          </div>
          <div>
            <span className="font-semibold text-[#F5F5F5] block text-xs truncate max-w-xs sm:max-w-md">
              {item.target_name}
            </span>
            <span className="text-[10px] text-[#71717A] font-mono uppercase">
              {item.job_type}
            </span>
          </div>
        </div>
      ),
    },
    {
      header: "Institution",
      cell: (item) => (
        <div className="flex items-center gap-1.5 text-xs text-[#D4D4D8]">
          <Building2 className="h-3 w-3 text-[#71717A]" />
          <span>{item.college_name}</span>
        </div>
      ),
    },
    {
      header: "Progress",
      cell: (item) => (
        <div className="w-32 space-y-1">
          <div className="flex items-center justify-between text-[10px] text-[#71717A]">
            <span>{item.progress_percent}%</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-[#1F1F23] overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                item.status === "FAILED"
                  ? "bg-[#EF4444]"
                  : item.progress_percent === 100
                  ? "bg-[#10B981]"
                  : "bg-[#6366F1]"
              }`}
              style={{ width: `${item.progress_percent}%` }}
            />
          </div>
        </div>
      ),
    },
    {
      header: "Status",
      cell: (item) => <StatusBadge status={item.status} />,
    },
    {
      header: "Initiated",
      cell: (item) => (
        <span className="text-[11px] text-[#71717A]">
          {new Date(item.created_at).toLocaleString()}
        </span>
      ),
    },
    {
      header: "Details / Logs",
      cell: (item) =>
        item.error_message ? (
          <span className="text-[11px] text-[#EF4444] flex items-center gap-1 truncate max-w-xs">
            <AlertCircle className="h-3 w-3 min-w-3" />
            {item.error_message}
          </span>
        ) : (
          <span className="text-[11px] text-[#71717A]">Normal execution</span>
        ),
    },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
            <Activity className="h-5 w-5 text-[#6366F1]" />
            Background Ingestion & Job Monitor
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Real-time telemetry across multi-tenant website crawler tasks and PDF OCR extraction pipelines.
          </p>
        </div>

        <button
          onClick={fetchJobs}
          className="self-start sm:self-auto p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
          title="Refresh background jobs"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-3 border-b border-[#2A2A30] pb-3 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-[#71717A]">Type:</span>
          {["ALL", "CRAWLER", "DOCUMENT_PROCESSING"].map((tp) => (
            <button
              key={tp}
              onClick={() => setTypeFilter(tp)}
              className={`px-3 py-1 rounded-lg font-medium transition ${
                typeFilter === tp
                  ? "bg-[#6366F1] text-white"
                  : "bg-[#18181B] text-[#A1A1AA] hover:text-[#F5F5F5]"
              }`}
            >
              {tp}
            </button>
          ))}
        </div>

        <div className="h-4 w-px bg-[#2A2A30] mx-1 hidden sm:block" />

        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-[#71717A]">Status:</span>
          {["ALL", "COMPLETED", "RUNNING", "FAILED"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1 rounded-lg font-medium transition ${
                statusFilter === st
                  ? "bg-[#6366F1] text-white"
                  : "bg-[#18181B] text-[#A1A1AA] hover:text-[#F5F5F5]"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Jobs Table */}
      <DataTable
        data={filteredJobs}
        columns={columns}
        searchPlaceholder="Search by URL, document name, or institution..."
        emptyMessage="No background ingestion tasks found matching filter criteria."
      />
    </div>
  );
}

