"use client";

import React, { useEffect, useState } from "react";
import { superAdminService } from "@/services/super-admin-service";
import { SupportTicket, College } from "@/types/admin";
import { DataTable, Column } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import {
  LifeBuoy,
  RefreshCw,
  Building2,
  Mail,
  MessageSquare,
  Edit,
  X,
  CheckCircle,
} from "lucide-react";

export default function SupportTicketsPage() {
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [colleges, setColleges] = useState<College[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [collegeFilter, setCollegeFilter] = useState("");

  // Update status modal
  const [selectedTicket, setSelectedTicket] = useState<SupportTicket | null>(null);
  const [newStatus, setNewStatus] = useState("IN_PROGRESS");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchTickets = async () => {
    setIsLoading(true);
    try {
      const [ticketsRes, collegesRes] = await Promise.all([
        superAdminService.getSupportTickets({
          status: statusFilter === "ALL" ? undefined : statusFilter,
          college_id: collegeFilter || undefined,
        }),
        superAdminService.getColleges(true),
      ]);

      if (ticketsRes.success && ticketsRes.data) setTickets(ticketsRes.data);
      if (collegesRes.success && collegesRes.data) setColleges(collegesRes.data);
    } catch (err) {
      console.error("Failed to load support tickets:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, [statusFilter, collegeFilter]);

  const handleUpdateStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket) return;
    setIsSubmitting(true);

    try {
      await superAdminService.updateSupportTicketStatus(selectedTicket.id, newStatus);
      setSelectedTicket(null);
      fetchTickets();
    } catch (err) {
      console.error("Failed to update ticket status:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns: Column<SupportTicket>[] = [
    {
      header: "Student Inquirer",
      cell: (item) => (
        <div>
          <span className="font-semibold text-[#F5F5F5] block text-xs">
            {item.student_name}
          </span>
          <span className="text-[11px] text-[#71717A] font-mono">
            {item.student_email}
          </span>
        </div>
      ),
    },
    {
      header: "College Institution",
      cell: (item) => (
        <div className="flex items-center gap-1.5 text-xs text-[#D4D4D8]">
          <Building2 className="h-3.5 w-3.5 text-[#6366F1]" />
          <span>{item.college_name}</span>
        </div>
      ),
    },
    {
      header: "Inquiry Subject & Message",
      cell: (item) => (
        <div className="max-w-xs sm:max-w-md">
          <span className="font-medium text-[#F5F5F5] block text-xs truncate">
            {item.subject}
          </span>
          <span className="text-[11px] text-[#A1A1AA] line-clamp-1">
            {item.message}
          </span>
        </div>
      ),
    },
    {
      header: "Lifecycle Status",
      cell: (item) => <StatusBadge status={item.status} />,
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
      header: "Action",
      className: "text-right",
      cell: (item) => (
        <button
          onClick={() => {
            setSelectedTicket(item);
            setNewStatus(item.status);
          }}
          className="p-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
          title="Update ticket status"
        >
          <Edit className="h-3.5 w-3.5" />
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
            <LifeBuoy className="h-5 w-5 text-[#6366F1]" />
            Student Support & Escalated Inquiries
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Questions escalated from the AI Chatbot when official grounding documentation was unavailable.
          </p>
        </div>

        <button
          onClick={fetchTickets}
          className="self-start sm:self-auto p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
          title="Refresh tickets"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#2A2A30] pb-3 text-xs">
        <div className="flex items-center gap-2">
          {["ALL", "OPEN", "IN_PROGRESS", "WAITING_FOR_USER", "RESOLVED", "CLOSED"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg font-medium transition ${
                statusFilter === st
                  ? "bg-[#6366F1] text-white"
                  : "bg-[#18181B] text-[#A1A1AA] hover:text-[#F5F5F5]"
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        <div>
          <select
            value={collegeFilter}
            onChange={(e) => setCollegeFilter(e.target.value)}
            className="bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-1.5 text-xs text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
          >
            <option value="">All Colleges</option>
            {colleges.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Data Table */}
      <DataTable
        data={tickets}
        columns={columns}
        searchPlaceholder="Search by student name, email, or subject..."
        emptyMessage="No escalated support inquiries found."
      />

      {/* Status Update Modal */}
      {selectedTicket && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl relative">
            <button
              onClick={() => setSelectedTicket(null)}
              className="absolute top-4 right-4 text-[#71717A] hover:text-[#F5F5F5]"
            >
              <X className="h-4 w-4" />
            </button>

            <h3 className="text-base font-bold text-[#F5F5F5] mb-1">
              Update Ticket Lifecycle
            </h3>
            <p className="text-xs text-[#A1A1AA] mb-4">
              Student: <span className="text-[#F5F5F5] font-semibold">{selectedTicket.student_name}</span> ({selectedTicket.student_email})
            </p>

            <div className="mb-4 p-3 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-xs space-y-1">
              <span className="font-semibold text-[#F5F5F5] block">{selectedTicket.subject}</span>
              <p className="text-[#A1A1AA]">{selectedTicket.message}</p>
            </div>

            <form onSubmit={handleUpdateStatus} className="space-y-4 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1.5">
                  Resolution Status *
                </label>
                <select
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value)}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                >
                  <option value="OPEN">OPEN (Awaiting response)</option>
                  <option value="IN_PROGRESS">IN_PROGRESS (Staff reviewing)</option>
                  <option value="WAITING_FOR_USER">WAITING_FOR_USER (Student response needed)</option>
                  <option value="RESOLVED">RESOLVED (Response delivered to student)</option>
                  <option value="CLOSED">CLOSED (Archived inquiry)</option>
                </select>
              </div>

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-[#2A2A30]">
                <button
                  type="button"
                  onClick={() => setSelectedTicket(null)}
                  className="px-4 py-2 text-[#A1A1AA] hover:text-[#F5F5F5] bg-[#1F1F23] rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-[#6366F1] hover:bg-[#4F46E5] text-white rounded-lg transition font-medium"
                >
                  {isSubmitting ? "Updating..." : "Update Status"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

