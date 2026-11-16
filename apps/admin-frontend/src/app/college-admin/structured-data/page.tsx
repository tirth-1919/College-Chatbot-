"use client";

import React, { useEffect, useState } from "react";
import { collegeAdminService } from "@/services/college-admin-service";
import { ExtractedFact } from "@/types/college-admin";
import { DataTable, Column } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import {
  Layers,
  Plus,
  RefreshCw,
  Edit,
  Trash2,
  X,
  BookOpen,
  GraduationCap,
  Building,
  Sparkles,
  HelpCircle,
} from "lucide-react";

const CATEGORIES = [
  "ALL",
  "ABOUT",
  "COURSES",
  "ADMISSIONS",
  "DEPARTMENTS",
  "FACILITIES",
  "FAQS",
];

export default function StructuredCollegeDataPage() {
  const [facts, setFacts] = useState<ExtractedFact[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState("ALL");

  // Create modal
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    category: "ABOUT",
    fact_key: "",
    fact_value: "",
  });
  const [isSubmittingCreate, setIsSubmittingCreate] = useState(false);

  // Edit modal
  const [editingFact, setEditingFact] = useState<ExtractedFact | null>(null);
  const [editForm, setEditForm] = useState({
    category: "ABOUT",
    fact_key: "",
    fact_value: "",
  });
  const [isSubmittingEdit, setIsSubmittingEdit] = useState(false);

  // Delete modal
  const [deletingFact, setDeletingFact] = useState<ExtractedFact | null>(null);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchFacts = async () => {
    setIsLoading(true);
    try {
      const res = await collegeAdminService.getStructuredFacts(
        selectedCategory === "ALL" ? undefined : selectedCategory
      );
      if (res.success && res.data) {
        setFacts(res.data);
      }
    } catch (err) {
      console.error("Failed to load structured facts:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFacts();
  }, [selectedCategory]);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingCreate(true);
    try {
      const res = await collegeAdminService.createStructuredFact(createForm);
      if (res.success) {
        setIsCreateOpen(false);
        setCreateForm({ category: "ABOUT", fact_key: "", fact_value: "" });
        fetchFacts();
      }
    } catch (err) {
      console.error("Failed to create structured fact:", err);
    } finally {
      setIsSubmittingCreate(false);
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingFact) return;
    setIsSubmittingEdit(true);
    try {
      const res = await collegeAdminService.updateStructuredFact(editingFact.id, editForm);
      if (res.success) {
        setEditingFact(null);
        fetchFacts();
      }
    } catch (err) {
      console.error("Failed to update structured fact:", err);
    } finally {
      setIsSubmittingEdit(false);
    }
  };

  const handleDelete = async () => {
    if (!deletingFact) return;
    setIsDeleting(true);
    try {
      await collegeAdminService.deleteStructuredFact(deletingFact.id);
      setIsDeleteOpen(false);
      setDeletingFact(null);
      fetchFacts();
    } catch (err) {
      console.error("Failed to delete structured fact:", err);
    } finally {
      setIsDeleting(false);
    }
  };

  const columns: Column<ExtractedFact>[] = [
    {
      header: "Category & Topic",
      cell: (item) => (
        <div>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-[#1F1F23] text-[#10B981] border border-[#10B981]/20 font-bold uppercase block w-fit mb-1">
            {item.category}
          </span>
          <span className="font-semibold text-xs text-[#F5F5F5] block">
            {item.fact_key}
          </span>
        </div>
      ),
    },
    {
      header: "Factual Information",
      cell: (item) => (
        <div className="max-w-md sm:max-w-xl py-1">
          <p className="text-xs text-[#D4D4D8] leading-relaxed line-clamp-2">
            {item.fact_value}
          </p>
        </div>
      ),
    },
    {
      header: "Verification",
      cell: (item) => <StatusBadge status={item.verification_status} />,
    },
    {
      header: "Actions",
      className: "text-right",
      cell: (item) => (
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={() => {
              setEditingFact(item);
              setEditForm({
                category: item.category,
                fact_key: item.fact_key,
                fact_value: item.fact_value,
              });
            }}
            className="p-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
            title="Edit Fact"
          >
            <Edit className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => {
              setDeletingFact(item);
              setIsDeleteOpen(true);
            }}
            className="p-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] text-[#A1A1AA] hover:text-[#EF4444] transition"
            title="Delete Fact"
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
            <Layers className="h-5 w-5 text-[#10B981]" />
            Structured College Information Manager
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Curate atomic institutional facts for admissions, fee tables, branches, departments, campus facilities, and official FAQs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchFacts}
            className="p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
            title="Refresh facts"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[#10B981] hover:bg-[#059669] text-white text-xs font-medium transition shadow-md shadow-[#10B981]/20"
          >
            <Plus className="h-4 w-4" />
            <span>Add Structured Fact</span>
          </button>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex items-center gap-2 border-b border-[#2A2A30] pb-3 text-xs overflow-x-auto">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-3.5 py-1.5 rounded-lg font-medium whitespace-nowrap transition ${
              selectedCategory === cat
                ? "bg-[#10B981] text-white"
                : "bg-[#18181B] text-[#A1A1AA] hover:text-[#F5F5F5]"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Data Table */}
      <DataTable
        data={facts}
        columns={columns}
        searchPlaceholder="Search structured facts by key or content..."
        emptyMessage="No structured facts found in this category."
      />

      {/* Create Modal */}
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
              Add Verified College Fact
            </h3>
            <p className="text-xs text-[#A1A1AA] mb-4">
              Directly curated facts carry Tier 2 ADMIN_VERIFIED grounding in student responses.
            </p>

            <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Information Category *
                </label>
                <select
                  value={createForm.category}
                  onChange={(e) => setCreateForm({ ...createForm, category: e.target.value })}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                >
                  <option value="ABOUT">About College (History, Accreditations)</option>
                  <option value="COURSES">Academic Courses & Programs</option>
                  <option value="ADMISSIONS">Admissions (Criteria, Cutoffs, Quotas)</option>
                  <option value="DEPARTMENTS">Departments & Faculty Leaders</option>
                  <option value="FACILITIES">Campus Facilities (Hostel, Library, Sports)</option>
                  <option value="FAQS">Frequently Asked Questions</option>
                </select>
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Topic / Fact Key *
                </label>
                <input
                  type="text"
                  required
                  value={createForm.fact_key}
                  onChange={(e) => setCreateForm({ ...createForm, fact_key: e.target.value })}
                  placeholder="e.g. Computer Science Annual Tuition Fee"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                />
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Factual Content *
                </label>
                <textarea
                  required
                  rows={4}
                  value={createForm.fact_value}
                  onChange={(e) => setCreateForm({ ...createForm, fact_value: e.target.value })}
                  placeholder="e.g. ₹78,000 per academic year, payable in two equal semester installments."
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg p-2.5 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
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
                  disabled={isSubmittingCreate}
                  className="px-4 py-2 bg-[#10B981] hover:bg-[#059669] text-white rounded-lg transition font-medium"
                >
                  {isSubmittingCreate ? "Saving..." : "Add Fact"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editingFact && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-lg bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl relative">
            <button
              onClick={() => setEditingFact(null)}
              className="absolute top-4 right-4 text-[#71717A] hover:text-[#F5F5F5]"
            >
              <X className="h-4 w-4" />
            </button>

            <h3 className="text-base font-bold text-[#F5F5F5] mb-1">
              Edit Structured Fact
            </h3>
            <p className="text-xs text-[#A1A1AA] mb-4">
              Update institutional parameters or update wording.
            </p>

            <form onSubmit={handleEditSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Information Category
                </label>
                <select
                  value={editForm.category}
                  onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                >
                  <option value="ABOUT">About College</option>
                  <option value="COURSES">Academic Courses</option>
                  <option value="ADMISSIONS">Admissions</option>
                  <option value="DEPARTMENTS">Departments</option>
                  <option value="FACILITIES">Campus Facilities</option>
                  <option value="FAQS">FAQs</option>
                </select>
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Topic / Fact Key
                </label>
                <input
                  type="text"
                  required
                  value={editForm.fact_key}
                  onChange={(e) => setEditForm({ ...editForm, fact_key: e.target.value })}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                />
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Factual Content
                </label>
                <textarea
                  required
                  rows={4}
                  value={editForm.fact_value}
                  onChange={(e) => setEditForm({ ...editForm, fact_value: e.target.value })}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg p-2.5 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                />
              </div>

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-[#2A2A30]">
                <button
                  type="button"
                  onClick={() => setEditingFact(null)}
                  className="px-4 py-2 text-[#A1A1AA] hover:text-[#F5F5F5] bg-[#1F1F23] rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingEdit}
                  className="px-4 py-2 bg-[#10B981] hover:bg-[#059669] text-white rounded-lg transition font-medium"
                >
                  {isSubmittingEdit ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      <ConfirmationDialog
        isOpen={isDeleteOpen}
        title={`Delete Structured Fact: ${deletingFact?.fact_key}`}
        description="Removing this fact will delete it from structured college retrieval. This action cannot be undone."
        confirmLabel="Delete Fact"
        isDestructive={true}
        isLoading={isDeleting}
        onConfirm={handleDelete}
        onCancel={() => {
          setIsDeleteOpen(false);
          setDeletingFact(null);
        }}
      />
    </div>
  );
}

