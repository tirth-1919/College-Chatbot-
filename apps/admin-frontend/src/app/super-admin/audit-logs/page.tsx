"use client";

import React, { useEffect, useState } from "react";
import { superAdminService } from "@/services/super-admin-service";
import { AuditLogItem } from "@/types/admin";
import { DataTable, Column } from "@/components/DataTable";
import {
  ShieldAlert,
  FileText,
  RefreshCw,
  Eye,
  X,
  Code,
} from "lucide-react";

export default function SecurityAuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState("ALL");

  // Inspection modal
  const [inspectLog, setInspectLog] = useState<AuditLogItem | null>(null);

  const fetchLogs = async () => {
    setIsLoading(true);
    try {
      const res = await superAdminService.getAuditLogs({ limit: 100 });
      if (res.success && res.data) {
        setLogs(res.data);
      }
    } catch (err) {
      console.error("Failed to load audit trail:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const filteredLogs = logs.filter((l) => {
    if (actionFilter !== "ALL" && l.action_type !== actionFilter) return false;
    return true;
  });

  const columns: Column<AuditLogItem>[] = [
    {
      header: "Action Type",
      cell: (item) => (
        <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-[#1F1F23] text-[#6366F1] border border-[#6366F1]/20 font-semibold">
          {item.action_type}
        </span>
      ),
    },
    {
      header: "Target Entity",
      cell: (item) => (
        <div>
          <span className="text-xs text-[#F5F5F5] font-medium block">
            {item.target_entity}
          </span>
          <span className="text-[10px] text-[#71717A] font-mono">
            id: {item.target_id}
          </span>
        </div>
      ),
    },
    {
      header: "Administrative Actor",
      cell: (item) => (
        <div className="text-xs">
          <span className="text-[#D4D4D8] block">
            {item.actor_email || "System Service Account"}
          </span>
          <span className="text-[10px] text-[#71717A] font-mono">
            {item.actor_user_id || "SYSTEM"}
          </span>
        </div>
      ),
    },
    {
      header: "IP Address",
      cell: (item) => (
        <span className="font-mono text-[11px] text-[#A1A1AA]">
          {item.ip_address || "127.0.0.1"}
        </span>
      ),
    },
    {
      header: "Timestamp",
      cell: (item) => (
        <span className="text-[11px] text-[#71717A]">
          {new Date(item.created_at).toLocaleString()}
        </span>
      ),
    },
    {
      header: "Payload",
      className: "text-right",
      cell: (item) => (
        <button
          onClick={() => setInspectLog(item)}
          className="p-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
          title="Inspect change payload diff"
        >
          <Code className="h-3.5 w-3.5" />
        </button>
      ),
    },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-[#6366F1]" />
            Compliance Security Audit Stream
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Immutable log of super administrative actions, institutional approvals, configuration updates, and permission changes.
          </p>
        </div>

        <button
          onClick={fetchLogs}
          className="self-start sm:self-auto p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
          title="Refresh audit stream"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-[#2A2A30] pb-3 text-xs overflow-x-auto">
        {[
          "ALL",
          "COLLEGE_APPROVED",
          "COLLEGE_REJECTED",
          "AI_PROVIDER_CREATED",
          "AI_PROVIDER_UPDATED",
          "SYSTEM_SETTINGS_UPDATED",
          "COLLEGE_ADMIN_ASSIGNED",
        ].map((act) => (
          <button
            key={act}
            onClick={() => setActionFilter(act)}
            className={`px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition ${
              actionFilter === act
                ? "bg-[#6366F1] text-white"
                : "bg-[#18181B] text-[#A1A1AA] hover:text-[#F5F5F5]"
            }`}
          >
            {act}
          </button>
        ))}
      </div>

      {/* Audit Data Table */}
      <DataTable
        data={filteredLogs}
        columns={columns}
        searchPlaceholder="Search audit events by action, actor, target entity..."
        emptyMessage="No audit logs found matching criteria."
      />

      {/* Payload Inspection Modal */}
      {inspectLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-lg bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl relative">
            <button
              onClick={() => setInspectLog(null)}
              className="absolute top-4 right-4 text-[#71717A] hover:text-[#F5F5F5]"
            >
              <X className="h-4 w-4" />
            </button>

            <h3 className="text-base font-bold text-[#F5F5F5] mb-1">
              Audit Event Payload Diff
            </h3>
            <div className="flex items-center gap-2 text-xs text-[#A1A1AA] mb-4">
              <span className="font-mono text-[#6366F1]">{inspectLog.action_type}</span>
              <span>•</span>
              <span>{new Date(inspectLog.created_at).toLocaleString()}</span>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-[#71717A] block mb-1">Target Entity & ID:</span>
                <div className="p-2.5 rounded-lg bg-[#1F1F23] font-mono text-[#D4D4D8]">
                  {inspectLog.target_entity} / {inspectLog.target_id}
                </div>
              </div>

              <div>
                <span className="text-[#71717A] block mb-1">Payload Diff (JSON):</span>
                <pre className="p-3 rounded-lg bg-[#0B0B0D] border border-[#1F1F23] font-mono text-[11px] text-[#10B981] overflow-x-auto max-h-60">
                  {JSON.stringify(inspectLog.payload_diff || { message: "No extra diff recorded" }, null, 2)}
                </pre>
              </div>
            </div>

            <div className="pt-4 mt-4 border-t border-[#2A2A30] flex justify-end">
              <button
                onClick={() => setInspectLog(null)}
                className="px-4 py-2 bg-[#1F1F23] hover:bg-[#2A2A30] text-xs text-[#F5F5F5] rounded-lg transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

