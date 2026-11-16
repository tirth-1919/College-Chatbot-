"use client";

import React, { useEffect, useState } from "react";
import { superAdminService } from "@/services/super-admin-service";
import { CollegeAdminItem, College, PlatformUser } from "@/types/admin";
import { DataTable, Column } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import {
  ShieldCheck,
  UserPlus,
  RefreshCw,
  Building2,
  Mail,
  Shield,
  X,
  Send,
  Trash2,
  Clock,
  CheckCircle,
} from "lucide-react";

interface PendingInvitation {
  id: string;
  college_id: string;
  college_name?: string;
  email: string;
  full_name: string;
  role_in_college: string;
  status: string;
  expires_at: string;
  created_at: string;
}

export default function CollegeAdminsPage() {
  const [admins, setAdmins] = useState<CollegeAdminItem[]>([]);
  const [colleges, setColleges] = useState<College[]>([]);
  const [users, setUsers] = useState<PlatformUser[]>([]);
  const [invitations, setInvitations] = useState<PendingInvitation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [dataError, setDataError] = useState<string | null>(null);
  const [dataNotice, setDataNotice] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"ACTIVE" | "INVITATIONS">("ACTIVE");

  // Assign modal state
  const [isAssignOpen, setIsAssignOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [selectedCollegeId, setSelectedCollegeId] = useState("");
  const [roleInCollege, setRoleInCollege] = useState("ADMIN");
  const [isPrimary, setIsPrimary] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Invite modal state
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteFullName, setInviteFullName] = useState("");
  const [inviteCollegeId, setInviteCollegeId] = useState("");
  const [inviteRole, setInviteRole] = useState("ADMIN");
  const [inviteSuccess, setInviteSuccess] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setDataError(null);
    setDataNotice(null);
    try {
      const [adminsRes, collegesRes, usersRes] = await Promise.all([
        superAdminService.getCollegeAdmins(),
        superAdminService.getColleges(true),
        superAdminService.getUsers(100),
      ]);

      const initialErrors = [
        !adminsRes.success ? adminsRes.error || "Unable to load administrators." : null,
        !usersRes.success ? usersRes.error || "Unable to load users." : null,
      ].filter((error): error is string => Boolean(error));
      if (initialErrors.length) setDataError(initialErrors.join(" "));

      setAdmins(adminsRes.success && adminsRes.data ? adminsRes.data : []);
      setColleges(collegesRes.success && collegesRes.data ? collegesRes.data : []);
      setUsers(usersRes.success && usersRes.data ? usersRes.data : []);
      if (!collegesRes.success || !collegesRes.data) {
        setDataError(
          [collegesRes.error || "Unable to load colleges.", ...initialErrors].join(" ")
        );
        setInvitations([]);
        return;
      }

      const invitationResults = await Promise.all(
        collegesRes.data.map((college) =>
          superAdminService.getCollegeAdminsAndInvitations(college.id)
        )
      );
      const failedResult = invitationResults.find((result) => !result.success);
      if (failedResult) {
        setDataError(failedResult.error || "Unable to load administrator invitations.");
      }
      setInvitations(
        invitationResults.flatMap((result) =>
          result.success ? result.data?.pending_invitations || [] : []
        )
      );
    } catch (err) {
      setDataError(err instanceof Error ? err.message : "Failed to fetch admin data.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId || !selectedCollegeId) {
      setFormError("Please select both a user and a college.");
      return;
    }

    setFormError(null);
    setIsSubmitting(true);

    try {
      const res = await superAdminService.assignCollegeAdmin({
        user_id: selectedUserId,
        college_id: selectedCollegeId,
        role_in_college: roleInCollege,
        is_primary: isPrimary,
      });

      if (res.success) {
        setIsAssignOpen(false);
        setSelectedUserId("");
        setSelectedCollegeId("");
        fetchData();
      } else {
        setFormError(res.error || "Failed to assign college admin.");
      }
    } catch (err: any) {
      setFormError(err.message || "An unexpected error occurred.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail || !inviteFullName || !inviteCollegeId) {
      setFormError("Please fill out all required fields.");
      return;
    }

    setFormError(null);
    setIsSubmitting(true);

    const targetCol = colleges.find((c) => c.id === inviteCollegeId);
    const collegeName = targetCol?.name || "College Institution";

    try {
      const res = await superAdminService.inviteCollegeAdmin(inviteCollegeId, {
        email: inviteEmail.trim().toLowerCase(),
        full_name: inviteFullName.trim(),
        role_in_college: inviteRole,
      });

      if (!res.success || !res.data) {
        setFormError(res.error || "Failed to dispatch invitation.");
        return;
      }

      const newInvite: PendingInvitation = {
        ...res.data,
        college_name: res.data.college_name || collegeName,
      };
      setInvitations((previous) => [newInvite, ...previous]);

      setInviteSuccess(
        res.message || `Invitation created for ${inviteEmail}. Check delivery status.`
      );
      setTimeout(() => {
        setIsInviteOpen(false);
        setInviteEmail("");
        setInviteFullName("");
        setInviteCollegeId("");
        setInviteSuccess(null);
      }, 1500);
    } catch (err: any) {
      setFormError(err.message || "Failed to dispatch invitation.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevokeInvitation = async (invId: string) => {
    const invite = invitations.find((item) => item.id === invId);
    if (!invite) {
      setDataError("The invitation is no longer available. Refresh the list and try again.");
      return;
    }
    try {
      const result = await superAdminService.revokeAdminInvitation(invite.college_id, invId);
      if (!result.success) {
        setDataError(result.error || "Unable to revoke invitation.");
        return;
      }
      setInvitations((previous) => previous.filter((item) => item.id !== invId));
      setDataError(null);
      setDataNotice(`Invitation for ${invite.email} was revoked.`);
    } catch (error) {
      setDataError(error instanceof Error ? error.message : "Unable to revoke invitation.");
    }
  };

  const handleResendInvitation = async (invId: string) => {
    const invite = invitations.find((item) => item.id === invId);
    if (!invite) {
      setDataError("The invitation is no longer available. Refresh the list and try again.");
      return;
    }
    try {
      const result = await superAdminService.resendAdminInvitation(invite.college_id, invId);
      if (!result.success || !result.data) {
        setDataError(result.error || "Unable to resend invitation.");
        return;
      }
      setInvitations((previous) =>
        previous.map((item) =>
          item.id === invId
            ? {
                ...item,
                ...result.data,
                college_name: result.data.college_name || item.college_name,
              }
            : item
        )
      );
      setDataError(null);
      setDataNotice(
        result.message || `Invitation token rotated for ${invite.email}. Check delivery status.`
      );
    } catch (error) {
      setDataError(error instanceof Error ? error.message : "Unable to resend invitation.");
    }
  };

  const columns: Column<CollegeAdminItem>[] = [
    {
      header: "Administrator",
      cell: (item) => (
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-[#6366F1]/10 border border-[#6366F1]/20 flex items-center justify-center text-xs font-bold text-[#6366F1]">
            {item.user_name.substring(0, 1).toUpperCase()}
          </div>
          <div>
            <span className="font-semibold text-[#F5F5F5] block text-xs">
              {item.user_name}
            </span>
            <span className="text-[11px] text-[#A1A1AA] font-mono flex items-center gap-1">
              <Mail className="h-3 w-3" />
              {item.user_email}
            </span>
          </div>
        </div>
      ),
    },
    {
      header: "Assigned College Institution",
      cell: (item: CollegeAdminItem) => (
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-[#A1A1AA]" />
          <div>
            <span className="text-xs font-medium text-[#F5F5F5] block">
              {item.college_name}
            </span>
            <span className="text-[10px] text-[#71717A] font-mono">
              Domain: {item.college_domain || "Verified"}
            </span>
          </div>
        </div>
      ),
    },
    {
      header: "Institutional Role",
      cell: (item) => (
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-[#1F1F23] text-[#818CF8] border border-[#2A2A30]">
            {item.role_in_college}
          </span>
          {item.is_primary && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20 font-medium">
              Primary Admin
            </span>
          )}
        </div>
      ),
    },
    {
      header: "Assigned Date",
      cell: (item) => (
        <span className="text-xs text-[#A1A1AA]">
          {new Date(item.created_at).toLocaleDateString()}
        </span>
      ),
    },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-[#6366F1]" />
            College Administrator Management
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Grant institutional authority, invite new college administrators, and enforce tenant boundary security.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <button
            onClick={() => {
              setFormError(null);
              setIsInviteOpen(true);
            }}
            className="px-3.5 py-2 rounded-lg bg-[#6366F1] hover:bg-[#4F46E5] text-white text-xs font-medium transition flex items-center gap-1.5 shadow-md shadow-[#6366F1]/20"
          >
            <Send className="h-4 w-4" />
            <span>Invite Administrator</span>
          </button>

          <button
            onClick={() => {
              setFormError(null);
              setIsAssignOpen(true);
            }}
            className="px-3 py-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] text-xs font-medium transition flex items-center gap-1.5"
          >
            <UserPlus className="h-4 w-4" />
            <span>Assign Existing</span>
          </button>

          <button
            onClick={fetchData}
            className="p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {dataError && (
        <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs text-red-300">
          {dataError}
        </div>
      )}
      {dataNotice && (
        <div role="status" className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-xs text-emerald-300">
          {dataNotice}
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-[#2A2A30] pb-2 text-xs">
        <button
          onClick={() => setActiveTab("ACTIVE")}
          className={`px-3.5 py-1.5 rounded-lg font-medium transition ${
            activeTab === "ACTIVE"
              ? "bg-[#6366F1] text-white"
              : "bg-[#18181B] text-[#A1A1AA] hover:text-[#F5F5F5]"
          }`}
        >
          Active Administrators ({admins.length})
        </button>
        <button
          onClick={() => setActiveTab("INVITATIONS")}
          className={`px-3.5 py-1.5 rounded-lg font-medium transition ${
            activeTab === "INVITATIONS"
              ? "bg-[#6366F1] text-white"
              : "bg-[#18181B] text-[#A1A1AA] hover:text-[#F5F5F5]"
          }`}
        >
          Pending Invitations ({invitations.length})
        </button>
      </div>

      {/* Tab 1: Active Admins Table */}
      {activeTab === "ACTIVE" && (
        isLoading ? (
          <div className="flex items-center justify-center py-20 text-xs text-[#A1A1AA]">
            <div className="w-5 h-5 border-2 border-[#6366F1] border-t-transparent rounded-full animate-spin mr-2" />
            <span>Loading college administrators...</span>
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={admins}
            searchPlaceholder="Search administrators or colleges..."
            emptyMessage="No administrators assigned to colleges yet."
          />
        )
      )}

      {/* Tab 2: Pending Invitations List */}
      {activeTab === "INVITATIONS" && (
        <div className="space-y-3">
          {invitations.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {invitations.map((inv) => (
                <div
                  key={inv.id}
                  className="p-5 rounded-xl border border-[#2A2A30] bg-[#111114] space-y-3 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="text-sm font-semibold text-[#F5F5F5]">{inv.full_name}</h4>
                        <div className="text-xs text-[#818CF8] font-mono mt-0.5">{inv.email}</div>
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/30 font-medium">
                        Pending Invitation
                      </span>
                    </div>

                    <div className="py-2.5 my-2 border-y border-[#1F1F23] text-xs text-[#A1A1AA] space-y-1">
                      <div className="flex items-center gap-2">
                        <Building2 className="h-3.5 w-3.5 text-[#71717A]" />
                        <span>College: </span>
                        <span className="text-[#F5F5F5] font-medium">{inv.college_name || "Institution"}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Clock className="h-3.5 w-3.5 text-[#71717A]" />
                        <span>Expires: </span>
                        <span>{new Date(inv.expires_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-1 border-t border-[#1F1F23]">
                    <button
                      onClick={() => handleResendInvitation(inv.id)}
                      className="px-2.5 py-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-[#A1A1AA] hover:text-[#F5F5F5] text-xs transition flex items-center gap-1"
                    >
                      <RefreshCw className="h-3.5 w-3.5" />
                      <span>Resend</span>
                    </button>
                    <button
                      onClick={() => handleRevokeInvitation(inv.id)}
                      className="px-2.5 py-1.5 rounded-lg border border-[#EF4444]/30 bg-[#EF4444]/10 hover:bg-[#EF4444]/20 text-[#EF4444] text-xs transition flex items-center gap-1"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      <span>Revoke</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-12 text-center rounded-xl border border-[#2A2A30] bg-[#111114]">
              <div className="h-10 w-10 rounded-full bg-[#10B981]/10 text-[#10B981] flex items-center justify-center mx-auto mb-2">
                <CheckCircle className="h-5 w-5" />
              </div>
              <h3 className="text-xs font-semibold text-[#F5F5F5]">No Pending Invitations</h3>
              <p className="text-[11px] text-[#A1A1AA] mt-1">All administrator invitations have been accepted or processed.</p>
            </div>
          )}
        </div>
      )}

      {/* Invite Administrator Dialog */}
      {isInviteOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl relative space-y-4">
            <button
              onClick={() => setIsInviteOpen(false)}
              className="absolute top-4 right-4 text-[#71717A] hover:text-[#F5F5F5]"
            >
              <X className="h-4 w-4" />
            </button>

            <h3 className="text-base font-bold text-[#F5F5F5]">
              Invite Institutional Administrator
            </h3>
            <p className="text-xs text-[#A1A1AA]">
              Sends a cryptographic 7-day invitation link to allow the designated person to create administrator credentials.
            </p>

            {formError && (
              <div className="p-3 rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/30 text-xs text-[#EF4444]">
                {formError}
              </div>
            )}
            {inviteSuccess && (
              <div className="p-3 rounded-lg bg-[#10B981]/10 border border-[#10B981]/30 text-xs text-[#10B981]">
                {inviteSuccess}
              </div>
            )}

            <form onSubmit={handleInvite} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">Target College Institution *</label>
                <select
                  required
                  value={inviteCollegeId}
                  onChange={(e) => setInviteCollegeId(e.target.value)}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                >
                  <option value="">-- Choose Institution --</option>
                  {colleges.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.official_domain})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">Administrator Full Name *</label>
                <input
                  type="text"
                  required
                  value={inviteFullName}
                  onChange={(e) => setInviteFullName(e.target.value)}
                  placeholder="e.g. Dr. R. K. Patel"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                />
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">Institutional Email Address *</label>
                <input
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="e.g. admin@aitindia.in"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                />
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">Permission Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                >
                  <option value="ADMIN">ADMIN (Full Crawl, OCR, &amp; Verification)</option>
                  <option value="EDITOR">EDITOR (Draft &amp; Fact Review Only)</option>
                  <option value="VIEWER">VIEWER (Read-Only Analytics)</option>
                </select>
              </div>

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-[#2A2A30]">
                <button
                  type="button"
                  onClick={() => setIsInviteOpen(false)}
                  className="px-4 py-2 text-[#A1A1AA] hover:text-[#F5F5F5] bg-[#1F1F23] rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-[#6366F1] hover:bg-[#4F46E5] text-white rounded-lg transition font-medium flex items-center gap-1.5"
                >
                  <Send className="h-3.5 w-3.5" />
                  <span>{isSubmitting ? "Dispatching..." : "Send Invitation"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Assign Existing Admin Dialog */}
      {isAssignOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl relative">
            <button
              onClick={() => setIsAssignOpen(false)}
              className="absolute top-4 right-4 text-[#71717A] hover:text-[#F5F5F5]"
            >
              <X className="h-4 w-4" />
            </button>

            <h3 className="text-base font-bold text-[#F5F5F5] mb-1">
              Assign College Administrator
            </h3>
            <p className="text-xs text-[#A1A1AA] mb-4">
              Grants college administrative authority within the designated tenant boundary.
            </p>

            {formError && (
              <div className="mb-4 p-3 rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/30 text-xs text-[#EF4444]">
                {formError}
              </div>
            )}

            <form onSubmit={handleAssign} className="space-y-4 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1.5">
                  Select User Account *
                </label>
                <select
                  required
                  value={selectedUserId}
                  onChange={(e) => setSelectedUserId(e.target.value)}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                >
                  <option value="">-- Choose User --</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.full_name} ({u.email}) [{u.role}]
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1.5">
                  Target College Tenant *
                </label>
                <select
                  required
                  value={selectedCollegeId}
                  onChange={(e) => setSelectedCollegeId(e.target.value)}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                >
                  <option value="">-- Choose College --</option>
                  {colleges.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.official_domain})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1.5">
                  Role Title in College
                </label>
                <input
                  type="text"
                  value={roleInCollege}
                  onChange={(e) => setRoleInCollege(e.target.value)}
                  placeholder="e.g. ADMIN, DEAN, HOD"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="primaryCheck"
                  checked={isPrimary}
                  onChange={(e) => setIsPrimary(e.target.checked)}
                  className="rounded border-[#2A2A30] text-[#6366F1] focus:ring-0 bg-[#1F1F23]"
                />
                <label htmlFor="primaryCheck" className="text-xs text-[#D4D4D8] cursor-pointer">
                  Set as primary institutional administrator
                </label>
              </div>

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-[#2A2A30]">
                <button
                  type="button"
                  onClick={() => setIsAssignOpen(false)}
                  className="px-4 py-2 text-[#A1A1AA] hover:text-[#F5F5F5] bg-[#1F1F23] rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-[#6366F1] hover:bg-[#4F46E5] text-white rounded-lg transition font-medium"
                >
                  {isSubmitting ? "Assigning..." : "Assign Privileges"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
