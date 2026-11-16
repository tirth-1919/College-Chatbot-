"use client";

import React, { useEffect, useState } from "react";
import { superAdminService } from "@/services/super-admin-service";
import { SystemSettings } from "@/types/admin";
import {
  Settings,
  Save,
  RotateCcw,
  ShieldAlert,
  Sliders,
  Globe,
  UploadCloud,
  Gauge,
  Lock,
  CheckCircle,
} from "lucide-react";

export default function GlobalSettingsPage() {
  const [settings, setSettings] = useState<SystemSettings>({
    allow_college_registration: true,
    default_language: "en",
    max_pdf_upload_mb: 50,
    rate_limit_per_minute: 60,
    maintenance_mode: false,
    rag_similarity_threshold: 0.72,
  });

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchSettings = async () => {
    setIsLoading(true);
    try {
      const res = await superAdminService.getSystemSettings();
      if (res.success && res.data) {
        setSettings(res.data);
      }
    } catch (err) {
      console.error("Failed to load settings:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSuccessMsg(null);

    try {
      const res = await superAdminService.updateSystemSettings(settings);
      if (res.success) {
        setSuccessMsg("Global platform parameters updated successfully!");
        setTimeout(() => setSuccessMsg(null), 4000);
      }
    } catch (err) {
      console.error("Failed to update settings:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleResetDefaults = () => {
    setSettings({
      allow_college_registration: true,
      default_language: "en",
      max_pdf_upload_mb: 50,
      rate_limit_per_minute: 60,
      maintenance_mode: false,
      rag_similarity_threshold: 0.72,
    });
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
            <Settings className="h-5 w-5 text-[#6366F1]" />
            Global Platform Settings & Governance
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            System-wide operational controls, tenant registration toggles, RAG vector thresholds, and rate limiting.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleResetDefaults}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#2A2A30] bg-[#111114] hover:bg-[#1F1F23] text-xs font-medium text-[#A1A1AA] hover:text-[#F5F5F5] transition"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Reset Defaults</span>
          </button>
        </div>
      </div>

      {successMsg && (
        <div className="p-4 rounded-xl bg-[#10B981]/10 border border-[#10B981]/30 flex items-center gap-3 text-xs text-[#10B981] animate-in fade-in">
          <CheckCircle className="h-4 w-4 min-w-4" />
          <span>{successMsg}</span>
        </div>
      )}

      {settings.maintenance_mode && (
        <div className="p-4 rounded-xl bg-[#EF4444]/10 border border-[#EF4444]/30 flex items-center gap-3 text-xs text-[#EF4444]">
          <ShieldAlert className="h-5 w-5 min-w-5" />
          <div>
            <span className="font-bold block">PLATFORM IN MAINTENANCE MODE</span>
            <span>Public student chatbot inquiries and ingestion jobs are temporarily blocked for non-superadmins.</span>
          </div>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Onboarding & Access Controls */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-5">
          <h3 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
            <Lock className="h-4 w-4 text-[#6366F1]" />
            Tenant Onboarding & Security Controls
          </h3>

          <div className="flex items-center justify-between py-3 border-b border-[#1F1F23]">
            <div>
              <span className="text-xs font-medium text-[#F5F5F5] block">
                Allow College Registration
              </span>
              <span className="text-[11px] text-[#71717A]">
                When enabled, colleges can submit new tenant onboarding applications.
              </span>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.allow_college_registration}
                onChange={(e) =>
                  setSettings({ ...settings, allow_college_registration: e.target.checked })
                }
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-[#1F1F23] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#6366F1]"></div>
            </label>
          </div>

          <div className="flex items-center justify-between py-3">
            <div>
              <span className="text-xs font-medium text-[#F5F5F5] block">
                Platform Maintenance Mode
              </span>
              <span className="text-[11px] text-[#71717A]">
                Locks student queries and restricts portal access exclusively to Super Administrators.
              </span>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.maintenance_mode}
                onChange={(e) =>
                  setSettings({ ...settings, maintenance_mode: e.target.checked })
                }
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-[#1F1F23] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#EF4444]"></div>
            </label>
          </div>
        </div>

        {/* AI & RAG Precision Tuning */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-5">
          <h3 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
            <Sliders className="h-4 w-4 text-[#6366F1]" />
            RAG Grounding & Search Precision
          </h3>

          <div>
            <div className="flex justify-between mb-1.5 text-xs">
              <span className="font-medium text-[#F5F5F5]">
                Vector Cosine Similarity Threshold
              </span>
              <span className="font-mono text-[#6366F1] font-bold">
                {settings.rag_similarity_threshold}
              </span>
            </div>
            <input
              type="range"
              min="0.5"
              max="0.95"
              step="0.01"
              value={settings.rag_similarity_threshold}
              onChange={(e) =>
                setSettings({ ...settings, rag_similarity_threshold: parseFloat(e.target.value) })
              }
              className="w-full accent-[#6366F1]"
            />
            <span className="text-[11px] text-[#71717A] block mt-1">
              Documents scoring below this cosine similarity threshold are discarded to prevent hallucinations (Recommended: 0.70 - 0.78).
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3 border-t border-[#1F1F23]">
            <div>
              <label className="block text-xs font-medium text-[#F5F5F5] mb-1">
                Default Portal Language
              </label>
              <select
                value={settings.default_language}
                onChange={(e) =>
                  setSettings({ ...settings, default_language: e.target.value })
                }
                className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-xs text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
              >
                <option value="en">English (en)</option>
                <option value="hi">Hindi (hi)</option>
                <option value="gu">Gujarati (gu)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-[#F5F5F5] mb-1">
                Max Document Upload Limit (MB)
              </label>
              <input
                type="number"
                min="5"
                max="200"
                value={settings.max_pdf_upload_mb}
                onChange={(e) =>
                  setSettings({ ...settings, max_pdf_upload_mb: parseInt(e.target.value) })
                }
                className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-xs text-[#F5F5F5] font-mono focus:outline-none focus:border-[#6366F1]"
              />
            </div>
          </div>
        </div>

        {/* Rate Limiting */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4">
          <h3 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
            <Gauge className="h-4 w-4 text-[#6366F1]" />
            DDoS & Abuse Protection
          </h3>

          <div>
            <label className="block text-xs font-medium text-[#F5F5F5] mb-1">
              Global Rate Limit (Requests per minute per IP)
            </label>
            <input
              type="number"
              min="10"
              max="500"
              value={settings.rate_limit_per_minute}
              onChange={(e) =>
                setSettings({ ...settings, rate_limit_per_minute: parseInt(e.target.value) })
              }
              className="w-full max-w-xs bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-xs text-[#F5F5F5] font-mono focus:outline-none focus:border-[#6366F1]"
            />
            <span className="text-[11px] text-[#71717A] block mt-1">
              Limits anonymous student questions and public endpoints using sliding window counters.
            </span>
          </div>
        </div>

        {/* Form Actions */}
        <div className="flex items-center justify-end gap-3 pt-4">
          <button
            type="submit"
            disabled={isSaving}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#6366F1] hover:bg-[#4F46E5] text-white text-xs font-medium transition shadow-lg shadow-[#6366F1]/20"
          >
            <Save className="h-4 w-4" />
            <span>{isSaving ? "Saving Settings..." : "Save Platform Settings"}</span>
          </button>
        </div>
      </form>
    </div>
  );
}

