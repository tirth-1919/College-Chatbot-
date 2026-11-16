"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAdminAuth } from "@/hooks/use-admin-auth";
import { CollegeAdminSidebar } from "@/components/CollegeAdminSidebar";
import { CollegeAdminNavbar } from "@/components/CollegeAdminNavbar";

export default function CollegeAdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { admin, isAuthenticated, isLoading } = useAdminAuth();

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.push("/login");
      } else if (admin?.role !== "COLLEGE_ADMIN" && admin?.role !== "SUPER_ADMIN") {
        router.push("/login");
      }
    }
  }, [isAuthenticated, admin, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0B0B0D] flex items-center justify-center text-xs text-[#A1A1AA]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-6 h-6 border-2 border-[#10B981] border-t-transparent rounded-full animate-spin" />
          <span>Authenticating college administrative credentials...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated || (admin?.role !== "COLLEGE_ADMIN" && admin?.role !== "SUPER_ADMIN")) {
    return null;
  }

  return (
    <div className="flex h-screen bg-[#0B0B0D] overflow-hidden">
      {/* College Admin Sidebar */}
      <CollegeAdminSidebar />

      {/* Main content body */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <CollegeAdminNavbar />
        <main className="flex-1 overflow-y-auto p-6 lg:p-8 bg-[#0B0B0D]">
          {children}
        </main>
      </div>
    </div>
  );
}

