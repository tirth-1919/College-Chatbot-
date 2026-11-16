"use client";

import React, { useEffect, useState } from "react";
import { superAdminService } from "@/services/super-admin-service";
import { College } from "@/types/admin";
import { DataTable, Column } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import {
  Building2,
  Plus,
  ExternalLink,
  ShieldAlert,
  CheckCircle,
  XCircle,
  Power,
  RefreshCw,
  X,
} from "lucide-react";

export default function CollegesManagementPage() {
  const [colleges, setColleges] = useState<College[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>("ALL");

  // Create college dialog state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: "",
    slug: "",
    official_domain: "",
    contact_email: "",
    contact_phone: "",
    logo_url: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Status toggle confirmation dialog state
  const [selectedCollege, setSelectedCollege] = useState<College | null>(null);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<"TOGGLE_ACTIVE" | "APPROVE" | "REJECT">("TOGGLE_ACTIVE");
  const [isActionLoading, setIsActionLoading] = useState(false);

  const fetchColleges = async () => {
    setIsLoading(true);
    try {
      const res = await superAdminService.getColleges(true);
      if (res.success && res.data) {
        setColleges(res.data);
      }
    } catch (err) {
      console.error("Failed to load colleges:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchColleges();
  }, []);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    try {
      const res = await superAdminService.createCollege(createForm);
      if (res.success) {
        setIsCreateOpen(false);
        setCreateForm({
          name: "",
          slug: "",
          official_domain: "",
          contact_email: "",
          contact_phone: "",
          logo_url: "",
        });
        fetchColleges();
      } else {
        setFormError(res.error || "Failed to create college tenant.");
      }
    } catch (err: any) {
      setFormError(err.message || "An unexpected error occurred.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExecuteAction = async () => {
    if (!selectedCollege) return;
    setIsActionLoading(true);

    try {
      if (confirmAction === "TOGGLE_ACTIVE") {
        await superAdminService.updateCollege(selectedCollege.id, {
          is_active: !selectedCollege.is_active,
        });
      } else if (confirmAction === "APPROVE") {
        await superAdminService.approveRegistration(selectedCollege.id, "Approved from college directory");
      } else if (confirmAction === "REJECT") {
        await superAdminService.rejectRegistration(selectedCollege.id, "Rejected from college directory");
      }
      setIsConfirmOpen(false);
      setSelectedCollege(null);
      fetchColleges();
    } catch (err) {
      console.error("Failed to execute college action:", err);
    } finally {
      setIsActionLoading(false);
    }
  };

  const filteredColleges = colleges.filter((c) => {
    if (filterStatus === "ALL") return true;
    return c.status === filterStatus;
  });

  const columns: Column<College>[] = [
    {
      header: "College Name & Domain",
      cell: (item) => (
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-[#1F1F23] border border-[#2A2A30] flex items-center justify-center text-xs font-bold text-[#6366F1]">
            {item.name.substring(0, 2).toUpperCase()}
          </div>
          <div>
            <span className="font-semibold text-[#F5F5F5] block text-xs">
              {item.name}
            </span>
            <div className="flex items-center gap-2 text-[11px] text-[#71717A]">
              <span className="font-mono">slug: {item.slug}</span>
              <span>•</span>
              <a
                href={`https://${item.official_domain}`}
                target="_blank"
                rel="noreferrer"
                className="hover:text-[#6366F1] flex items-center gap-1 font-mono text-[10px]"
              >
                {item.official_domain}
                <ExternalLink className="h-2.5 w-2.5" />
              </a>
            </div>
          </div>
        </div>
      ),
    },
    {
      header: "Contact Email",
      accessorKey: "contact_email",
      cell: (item) => (
        <span className="font-mono text-[11px] text-[#D4D4D8]">
          {item.contact_email}
        </span>
      ),
    },
    {
      header: "Status",
      cell: (item) => <StatusBadge status={item.status} />,
    },
    {
      header: "Service State",
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
          {item.is_active ? "Active" : "Suspended"}
        </span>
      ),
    },
    {
      header: "Created",
      cell: (item) => (
        <span className="text-[11px] text-[#71717A]">
          {new Date(item.created_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      header: "Actions",
      className: "text-right",
      cell: (item) => (
        <div className="flex items-center justify-end gap-2">
          {item.status === "PENDING" && (
            <>
              <button
                onClick={() => {
                  setSelectedCollege(item);
                  setConfirmAction("APPROVE");
                  setIsConfirmOpen(true);
                }}
                className="p-1.5 rounded-lg bg-[#10B981]/10 text-[#10B981] hover:bg-[#10B981]/20 transition"
                title="Approve Tenant"
              >
                <CheckCircle className="h-4 w-4" />
              </button>
              <button
                onClick={() => {
                  setSelectedCollege(item);
                  setConfirmAction("REJECT");
                  setIsConfirmOpen(true);
                }}
                className="p-1.5 rounded-lg bg-[#EF4444]/10 text-[#EF4444] hover:bg-[#EF4444]/20 transition"
                title="Reject Onboarding"
              >
                <XCircle className="h-4 w-4" />
              </button>
            </>
          )}

          <button
            onClick={() => {
              setSelectedCollege(item);
              setConfirmAction("TOGGLE_ACTIVE");
              setIsConfirmOpen(true);
            }}
            className={`p-1.5 rounded-lg border transition ${
              item.is_active
                ? "bg-[#1F1F23] border-[#2A2A30] text-[#A1A1AA] hover:text-[#EF4444] hover:border-[#EF4444]/30"
                : "bg-[#10B981]/10 border-[#10B981]/30 text-[#10B981] hover:bg-[#10B981]/20"
            }`}
            title={item.is_active ? "Suspend College" : "Activate College"}
          >
            <Power className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Page Title & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
            <Building2 className="h-5 w-5 text-[#6366F1]" />
            Colleges & Tenant Management
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Super Administrator oversight of institutional tenants, onboarding states, and domain isolation.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchColleges}
            className="p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
            title="Refresh list"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[#6366F1] hover:bg-[#4F46E5] text-white text-xs font-medium transition shadow-md shadow-[#6366F1]/20"
          >
            <Plus className="h-4 w-4" />
            <span>Onboard College</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-[#2A2A30] pb-3 text-xs">
        {["ALL", "APPROVED", "PENDING", "REJECTED", "SUSPENDED"].map((st) => (
          <button
            key={st}
            onClick={() => setFilterStatus(st)}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              filterStatus === st
                ? "bg-[#6366F1] text-white"
                : "bg-[#18181B] text-[#A1A1AA] hover:text-[#F5F5F5]"
            }`}
          >
            {st} ({st === "ALL" ? colleges.length : colleges.filter((c) => c.status === st).length})
          </button>
        ))}
      </div>

      {/* Data Table */}
      <DataTable
        data={filteredColleges}
        columns={columns}
        searchPlaceholder="Search by name, slug, domain, email..."
        emptyMessage="No colleges found matching the selected filter."
      />

      {/* Create College Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-lg bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl relative">
            <button
              onClick={() => setIsCreateOpen(false)}
              className="absolute top-4 right-4 text-[#71717A] hover:text-[#F5F5F5]"
            >
              <X className="h-4 w-4" />
            </button>

            <h3 className="text-base font-bold text-[#F5F5F5] mb-1">
              Onboard New College Tenant
            </h3>
            <p className="text-xs text-[#A1A1AA] mb-4">
              Directly provisions an institutional workspace as Super Administrator.
            </p>

            {formError && (
              <div className="mb-4 p-3 rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/30 text-xs text-[#EF4444]">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  College Institutional Name *
                </label>
                <input
                  type="text"
                  required
                  value={createForm.name}
                  onChange={(e) => {
                    const name = e.target.value;
                    const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
                    setCreateForm({ ...createForm, name, slug });
                  }}
                  placeholder="e.g. Ahmedabad Institute of Technology"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Unique Slug *
                  </label>
                  <input
                    type="text"
                    required
                    value={createForm.slug}
                    onChange={(e) => setCreateForm({ ...createForm, slug: e.target.value })}
                    placeholder="ait-college"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] font-mono focus:outline-none focus:border-[#6366F1]"
                  />
                </div>
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Official Domain *
                  </label>
                  <input
                    type="text"
                    required
                    value={createForm.official_domain}
                    onChange={(e) => setCreateForm({ ...createForm, official_domain: e.target.value })}
                    placeholder="aitindia.in"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] font-mono focus:outline-none focus:border-[#6366F1]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Contact Email *
                  </label>
                  <input
                    type="email"
                    required
                    value={createForm.contact_email}
                    onChange={(e) => setCreateForm({ ...createForm, contact_email: e.target.value })}
                    placeholder="contact@aitindia.in"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                  />
                </div>
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Contact Phone
                  </label>
                  <input
                    type="text"
                    value={createForm.contact_phone}
                    onChange={(e) => setCreateForm({ ...createForm, contact_phone: e.target.value })}
                    placeholder="+91 9876543210"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Logo URL (Optional)
                </label>
                <input
                  type="url"
                  value={createForm.logo_url}
                  onChange={(e) => setCreateForm({ ...createForm, logo_url: e.target.value })}
                  placeholder="https://..."
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                />
              </div>

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-[#2A2A30]">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 text-[#A1A1AA] hover:text-[#F5F5F5] bg-[#1F1F23] rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-[#6366F1] hover:bg-[#4F46E5] text-white rounded-lg transition font-medium"
                >
                  {isSubmitting ? "Provisioning..." : "Provision College"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={isConfirmOpen}
        title={
          confirmAction === "APPROVE"
            ? `Approve College: ${selectedCollege?.name}`
            : confirmAction === "REJECT"
            ? `Reject College: ${selectedCollege?.name}`
            : `${selectedCollege?.is_active ? "Suspend" : "Activate"} College: ${selectedCollege?.name}`
        }
        description={
          confirmAction === "APPROVE"
            ? "Approving this college will allow students to select it in the public chatbot and grant its admins full operational rights."
            : confirmAction === "REJECT"
            ? "Rejecting this college will mark its onboarding as rejected and prevent it from going live."
            : selectedCollege?.is_active
            ? "Suspending this college will temporarily pause student chat queries and crawler jobs for this tenant."
            : "Activating this college will resume all chatbot and ingestion capabilities for this tenant."
        }
        confirmLabel={
          confirmAction === "APPROVE"
            ? "Approve Tenant"
            : confirmAction === "REJECT"
            ? "Reject Tenant"
            : selectedCollege?.is_active
            ? "Suspend College"
            : "Activate College"
        }
        isDestructive={confirmAction === "REJECT" || (confirmAction === "TOGGLE_ACTIVE" && selectedCollege?.is_active === true)}
        isLoading={isActionLoading}
        onConfirm={handleExecuteAction}
        onCancel={() => {
          setIsConfirmOpen(false);
          setSelectedCollege(null);
        }}
      />
    </div>
  );
}
