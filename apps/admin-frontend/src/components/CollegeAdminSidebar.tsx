"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAdminAuth } from "@/hooks/use-admin-auth";
import {
  LayoutDashboard,
  Building2,
  Globe,
  Activity,
  FileText,
  Database,
  CheckSquare,
  Layers,
  BarChart3,
  LifeBuoy,
  Bell,
  ChevronLeft,
  ChevronRight,
  LogOut,
  GraduationCap,
  Sparkles,
} from "lucide-react";

const NAV_GROUPS = [
  {
    category: "INSTITUTION",
    items: [
      { name: "Overview", href: "/college-admin/dashboard", icon: LayoutDashboard },
      { name: "Onboarding Wizard", href: "/college-admin/onboarding", icon: Sparkles },
      { name: "College Profile", href: "/college-admin/profile", icon: Building2 },
    ],
  },
  {
    category: "INGESTION & DATA",
    items: [
      { name: "Website Sources", href: "/college-admin/websites", icon: Globe },
      { name: "Web Crawler", href: "/college-admin/crawler", icon: Activity },
      { name: "PDF Documents", href: "/college-admin/documents", icon: FileText },
    ],
  },
  {
    category: "KNOWLEDGE & REVIEWS",
    items: [
      { name: "Knowledge Base", href: "/college-admin/knowledge", icon: Database },
      { name: "Review Queue", href: "/college-admin/reviews", icon: CheckSquare },
      { name: "Structured Facts", href: "/college-admin/structured-data", icon: Layers },
      { name: "Courses & Fees", href: "/college-admin/academic", icon: GraduationCap },
      { name: "Image Gallery", href: "/college-admin/gallery", icon: Building2 },
    ],
  },
  {
    category: "INTELLIGENCE & SUPPORT",
    items: [
      { name: "Analytics", href: "/college-admin/analytics", icon: BarChart3 },
      { name: "Student Inquiries", href: "/college-admin/support", icon: LifeBuoy },
      { name: "Notifications", href: "/college-admin/notifications", icon: Bell },
    ],
  },
];

export function CollegeAdminSidebar() {
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
          <Link href="/college-admin/dashboard" className="flex items-center gap-3 overflow-hidden">
            <div className="h-9 w-9 min-w-9 rounded-lg bg-[#10B981] flex items-center justify-center text-white font-bold shadow-md shadow-[#10B981]/20">
              <GraduationCap className="h-5 w-5" />
            </div>
            {!collapsed && (
              <div>
                <span className="font-semibold text-sm text-[#F5F5F5] tracking-tight block leading-tight">
                  AI FAQ Colleges Chatbot <span className="text-[#10B981]">Admin</span>
                </span>
                <span className="text-[10px] text-[#A1A1AA] uppercase tracking-wider block">
                  College Workspace
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
        <div className="py-4 px-2 space-y-5 overflow-y-auto max-h-[calc(100vh-140px)]">
          {NAV_GROUPS.map((group, gIdx) => (
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
                        ? "bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/30 font-semibold"
                        : "text-[#A1A1AA] hover:text-[#F5F5F5] hover:bg-[#1F1F23]"
                    }`}
                  >
                    <Icon className={`h-4 w-4 min-w-4 ${isActive ? "text-[#10B981]" : "text-[#71717A]"}`} />
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
              <div className="h-8 w-8 min-w-8 rounded-full bg-[#1F1F23] border border-[#2A2A30] flex items-center justify-center text-xs font-bold text-[#10B981]">
                {admin?.full_name ? admin.full_name[0].toUpperCase() : "C"}
              </div>
              <div className="overflow-hidden">
                <span className="text-xs font-semibold text-[#F5F5F5] truncate block leading-tight">
                  {admin?.full_name || "College Admin"}
                </span>
                <span className="text-[10px] text-[#10B981] font-mono block">
                  COLLEGE_ADMIN
                </span>
              </div>
            </div>
          ) : (
            <div className="mx-auto h-8 w-8 rounded-full bg-[#1F1F23] border border-[#2A2A30] flex items-center justify-center text-xs font-bold text-[#10B981]">
              {admin?.full_name ? admin.full_name[0].toUpperCase() : "C"}
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

