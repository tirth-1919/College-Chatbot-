"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAdminAuth } from "@/hooks/use-admin-auth";
import { Shield, Bell, ExternalLink, Activity } from "lucide-react";

export function AdminNavbar() {
  const pathname = usePathname();
  const { admin } = useAdminAuth();

  // Dynamic breadcrumb title
  const getBreadcrumb = () => {
    if (pathname.includes("/colleges")) return "Colleges & Tenants";
    if (pathname.includes("/registrations")) return "Registration Queue";
    if (pathname.includes("/admins")) return "College Administrators";
    if (pathname.includes("/users")) return "Platform User Directory";
    if (pathname.includes("/ai-providers")) return "AI Provider Configurations";
    if (pathname.includes("/analytics")) return "Usage & Token Telemetry";
    if (pathname.includes("/usage")) return "Background Ingestion Jobs";
    if (pathname.includes("/audit-logs")) return "Compliance Security Audit";
    if (pathname.includes("/support")) return "Student Support Tickets";
    if (pathname.includes("/system-health")) return "System Infrastructure Health";
    if (pathname.includes("/settings")) return "Global Platform Settings";
    return "Platform Overview";
  };

  return (
    <header className="h-16 border-b border-[#2A2A30] bg-[#111114] px-6 flex items-center justify-between z-30">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-[#71717A]">Super Admin</span>
        <span className="text-xs text-[#3F3F46]">/</span>
        <h2 className="text-sm font-semibold text-[#F5F5F5]">{getBreadcrumb()}</h2>
      </div>

      {/* Top right actions */}
      <div className="flex items-center gap-4">
        {/* Live system status indicator pill */}
        <Link
          href="/super-admin/system-health"
          className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-full bg-[#10B981]/10 border border-[#10B981]/20 text-[11px] font-medium text-[#10B981] hover:bg-[#10B981]/20 transition"
        >
          <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse" />
          <span>Systems Operational</span>
        </Link>

        {/* User Frontend Link shortcut */}
        <a
          href="http://localhost:3000"
          target="_blank"
          rel="noopener noreferrer"
          className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-[#A1A1AA] hover:text-[#F5F5F5] text-xs transition"
        >
          <span>Student Portal</span>
          <ExternalLink className="h-3 w-3" />
        </a>

        {/* Super admin badge */}
        <div className="flex items-center gap-2 pl-2 border-l border-[#2A2A30]">
          <div className="h-7 w-7 rounded-lg bg-[#6366F1]/10 border border-[#6366F1]/30 flex items-center justify-center text-[#6366F1]">
            <Shield className="h-4 w-4" />
          </div>
          <div className="text-right hidden sm:block">
            <span className="text-xs font-medium text-[#F5F5F5] block leading-tight">
              {admin?.full_name || "Super Admin"}
            </span>
            <span className="text-[10px] text-[#A1A1AA] block leading-none">
              {admin?.email}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
