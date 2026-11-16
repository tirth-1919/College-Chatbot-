"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAdminAuth } from "@/hooks/use-admin-auth";
import { collegeAdminService } from "@/services/college-admin-service";
import { CollegeProfile } from "@/types/college-admin";
import {
  GraduationCap,
  ExternalLink,
  Bell,
  Building2,
  ShieldCheck,
} from "lucide-react";

export function CollegeAdminNavbar() {
  const pathname = usePathname();
  const { admin } = useAdminAuth();
  const [college, setCollege] = useState<CollegeProfile | null>(null);

  useEffect(() => {
    collegeAdminService.getProfile().then((res) => {
      if (res.success && res.data) setCollege(res.data);
    });
  }, []);

  const getBreadcrumb = () => {
    if (pathname.includes("/profile")) return "College Profile & Metadata";
    if (pathname.includes("/websites")) return "Website Sources";
    if (pathname.includes("/crawler")) return "Web Crawler Management";
    if (pathname.includes("/documents")) return "PDF Document Ingestion";
    if (pathname.includes("/knowledge")) return "Knowledge Base Explorer";
    if (pathname.includes("/reviews")) return "Knowledge Review Queue";
    if (pathname.includes("/structured-data")) return "Structured College Facts";
    if (pathname.includes("/analytics")) return "Institutional Telemetry";
    if (pathname.includes("/support")) return "Student Support Inquiries";
    if (pathname.includes("/notifications")) return "System Alerts & Notices";
    return "Institutional Overview";
  };

  return (
    <header className="h-16 border-b border-[#2A2A30] bg-[#111114] px-6 flex items-center justify-between z-30">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-[#71717A]">College Admin</span>
        <span className="text-xs text-[#3F3F46]">/</span>
        <h2 className="text-sm font-semibold text-[#F5F5F5]">{getBreadcrumb()}</h2>
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-4">
        {/* College Tenant Badge */}
        {college && (
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-[#1F1F23] border border-[#2A2A30] text-xs">
            <Building2 className="h-3.5 w-3.5 text-[#10B981]" />
            <span className="font-medium text-[#F5F5F5] max-w-[200px] truncate">
              {college.name}
            </span>
            <span className="text-[10px] text-[#10B981] font-mono px-1.5 py-0.2 rounded bg-[#10B981]/10">
              Verified Tenant
            </span>
          </div>
        )}

        {/* Notifications shortcut */}
        <Link
          href="/college-admin/notifications"
          className="p-2 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-[#A1A1AA] hover:text-[#F5F5F5] transition relative"
          title="Notifications"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[#10B981]" />
        </Link>

        {/* User Portal Link */}
        <a
          href="http://localhost:3000"
          target="_blank"
          rel="noopener noreferrer"
          className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-[#A1A1AA] hover:text-[#F5F5F5] text-xs transition"
        >
          <span>Live Chatbot</span>
          <ExternalLink className="h-3 w-3" />
        </a>

        {/* User Profile */}
        <div className="flex items-center gap-2 pl-2 border-l border-[#2A2A30]">
          <div className="h-7 w-7 rounded-lg bg-[#10B981]/10 border border-[#10B981]/30 flex items-center justify-center text-[#10B981]">
            <GraduationCap className="h-4 w-4" />
          </div>
          <div className="text-right hidden sm:block">
            <span className="text-xs font-medium text-[#F5F5F5] block leading-tight">
              {admin?.full_name || "College Admin"}
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

