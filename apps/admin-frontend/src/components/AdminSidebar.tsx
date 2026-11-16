"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAdminAuth } from "@/hooks/use-admin-auth";
import {
  LayoutDashboard,
  Building2,
  UserCheck,
  ShieldCheck,
  Users,
  Cpu,
  BarChart3,
  Activity,
  ShieldAlert,
  LifeBuoy,
  HeartPulse,
  Settings,
  ChevronLeft,
  ChevronRight,
  Shield,
  LogOut,
} from "lucide-react";

const NAV_ITEMS = [
  {
    category: "PLATFORM GOVERNANCE",
    items: [
      { name: "Overview", href: "/super-admin/dashboard", icon: LayoutDashboard },
      { name: "Colleges & Tenants", href: "/super-admin/colleges", icon: Building2 },
      { name: "Registration Queue", href: "/super-admin/registrations", icon: UserCheck },
      { name: "College Admins", href: "/super-admin/admins", icon: ShieldCheck },
      { name: "User Directory", href: "/super-admin/users", icon: Users },
    ],
  },
  {
    category: "AI & TELEMETRY",
    items: [
      { name: "AI Providers", href: "/super-admin/ai-providers", icon: Cpu },
      { name: "Usage & Analytics", href: "/super-admin/analytics", icon: BarChart3 },
      { name: "Ingestion & Jobs", href: "/super-admin/usage", icon: Activity },
    ],
  },
  {
    category: "SECURITY & OPERATIONS",
    items: [
      { name: "Security Audit", href: "/super-admin/audit-logs", icon: ShieldAlert },
      { name: "Support Tickets", href: "/super-admin/support", icon: LifeBuoy },
      { name: "System Health", href: "/super-admin/system-health", icon: HeartPulse },
      { name: "Global Settings", href: "/super-admin/settings", icon: Settings },
    ],
  },
];

export function AdminSidebar() {
  const pathname = usePathname();
  const { admin, logout } = useAdminAuth();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={`relative border-r border-[#2A2A30] bg-[#111114] flex flex-col justify-between transition-all duration-200 z-40 ${
        collapsed ? "w-16" : "w-64"
      }`}
    >
      {/* Top Header / Branding */}
      <div>
        <div className="h-16 px-4 border-b border-[#2A2A30] flex items-center justify-between">
          <Link href="/super-admin/dashboard" className="flex items-center gap-3 overflow-hidden">
            <div className="h-9 w-9 min-w-9 rounded-lg bg-[#6366F1] flex items-center justify-center text-white font-bold shadow-md shadow-[#6366F1]/20">
              <Shield className="h-5 w-5" />
            </div>
            {!collapsed && (
              <div>
                <span className="font-semibold text-sm text-[#F5F5F5] tracking-tight block leading-tight">
                  CampusAI <span className="text-[#6366F1]">SaaS</span>
                </span>
                <span className="text-[10px] text-[#A1A1AA] uppercase tracking-wider block">
                  Super Admin
                </span>
              </div>
            )}
          </Link>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 rounded-md text-[#71717A] hover:text-[#F5F5F5] hover:bg-[#1F1F23] transition"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>

        {/* Navigation list */}
        <div className="py-4 px-2 space-y-6 overflow-y-auto max-h-[calc(100vh-140px)]">
          {NAV_ITEMS.map((group, gIdx) => (
            <div key={gIdx} className="space-y-1">
              {!collapsed && (
                <div className="px-3 pb-1 text-[10px] font-semibold text-[#71717A] tracking-wider uppercase">
                  {group.category}
                </div>
              )}
              {group.items.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    title={collapsed ? item.name : undefined}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition ${
                      isActive
                        ? "bg-[#6366F1]/10 text-[#6366F1] border border-[#6366F1]/30 font-semibold"
                        : "text-[#A1A1AA] hover:text-[#F5F5F5] hover:bg-[#1F1F23]"
                    }`}
                  >
                    <Icon className={`h-4 w-4 min-w-4 ${isActive ? "text-[#6366F1]" : "text-[#71717A]"}`} />
                    {!collapsed && <span className="truncate">{item.name}</span>}
                  </Link>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Bottom Profile / Logout */}
      <div className="p-3 border-t border-[#2A2A30] bg-[#0E0E11]">
        <div className="flex items-center justify-between">
          {!collapsed ? (
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="h-8 w-8 min-w-8 rounded-full bg-[#1F1F23] border border-[#2A2A30] flex items-center justify-center text-xs font-bold text-[#6366F1]">
                {admin?.full_name ? admin.full_name[0].toUpperCase() : "A"}
              </div>
              <div className="overflow-hidden">
                <span className="text-xs font-semibold text-[#F5F5F5] truncate block leading-tight">
                  {admin?.full_name || "Super Admin"}
                </span>
                <span className="text-[10px] text-[#10B981] font-mono block">
                  SUPER_ADMIN
                </span>
              </div>
            </div>
          ) : (
            <div className="mx-auto h-8 w-8 rounded-full bg-[#1F1F23] border border-[#2A2A30] flex items-center justify-center text-xs font-bold text-[#6366F1]">
              {admin?.full_name ? admin.full_name[0].toUpperCase() : "A"}
            </div>
          )}

          {!collapsed && (
            <button
              onClick={logout}
              className="p-1.5 rounded-lg text-[#71717A] hover:text-[#EF4444] hover:bg-[#EF4444]/10 transition"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}

