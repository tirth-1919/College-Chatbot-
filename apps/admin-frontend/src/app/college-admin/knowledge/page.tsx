"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { collegeAdminService } from "@/services/college-admin-service";
import { KnowledgeChunk } from "@/types/college-admin";
import { DataTable, Column } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Database,
  Globe,
  FileText,
  Layers,
  RefreshCw,
  ExternalLink,
  CheckSquare,
  Search,
  CheckCircle2,
  Tag,
  Filter,
} from "lucide-react";

const CATEGORIES = [
  "ALL",
  "ADMISSIONS",
  "COURSES",
  "FEES",
  "SCHOLARSHIPS",
  "EXAMINATIONS",
  "RESULTS",
  "ACADEMIC_CALENDAR",
  "FACILITIES",
  "HOSTEL",
  "LIBRARY",
  "PLACEMENT",
  "CONTACT",
  "RULES",
  "DEPARTMENTS",
  "OTHER",
];

export default function KnowledgeBaseExplorerPage() {
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [sourceTypeFilter, setSourceTypeFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchKnowledge = async () => {
    setIsLoading(true);
    try {
      const res = await collegeAdminService.getKnowledge({
        status: statusFilter === "ALL" ? undefined : statusFilter,
        source_type: sourceTypeFilter === "ALL" ? undefined : sourceTypeFilter,
        limit: 100,
      });
      if (res.success && res.data) {
        let items = res.data;
        if (categoryFilter !== "ALL") {
          items = items.filter((c) => (c.category || "OTHER") === categoryFilter);
        }
        setChunks(items);
      }
    } catch (err) {
      console.error("Failed to load knowledge base:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchKnowledge();
  }, [sourceTypeFilter, statusFilter, categoryFilter]);

  const handlePublish = async (chunkId: string) => {
    try {
      const res = await collegeAdminService.publishKnowledgeChunk(chunkId);
      if (res.success) {
        setActionMessage("Chunk published to live student vector retrieval.");
        fetchKnowledge();
        setTimeout(() => setActionMessage(null), 3000);
      }
    } catch (err) {
      console.error("Failed to publish chunk:", err);
    }
  };

  const handleUnpublish = async (chunkId: string) => {
    try {
      const res = await collegeAdminService.unpublishKnowledgeChunk(chunkId);
      if (res.success) {
        setActionMessage("Chunk unpublished and removed from active vector search.");
        fetchKnowledge();
        setTimeout(() => setActionMessage(null), 3000);
      }
    } catch (err) {
      console.error("Failed to unpublish chunk:", err);
    }
  };

  const columns: Column<KnowledgeChunk>[] = [
    {
      header: "Source Origin",
      cell: (item) => (
        <div className="flex items-center gap-2">
          <div
            className={`p-1.5 rounded-lg ${
              item.source_type === "WEBSITE" || item.source_type === "OFFICIAL_WEBSITE"
                ? "bg-[#3B82F6]/10 text-[#3B82F6]"
                : item.source_type === "DOCUMENT" || item.source_type === "PDF"
                ? "bg-[#10B981]/10 text-[#10B981]"
                : "bg-[#8B5CF6]/10 text-[#8B5CF6]"
            }`}
          >
            {item.source_type === "WEBSITE" || item.source_type === "OFFICIAL_WEBSITE" ? (
              <Globe className="h-3.5 w-3.5" />
            ) : item.source_type === "DOCUMENT" || item.source_type === "PDF" ? (
              <FileText className="h-3.5 w-3.5" />
            ) : (
              <Layers className="h-3.5 w-3.5" />
            )}
          </div>
          <div>
            <span className="font-mono text-[10px] text-[#A1A1AA] uppercase block">
              {item.source_type}
            </span>
            {item.source_url ? (
              <a
                href={item.source_url}
                target="_blank"
                rel="noreferrer"
                className="text-[11px] text-[#10B981] hover:underline font-mono truncate max-w-xs block flex items-center gap-1"
              >
                {item.source_url}
                <ExternalLink className="h-2.5 w-2.5 shrink-0" />
              </a>
            ) : item.page_number ? (
              <span className="text-[11px] text-[#71717A] font-mono">
                Page {item.page_number}
              </span>
            ) : (
              <span className="text-[11px] text-[#71717A]">Admin Curated</span>
            )}
          </div>
        </div>
      ),
    },
    {
      header: "Category & Section",
      cell: (item) => (
        <div className="space-y-1">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-[#1F1F23] border border-[#2A2A30] text-[#A1A1AA]">
            <Tag className="h-2.5 w-2.5 text-[#6366F1]" />
            {item.category || "OTHER"}
          </span>
          {item.heading && (
            <span className="text-[11px] text-[#D4D4D8] block font-medium truncate max-w-[200px]">
              {item.heading}
            </span>
          )}
        </div>
      ),
    },
    {
      header: "Factual Chunk Text",
      cell: (item) => (
        <div className="max-w-md sm:max-w-xl py-1">
          <p className="text-xs text-[#D4D4D8] leading-relaxed line-clamp-2">
            "{item.chunk_text}"
          </p>
        </div>
      ),
    },
    {
      header: "Status",
      cell: (item) => <StatusBadge status={item.status} />,
    },
    {
      header: "Actions",
      cell: (item) => (
        <div className="flex items-center gap-2">
          {item.status === "APPROVED" && (
            <button
              onClick={() => handlePublish(item.id)}
              className="px-2.5 py-1 rounded bg-[#10B981]/10 border border-[#10B981]/30 hover:bg-[#10B981]/20 text-[#10B981] text-[11px] font-medium transition"
              title="Promote to live student vector retrieval"
            >
              Publish
            </button>
          )}
          {item.status === "PUBLISHED" && (
            <button
              onClick={() => handleUnpublish(item.id)}
              className="px-2.5 py-1 rounded bg-[#EF4444]/10 border border-[#EF4444]/30 hover:bg-[#EF4444]/20 text-[#EF4444] text-[11px] font-medium transition"
              title="Unpublish from live search"
            >
              Unpublish
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Toast Notification */}
      {actionMessage && (
        <div className="p-3 rounded-xl bg-[#10B981]/10 border border-[#10B981]/30 text-[#10B981] text-xs flex items-center gap-2 animate-fade-in">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
            <Database className="h-5 w-5 text-[#10B981]" />
            Institutional Knowledge Base Explorer
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Browse deconstructed semantic chunks generated from website crawling, uploaded PDF circulars, and verified structured facts.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchKnowledge}
            className="p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
            title="Refresh knowledge base"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <Link
            href="/college-admin/reviews"
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[#F59E0B]/10 border border-[#F59E0B]/30 hover:bg-[#F59E0B]/20 text-[#F59E0B] text-xs font-medium transition"
          >
            <CheckSquare className="h-4 w-4" />
            <span>Open Review Queue</span>
          </Link>
        </div>
      </div>

      {/* Category Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none text-xs">
        <span className="text-[11px] text-[#71717A] flex items-center gap-1 shrink-0">
          <Filter className="h-3 w-3" />
          Category:
        </span>
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategoryFilter(cat)}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-medium shrink-0 transition ${
              categoryFilter === cat
                ? "bg-[#6366F1] text-white"
                : "bg-[#18181B] text-[#A1A1AA] hover:text-[#F5F5F5] border border-[#2A2A30]"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-3 border-b border-[#2A2A30] pb-3 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-[#71717A]">Origin:</span>
          {["ALL", "WEBSITE", "DOCUMENT", "ADMIN_STRUCTURED"].map((t) => (
            <button
              key={t}
              onClick={() => setSourceTypeFilter(t)}
              className={`px-3 py-1 rounded-lg font-medium transition ${
                sourceTypeFilter === t
                  ? "bg-[#10B981] text-white"
                  : "bg-[#18181B] text-[#A1A1AA] hover:text-[#F5F5F5]"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <div className="h-4 w-px bg-[#2A2A30] mx-1 hidden sm:block" />

        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-[#71717A]">Verification:</span>
          {["ALL", "PUBLISHED", "APPROVED", "PENDING_REVIEW", "REJECTED"].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1 rounded-lg font-medium transition ${
                statusFilter === s
                  ? "bg-[#10B981] text-white"
                  : "bg-[#18181B] text-[#A1A1AA] hover:text-[#F5F5F5]"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Data Table */}
      <DataTable
        data={chunks}
        columns={columns}
        searchPlaceholder="Search knowledge text, category, or source..."
        emptyMessage="No knowledge chunks match the selected criteria."
      />
    </div>
  );
}
