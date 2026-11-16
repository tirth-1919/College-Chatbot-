"use client";

import React, { ReactNode } from "react";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

interface DashboardCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: ReactNode;
  iconColor?: string;
  trend?: string;
  trendUp?: boolean;
  href?: string;
}

export function DashboardCard({
  title,
  value,
  subtitle,
  icon,
  iconColor = "text-[#6366F1] bg-[#6366F1]/10",
  trend,
  trendUp,
  href,
}: DashboardCardProps) {
  const CardContent = (
    <div className="p-5 rounded-xl border border-[#2A2A30] bg-[#111114] hover:border-[#3F3F46] transition-all relative group flex flex-col justify-between">
      <div className="flex items-start justify-between mb-3">
        <div className={`p-2.5 rounded-lg ${iconColor}`}>
          {icon}
        </div>
        {href && (
          <div className="text-[#71717A] group-hover:text-[#F5F5F5] group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform">
            <ArrowUpRight className="h-4 w-4" />
          </div>
        )}
      </div>

      <div>
        <span className="text-2xl font-bold text-[#F5F5F5] tracking-tight block">
          {value}
        </span>
        <span className="text-xs font-medium text-[#A1A1AA] block mt-0.5">
          {title}
        </span>
      </div>

      {(subtitle || trend) && (
        <div className="mt-3 pt-3 border-t border-[#1F1F23] flex items-center justify-between text-[11px]">
          {subtitle && <span className="text-[#71717A]">{subtitle}</span>}
          {trend && (
            <span
              className={`font-medium ${
                trendUp === true
                  ? "text-[#10B981]"
                  : trendUp === false
                  ? "text-[#EF4444]"
                  : "text-[#A1A1AA]"
              }`}
            >
              {trend}
            </span>
          )}
        </div>
      )}
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block">
        {CardContent}
      </Link>
    );
  }

  return CardContent;
}

