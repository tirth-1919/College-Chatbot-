"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { GraduationCap, MessageSquare, Building2, User, LogOut, ShieldCheck, Clock } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";

export function Navbar() {
  const pathname = usePathname();
  const { user, isAuthenticated, logout } = useAuth();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // When on the chatbot page (/chat), hide the top navigation bar completely (ChatGPT layout)
  if (pathname === "/chat" || pathname?.startsWith("/chat")) {
    return null;
  }

  return (
    <nav className="border-b border-[#2A2A30] bg-[#111114]/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <div className="h-9 w-9 rounded-lg bg-[#6366F1] flex items-center justify-center text-white font-bold">
            <GraduationCap className="h-5 w-5" />
          </div>
          <span className="font-semibold text-lg text-[#F5F5F5] tracking-tight">
            Campus<span className="text-[#6366F1]">AI</span>
          </span>
        </Link>

        <div className="flex items-center gap-5 sm:gap-6">
          <Link
            href="/colleges"
            className="flex items-center gap-1.5 text-sm text-[#A1A1AA] hover:text-[#F5F5F5] transition"
          >
            <Building2 className="h-4 w-4" />
            Colleges
          </Link>
          <Link
            href="/chat"
            className="flex items-center gap-1.5 text-sm text-[#A1A1AA] hover:text-[#F5F5F5] transition"
          >
            <MessageSquare className="h-4 w-4" />
            Chatbot
          </Link>
          <Link
            href="/register-college"
            className="hidden md:flex items-center gap-1.5 text-sm text-[#A1A1AA] hover:text-[#818CF8] transition"
          >
            <ShieldCheck className="h-4 w-4 text-[#6366F1]" />
            Register Institution
          </Link>
          <Link
            href="/registration-status"
            className="hidden lg:flex items-center gap-1.5 text-sm text-[#A1A1AA] hover:text-[#F5F5F5] transition"
          >
            <Clock className="h-4 w-4" />
            Track Status
          </Link>

          {!mounted ? (
            <div className="flex items-center gap-3 min-w-[120px] justify-end"></div>
          ) : isAuthenticated ? (
            <div className="flex items-center gap-3">
              <Link
                href="/dashboard"
                className="flex items-center gap-1.5 text-sm text-[#F5F5F5] bg-[#1F1F23] px-3 py-1.5 rounded-md border border-[#2A2A30]"
              >
                <User className="h-4 w-4 text-[#6366F1]" />
                {user?.full_name?.split(" ")[0]}
              </Link>
              <button
                onClick={logout}
                className="text-sm text-[#A1A1AA] hover:text-[#EF4444] transition flex items-center gap-1"
                title="Logout"
              >
                <LogOut className="h-4 w-4" />
              </button>
              <ThemeToggle />
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <Link
                href="/login"
                className="text-sm text-[#A1A1AA] hover:text-[#F5F5F5] transition px-3 py-1.5"
              >
                Sign In
              </Link>
              <Link
                href="/register"
                className="text-sm text-white bg-[#6366F1] hover:bg-[#4F46E5] transition px-3.5 py-1.5 rounded-md font-medium"
              >
                Get Started
              </Link>
              <ThemeToggle />
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}

