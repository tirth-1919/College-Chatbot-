"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { collegeAdminService } from "@/services/college-admin-service";
import { CollegeNotification } from "@/types/college-admin";
import {
  Bell,
  RefreshCw,
  AlertTriangle,
  Info,
  CheckCircle,
  XCircle,
  CheckCheck,
} from "lucide-react";

export default function CollegeNotificationsPage() {
  const [notifications, setNotifications] = useState<CollegeNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  const fetchNotifications = async () => {
    setIsLoading(true);
    try {
      const res = await collegeAdminService.getNotifications();
      if (res.success && res.data) {
        setNotifications(res.data);
        const unread = res.data.filter((n) => n.is_read === false).length;
        setUnreadCount((res as any).unread_count !== undefined ? (res as any).unread_count : unread);
      }
    } catch (err) {
      console.error("Failed to load notifications:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const handleMarkAsRead = async (id: string) => {
    try {
      await collegeAdminService.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.error("Failed to mark notification read:", err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await collegeAdminService.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error("Failed to mark all notifications read:", err);
    }
  };

  const getIcon = (type?: string) => {
    const t = (type || "INFO").toUpperCase();
    switch (t) {
      case "WARNING":
        return <AlertTriangle className="h-5 w-5 text-[#F59E0B]" />;
      case "ERROR":
        return <XCircle className="h-5 w-5 text-[#EF4444]" />;
      case "SUCCESS":
        return <CheckCircle className="h-5 w-5 text-[#10B981]" />;
      default:
        return <Info className="h-5 w-5 text-[#3B82F6]" />;
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
            <Bell className="h-5 w-5 text-[#10B981]" />
            System Notifications & Institutional Alerts
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Real-time status updates on crawler discoveries, PDF OCR completions, and human verification reminders.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="px-3 py-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] text-xs text-[#F5F5F5] hover:border-[#10B981] hover:text-[#10B981] transition flex items-center gap-1.5"
            >
              <CheckCheck className="h-3.5 w-3.5" />
              <span>Mark all as read</span>
            </button>
          )}

          <button
            onClick={fetchNotifications}
            className="p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
            title="Refresh notifications"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Notifications Stream */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20 text-xs text-[#A1A1AA]">
          <div className="flex flex-col items-center gap-2">
            <div className="w-5 h-5 border-2 border-[#10B981] border-t-transparent rounded-full animate-spin" />
            <span>Checking institutional notifications...</span>
          </div>
        </div>
      ) : notifications.length > 0 ? (
        <div className="space-y-3">
          {notifications.map((n) => {
            const isUnread = n.is_read === false;
            return (
              <div
                key={n.id}
                onClick={() => isUnread && handleMarkAsRead(n.id)}
                className={`p-5 rounded-2xl border transition flex items-start gap-4 cursor-pointer ${
                  isUnread
                    ? "border-[#10B981]/40 bg-[#111114] shadow-sm shadow-[#10B981]/5"
                    : "border-[#2A2A30] bg-[#111114]/60 opacity-80 hover:opacity-100"
                }`}
              >
                <div className="p-2 rounded-xl bg-[#1F1F23] shrink-0 mt-0.5">
                  {getIcon(n.notification_type || n.type)}
                </div>
                <div className="flex-1 space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold text-[#F5F5F5]">
                        {n.title}
                      </h3>
                      {isUnread && (
                        <span className="h-2 w-2 rounded-full bg-[#10B981] animate-pulse" />
                      )}
                    </div>
                    <span className="text-[10px] text-[#71717A]">
                      {new Date(n.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                  <p className="text-xs text-[#A1A1AA] leading-relaxed">
                    {n.message}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="p-12 text-center rounded-2xl border border-[#2A2A30] bg-[#111114]">
          <div className="h-12 w-12 rounded-full bg-[#10B981]/10 text-[#10B981] flex items-center justify-center mx-auto mb-3">
            <CheckCircle className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-semibold text-[#F5F5F5] mb-1">
            No Active Alerts
          </h3>
          <p className="text-xs text-[#A1A1AA] max-w-sm mx-auto">
            All system processes for this college are operating cleanly with zero errors.
          </p>
        </div>
      )}
    </div>
  );
}

