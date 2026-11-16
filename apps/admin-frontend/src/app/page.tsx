"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAdminAuth } from "@/hooks/use-admin-auth";

export default function AdminRootPage() {
  const router = useRouter();
  const { admin, isAuthenticated, isLoading } = useAdminAuth();

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.push("/login");
      } else if (admin?.role === "SUPER_ADMIN") {
        router.push("/super-admin/dashboard");
      } else {
        router.push("/college-admin/dashboard");
      }
    }
  }, [admin, isAuthenticated, isLoading, router]);

  return (
    <div className="flex items-center justify-center min-h-screen text-sm text-[#A1A1AA]">
      Resolving administrative workspace...
    </div>
  );
}

