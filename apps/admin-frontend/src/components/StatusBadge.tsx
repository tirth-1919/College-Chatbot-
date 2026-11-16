"use client";

import React from "react";

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

export function StatusBadge({ status, size = "sm" }: StatusBadgeProps) {
  const norm = (status || "").toUpperCase();

  let colorClasses = "bg-[#27272A] text-[#A1A1AA] border-[#3F3F46]";

  if (
    norm === "APPROVED" ||
    norm === "ACTIVE" ||
    norm === "HEALTHY" ||
    norm === "RESOLVED" ||
    norm === "COMPLETED" ||
    norm === "SUCCESS"
  ) {
    colorClasses = "bg-[#10B981]/10 text-[#10B981] border-[#10B981]/20";
  } else if (
    norm === "PENDING" ||
    norm === "RUNNING" ||
    norm === "IN_PROGRESS" ||
    norm === "OPEN"
  ) {
    colorClasses = "bg-[#F59E0B]/10 text-[#F59E0B] border-[#F59E0B]/20";
  } else if (
    norm === "REJECTED" ||
    norm === "INACTIVE" ||
    norm === "FAILED" ||
    norm === "CRITICAL" ||
    norm === "SUSPENDED"
  ) {
    colorClasses = "bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/20";
  } else if (norm === "DEGRADED" || norm === "CLOSED") {
    colorClasses = "bg-[#71717A]/10 text-[#A1A1AA] border-[#71717A]/20";
  }

  const sizeClasses =
    size === "sm" ? "text-[11px] px-2 py-0.5" : "text-xs px-2.5 py-1";

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border ${sizeClasses} ${colorClasses}`}
    >
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-80" />
      {norm}
    </span>
  );
}

