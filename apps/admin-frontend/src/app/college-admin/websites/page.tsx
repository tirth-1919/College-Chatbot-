"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { collegeAdminService } from "@/services/college-admin-service";
import { WebsiteSource } from "@/types/college-admin";
import { DataTable, Column } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import {
  Globe,
  Plus,
  RefreshCw,
  PlayCircle,
  ExternalLink,
  Power,
  Trash2,
  X,
  Sliders,
  ShieldCheck,
} from "lucide-react";

export default function WebsiteSourcesPage() {
  const router = useRouter();
  const [sources, setSources] = useState<WebsiteSource[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Add source modal
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [newForm, setNewForm] = useState({
    base_url: "",
    allowed_subdomains: "",
    max_depth: 2,
    max_pages: 50,
    crawl_frequency: "WEEKLY",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Delete confirmation
  const [deletingSource, setDeletingSource] = useState<WebsiteSource | null>(null);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchSources = async () => {
    setIsLoading(true);
    try {
      const res = await collegeAdminService.getWebsites();
      if (res.success && res.data) {
        setSources(res.data);
      }
    } catch (err) {
      console.error("Failed to load website sources:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSources();
  }, []);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    try {
      const res = await collegeAdminService.createWebsite(newForm);
      if (res.success) {
        setIsAddOpen(false);
        setNewForm({
          base_url: "",
          allowed_subdomains: "",
          max_depth: 2,
          max_pages: 50,
          crawl_frequency: "WEEKLY",
        });
        fetchSources();
      } else {
        setFormError(res.error || "Failed to register website source.");
      }
    } catch (err: any) {
      setFormError(err.message || "An unexpected error occurred.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTriggerCrawl = async (sourceId: string) => {
    try {
      const res = await collegeAdminService.startCrawl(sourceId);
      if (res.success) {
        router.push("/college-admin/crawler");
      }
    } catch (err) {
      console.error("Failed to trigger crawl:", err);
    }
  };

  const handleToggleActive = async (source: WebsiteSource) => {
    try {
      await collegeAdminService.updateWebsite(source.id, {
        is_active: !source.is_active,
      });
      fetchSources();
    } catch (err) {
      console.error("Failed to toggle source:", err);
    }
  };

  const handleDelete = async () => {
    if (!deletingSource) return;
    setIsDeleting(true);

    try {
      await collegeAdminService.deleteWebsite(deletingSource.id);
      setIsDeleteOpen(false);
      setDeletingSource(null);
      fetchSources();
    } catch (err) {
      console.error("Failed to delete source:", err);
    } finally {
      setIsDeleting(false);
    }
  };

  const columns: Column<WebsiteSource>[] = [
    {
      header: "Website Target URL",
      cell: (item) => (
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-[#3B82F6]/10 text-[#3B82F6]">
            <Globe className="h-4 w-4" />
          </div>
          <div>
            <a
              href={item.base_url}
              target="_blank"
              rel="noreferrer"
              className="font-medium text-[#F5F5F5] hover:text-[#10B981] flex items-center gap-1 text-xs"
            >
              {item.base_url}
              <ExternalLink className="h-2.5 w-2.5" />
            </a>
            {item.allowed_subdomains && (
              <span className="text-[10px] text-[#71717A] font-mono block">
                Subdomains: {item.allowed_subdomains}
              </span>
            )}
          </div>
        </div>
      ),
    },
    {
      header: "Crawl Parameters",
      cell: (item) => (
        <div className="text-[11px] text-[#D4D4D8] space-y-0.5">
          <div>Depth: <span className="font-mono text-[#F5F5F5]">{item.max_depth} levels</span></div>
          <div>Page Cap: <span className="font-mono text-[#F5F5F5]">{item.max_pages} pages</span></div>
        </div>
      ),
    },
    {
      header: "Frequency",
      cell: (item) => (
        <span className="text-[10px] px-2 py-0.5 rounded bg-[#1F1F23] text-[#A1A1AA] border border-[#2A2A30] font-mono">
          {item.crawl_frequency}
        </span>
      ),
    },
    {
      header: "Status",
      cell: (item) => (
        <span
          className={`inline-flex items-center gap-1.5 text-[11px] font-medium ${
            item.is_active ? "text-[#10B981]" : "text-[#EF4444]"
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              item.is_active ? "bg-[#10B981]" : "bg-[#EF4444]"
            }`}
          />
          {item.is_active ? "Active" : "Disabled"}
        </span>
      ),
    },
    {
      header: "Last Crawled",
      cell: (item) => (
        <span className="text-[11px] text-[#71717A]">
          {item.last_crawled_at ? new Date(item.last_crawled_at).toLocaleString() : "Never"}
        </span>
      ),
    },
    {
      header: "Actions",
      className: "text-right",
      cell: (item) => (
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={() => handleTriggerCrawl(item.id)}
            className="p-1.5 rounded-lg bg-[#10B981]/10 text-[#10B981] hover:bg-[#10B981]/20 transition flex items-center gap-1 text-[11px] font-medium px-2.5"
            title="Start Crawl Now"
          >
            <PlayCircle className="h-3.5 w-3.5" />
            <span>Crawl</span>
          </button>
          <button
            onClick={() => handleToggleActive(item)}
            className="p-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
            title={item.is_active ? "Disable Source" : "Enable Source"}
          >
            <Power className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => {
              setDeletingSource(item);
              setIsDeleteOpen(true);
            }}
            className="p-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] text-[#A1A1AA] hover:text-[#EF4444] transition"
            title="Delete Source"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
            <Globe className="h-5 w-5 text-[#10B981]" />
            Official Website Sources & Crawl Scopes
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Register official institutional URLs, configure maximum discovery depth, and initiate automated Playwright website extractions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchSources}
            className="p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
            title="Refresh sources"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <button
            onClick={() => setIsAddOpen(true)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[#10B981] hover:bg-[#059669] text-white text-xs font-medium transition shadow-md shadow-[#10B981]/20"
          >
            <Plus className="h-4 w-4" />
            <span>Add Website Target</span>
          </button>
        </div>
      </div>

      {/* Sources Table */}
      <DataTable
        data={sources}
        columns={columns}
        searchPlaceholder="Search website sources by URL or frequency..."
        emptyMessage="No website sources registered. Add your official college portal to start crawling."
      />

      {/* Add Website Source Modal */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl relative">
            <button
              onClick={() => setIsAddOpen(false)}
              className="absolute top-4 right-4 text-[#71717A] hover:text-[#F5F5F5]"
            >
              <X className="h-4 w-4" />
            </button>

            <h3 className="text-base font-bold text-[#F5F5F5] mb-1">
              Register Official Website Target
            </h3>
            <p className="text-xs text-[#A1A1AA] mb-4">
              Playwright will periodically crawl and deconstruct pages from this domain.
            </p>

            {formError && (
              <div className="mb-4 p-3 rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/30 text-xs text-[#EF4444]">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Official Website Base URL *
                </label>
                <input
                  type="url"
                  required
                  value={newForm.base_url}
                  onChange={(e) => setNewForm({ ...newForm, base_url: e.target.value })}
                  placeholder="https://aitindia.in"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] font-mono focus:outline-none focus:border-[#10B981]"
                />
                <span className="text-[10px] text-[#71717A] block mt-0.5">
                  Anti-SSRF validated: Must be public HTTP/HTTPS target.
                </span>
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Allowed Subdomains (Optional)
                </label>
                <input
                  type="text"
                  value={newForm.allowed_subdomains}
                  onChange={(e) => setNewForm({ ...newForm, allowed_subdomains: e.target.value })}
                  placeholder="admissions.aitindia.in, courses.aitindia.in"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] font-mono focus:outline-none focus:border-[#10B981]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Max Link Depth (1-5)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="5"
                    value={newForm.max_depth}
                    onChange={(e) => setNewForm({ ...newForm, max_depth: parseInt(e.target.value) })}
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] font-mono focus:outline-none focus:border-[#10B981]"
                  />
                </div>
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Max Page Cap (5-500)
                  </label>
                  <input
                    type="number"
                    min="5"
                    max="500"
                    value={newForm.max_pages}
                    onChange={(e) => setNewForm({ ...newForm, max_pages: parseInt(e.target.value) })}
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] font-mono focus:outline-none focus:border-[#10B981]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Crawl Schedule Frequency
                </label>
                <select
                  value={newForm.crawl_frequency}
                  onChange={(e) => setNewForm({ ...newForm, crawl_frequency: e.target.value })}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                >
                  <option value="DAILY">Daily (High-frequency updates)</option>
                  <option value="WEEKLY">Weekly (Recommended for syllabi & general notices)</option>
                  <option value="MONTHLY">Monthly</option>
                </select>
              </div>

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-[#2A2A30]">
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="px-4 py-2 text-[#A1A1AA] hover:text-[#F5F5F5] bg-[#1F1F23] rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-[#10B981] hover:bg-[#059669] text-white rounded-lg transition font-medium"
                >
                  {isSubmitting ? "Registering..." : "Add Target"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={isDeleteOpen}
        title={`Remove Website Source: ${deletingSource?.base_url}`}
        description="Removing this website source will delete its crawling schedule and historical logs. Crawled knowledge chunks will remain unless manually cleaned up."
        confirmLabel="Remove Source"
        isDestructive={true}
        isLoading={isDeleting}
        onConfirm={handleDelete}
        onCancel={() => {
          setIsDeleteOpen(false);
          setDeletingSource(null);
        }}
      />
    </div>
  );
}

