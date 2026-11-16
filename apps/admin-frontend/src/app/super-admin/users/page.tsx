"use client";

import React, { useEffect, useState } from "react";
import { superAdminService } from "@/services/super-admin-service";
import { PlatformUser, UserRole } from "@/types/admin";
import { DataTable, Column } from "@/components/DataTable";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import {
  Users,
  Shield,
  GraduationCap,
  CheckCircle,
  XCircle,
  RefreshCw,
  Power,
  Edit,
  X,
} from "lucide-react";

export default function UsersManagementPage() {
  const [users, setUsers] = useState<PlatformUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [roleFilter, setRoleFilter] = useState<string>("ALL");

  // Edit user modal
  const [editingUser, setEditingUser] = useState<PlatformUser | null>(null);
  const [editRole, setEditRole] = useState<UserRole>("STUDENT");
  const [editName, setEditName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Status toggle confirmation
  const [confirmUser, setConfirmUser] = useState<PlatformUser | null>(null);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState(false);

  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      const res = await superAdminService.getUsers(200);
      if (res.success && res.data) {
        setUsers(res.data);
      }
    } catch (err) {
      console.error("Failed to load user directory:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    setIsSubmitting(true);

    try {
      await superAdminService.updateUser(editingUser.id, {
        full_name: editName,
        role: editRole,
      });
      setEditingUser(null);
      fetchUsers();
    } catch (err) {
      console.error("Failed to update user:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async () => {
    if (!confirmUser) return;
    setIsActionLoading(true);

    try {
      await superAdminService.updateUser(confirmUser.id, {
        is_active: !confirmUser.is_active,
      });
      setIsConfirmOpen(false);
      setConfirmUser(null);
      fetchUsers();
    } catch (err) {
      console.error("Failed to toggle user status:", err);
    } finally {
      setIsActionLoading(false);
    }
  };

  const filteredUsers = users.filter((u) => {
    if (roleFilter === "ALL") return true;
    return u.role === roleFilter;
  });

  const getRoleBadge = (role: UserRole) => {
    if (role === "SUPER_ADMIN") {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-[#6366F1]/10 text-[#6366F1] border border-[#6366F1]/30 font-semibold font-mono">
          <Shield className="h-3 w-3" />
          SUPER_ADMIN
        </span>
      );
    }
    if (role === "COLLEGE_ADMIN") {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/30 font-semibold font-mono">
          <Shield className="h-3 w-3" />
          COLLEGE_ADMIN
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-[#3B82F6]/10 text-[#3B82F6] border border-[#3B82F6]/30 font-medium font-mono">
        <GraduationCap className="h-3 w-3" />
        STUDENT
      </span>
    );
  };

  const columns: Column<PlatformUser>[] = [
    {
      header: "User Account",
      cell: (item) => (
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-[#1F1F23] border border-[#2A2A30] flex items-center justify-center text-xs font-bold text-[#F5F5F5]">
            {item.full_name ? item.full_name[0].toUpperCase() : "U"}
          </div>
          <div>
            <span className="font-semibold text-[#F5F5F5] block text-xs">
              {item.full_name}
            </span>
            <span className="text-[11px] text-[#71717A] font-mono">
              {item.email}
            </span>
          </div>
        </div>
      ),
    },
    {
      header: "Platform Role",
      cell: (item) => getRoleBadge(item.role),
    },
    {
      header: "Verification",
      cell: (item) => (
        <span
          className={`inline-flex items-center gap-1 text-[11px] font-medium ${
            item.is_verified ? "text-[#10B981]" : "text-[#71717A]"
          }`}
        >
          {item.is_verified ? (
            <CheckCircle className="h-3.5 w-3.5" />
          ) : (
            <XCircle className="h-3.5 w-3.5" />
          )}
          {item.is_verified ? "Verified" : "Unverified"}
        </span>
      ),
    },
    {
      header: "Account State",
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
      header: "Registered",
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
          <button
            onClick={() => {
              setEditingUser(item);
              setEditName(item.full_name);
              setEditRole(item.role);
            }}
            className="p-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
            title="Edit User"
          >
            <Edit className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => {
              setConfirmUser(item);
              setIsConfirmOpen(true);
            }}
            className={`p-1.5 rounded-lg border transition ${
              item.is_active
                ? "bg-[#1F1F23] border-[#2A2A30] text-[#A1A1AA] hover:text-[#EF4444] hover:border-[#EF4444]/30"
                : "bg-[#10B981]/10 border-[#10B981]/30 text-[#10B981] hover:bg-[#10B981]/20"
            }`}
            title={item.is_active ? "Suspend Account" : "Activate Account"}
          >
            <Power className="h-3.5 w-3.5" />
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
            <Users className="h-5 w-5 text-[#6366F1]" />
            Platform User Directory
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Global view of all student, college administrative, and platform super administrator accounts.
          </p>
        </div>

        <button
          onClick={fetchUsers}
          className="self-start sm:self-auto p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
          title="Refresh directory"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {/* Role Filters */}
      <div className="flex items-center gap-2 border-b border-[#2A2A30] pb-3 text-xs">
        {["ALL", "STUDENT", "COLLEGE_ADMIN", "SUPER_ADMIN"].map((r) => (
          <button
            key={r}
            onClick={() => setRoleFilter(r)}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              roleFilter === r
                ? "bg-[#6366F1] text-white"
                : "bg-[#18181B] text-[#A1A1AA] hover:text-[#F5F5F5]"
            }`}
          >
            {r} ({r === "ALL" ? users.length : users.filter((u) => u.role === r).length})
          </button>
        ))}
      </div>

      {/* Users Table */}
      <DataTable
        data={filteredUsers}
        columns={columns}
        searchPlaceholder="Search by name, email, or role..."
        emptyMessage="No users found in directory matching criteria."
      />

      {/* Edit User Modal */}
      {editingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl relative">
            <button
              onClick={() => setEditingUser(null)}
              className="absolute top-4 right-4 text-[#71717A] hover:text-[#F5F5F5]"
            >
              <X className="h-4 w-4" />
            </button>

            <h3 className="text-base font-bold text-[#F5F5F5] mb-1">
              Edit User Account
            </h3>
            <p className="text-xs text-[#A1A1AA] mb-4">
              Modify account attributes and platform authorization role.
            </p>

            <form onSubmit={handleEditSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                />
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  disabled
                  value={editingUser.email}
                  className="w-full bg-[#18181B] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#71717A] font-mono cursor-not-allowed"
                />
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Platform Authority Role *
                </label>
                <select
                  value={editRole}
                  onChange={(e) => setEditRole(e.target.value as UserRole)}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                >
                  <option value="STUDENT">STUDENT (Public Student Inquiries)</option>
                  <option value="COLLEGE_ADMIN">COLLEGE_ADMIN (College Management)</option>
                  <option value="SUPER_ADMIN">SUPER_ADMIN (Global Platform Governance)</option>
                </select>
              </div>

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-[#2A2A30]">
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="px-4 py-2 text-[#A1A1AA] hover:text-[#F5F5F5] bg-[#1F1F23] rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-[#6366F1] hover:bg-[#4F46E5] text-white rounded-lg transition font-medium"
                >
                  {isSubmitting ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Status Toggle Confirmation */}
      <ConfirmationDialog
        isOpen={isConfirmOpen}
        title={`${confirmUser?.is_active ? "Suspend" : "Activate"} User: ${confirmUser?.full_name}`}
        description={
          confirmUser?.is_active
            ? "Suspending this account will immediately revoke all JWT sessions and prevent sign in across user and admin portals."
            : "Activating this account will restore login and session privileges."
        }
        confirmLabel={confirmUser?.is_active ? "Suspend User" : "Activate User"}
        isDestructive={confirmUser?.is_active === true}
        isLoading={isActionLoading}
        onConfirm={handleToggleStatus}
        onCancel={() => {
          setIsConfirmOpen(false);
          setConfirmUser(null);
        }}
      />
    </div>
  );
}
