"use client";

import React, { useEffect, useState } from "react";
import { collegeAdminService } from "@/services/college-admin-service";
import { CollegeProfile } from "@/types/college-admin";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Building2,
  Save,
  Globe,
  Mail,
  Phone,
  Image as ImageIcon,
  CheckCircle,
  ExternalLink,
  Shield,
} from "lucide-react";

export default function CollegeProfilePage() {
  const [profile, setProfile] = useState<CollegeProfile | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    official_domain: "",
    contact_email: "",
    contact_phone: "",
    logo_url: "",
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchProfile = async () => {
    setIsLoading(true);
    try {
      const res = await collegeAdminService.getProfile();
      if (res.success && res.data) {
        setProfile(res.data);
        setFormData({
          name: res.data.name || "",
          official_domain: res.data.official_domain || "",
          contact_email: res.data.contact_email || "",
          contact_phone: res.data.contact_phone || "",
          logo_url: res.data.logo_url || "",
        });
      }
    } catch (err) {
      console.error("Failed to load profile:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSuccessMsg(null);
    setErrorMsg(null);

    try {
      const res = await collegeAdminService.updateProfile(formData);
      if (res.success && res.data) {
        setProfile(res.data);
        setSuccessMsg("College institutional profile updated successfully!");
        setTimeout(() => setSuccessMsg(null), 4000);
      } else {
        setErrorMsg(res.error || "Failed to update profile.");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "An unexpected error occurred.");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20 text-xs text-[#A1A1AA]">
        <div className="flex flex-col items-center gap-2">
          <div className="w-5 h-5 border-2 border-[#10B981] border-t-transparent rounded-full animate-spin" />
          <span>Loading institutional profile...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
          <Building2 className="h-5 w-5 text-[#10B981]" />
          College Profile & Institutional Metadata
        </h1>
        <p className="text-xs text-[#A1A1AA] mt-1">
          Manage your institution's public profile, official domain, and administrative contact channels.
        </p>
      </div>

      {successMsg && (
        <div className="p-4 rounded-xl bg-[#10B981]/10 border border-[#10B981]/30 flex items-center gap-3 text-xs text-[#10B981] animate-in fade-in">
          <CheckCircle className="h-4 w-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 rounded-xl bg-[#EF4444]/10 border border-[#EF4444]/30 flex items-center gap-3 text-xs text-[#EF4444]">
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Profile Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Core Institutional Identification */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4">
          <h3 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
            <Shield className="h-4 w-4 text-[#10B981]" />
            Official Identification
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-[#A1A1AA] font-medium mb-1">
                College Institutional Name *
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
              />
            </div>

            <div>
              <label className="block text-[#A1A1AA] font-medium mb-1">
                Permanent Slug Identifier (Immutable)
              </label>
              <input
                type="text"
                disabled
                value={profile?.slug || ""}
                className="w-full bg-[#18181B] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#71717A] font-mono cursor-not-allowed"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-2">
            <div>
              <label className="block text-[#A1A1AA] font-medium mb-1">
                Official Institutional Domain *
              </label>
              <div className="relative">
                <Globe className="absolute left-3 top-2.5 h-4 w-4 text-[#71717A]" />
                <input
                  type="text"
                  required
                  value={formData.official_domain}
                  onChange={(e) => setFormData({ ...formData, official_domain: e.target.value })}
                  placeholder="e.g. aitindia.in"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg pl-9 pr-3 py-2 text-[#F5F5F5] font-mono focus:outline-none focus:border-[#10B981]"
                />
              </div>
            </div>

            <div>
              <label className="block text-[#A1A1AA] font-medium mb-1">
                Registration Status
              </label>
              <div className="h-9 flex items-center gap-2">
                <StatusBadge status={profile?.status || "APPROVED"} />
                <span className="text-[11px] text-[#71717A]">
                  (Status managed by Global Super Administrator)
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Contact Channels */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4">
          <h3 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
            <Mail className="h-4 w-4 text-[#10B981]" />
            Official Inquiries & Contact Channels
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-[#A1A1AA] font-medium mb-1">
                Official Contact Email *
              </label>
              <input
                type="email"
                required
                value={formData.contact_email}
                onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
              />
            </div>

            <div>
              <label className="block text-[#A1A1AA] font-medium mb-1">
                Official Helpline / Phone
              </label>
              <div className="relative">
                <Phone className="absolute left-3 top-2.5 h-4 w-4 text-[#71717A]" />
                <input
                  type="text"
                  value={formData.contact_phone}
                  onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                  placeholder="+91 79 2970 8000"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg pl-9 pr-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                />
              </div>
            </div>
          </div>

          <div className="text-xs pt-2">
            <label className="block text-[#A1A1AA] font-medium mb-1">
              Institutional Logo URL
            </label>
            <div className="relative">
              <ImageIcon className="absolute left-3 top-2.5 h-4 w-4 text-[#71717A]" />
              <input
                type="url"
                value={formData.logo_url}
                onChange={(e) => setFormData({ ...formData, logo_url: e.target.value })}
                placeholder="https://example.edu/logo.png"
                className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg pl-9 pr-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
              />
            </div>
          </div>
        </div>

        {/* Submit Action */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="submit"
            disabled={isSaving}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#10B981] hover:bg-[#059669] text-white text-xs font-medium transition shadow-lg shadow-[#10B981]/20"
          >
            <Save className="h-4 w-4" />
            <span>{isSaving ? "Saving..." : "Save Profile Details"}</span>
          </button>
        </div>
      </form>
    </div>
  );
}

