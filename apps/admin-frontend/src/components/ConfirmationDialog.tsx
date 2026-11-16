"use client";

import React from "react";
import { AlertTriangle, X } from "lucide-react";

interface ConfirmationDialogProps {
  isOpen: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isDestructive?: boolean;
  isLoading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmationDialog({
  isOpen,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  isDestructive = false,
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmationDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-md bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl relative">
        <button
          onClick={onCancel}
          disabled={isLoading}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-[#71717A] hover:text-[#F5F5F5] hover:bg-[#1F1F23] transition"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div
            className={`p-2.5 rounded-xl ${
              isDestructive
                ? "bg-[#EF4444]/10 text-[#EF4444]"
                : "bg-[#6366F1]/10 text-[#6366F1]"
            }`}
          >
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-[#F5F5F5] leading-tight">
              {title}
            </h3>
            <p className="text-xs text-[#A1A1AA] mt-0.5">Please review before continuing</p>
          </div>
        </div>

        <p className="text-xs text-[#D4D4D8] leading-relaxed mb-6 bg-[#0B0B0D] p-3 rounded-lg border border-[#1F1F23]">
          {description}
        </p>

        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="px-4 py-2 text-xs font-medium text-[#A1A1AA] hover:text-[#F5F5F5] bg-[#1F1F23] hover:bg-[#2A2A30] rounded-lg transition"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className={`px-4 py-2 text-xs font-medium rounded-lg text-white transition flex items-center gap-2 ${
              isDestructive
                ? "bg-[#EF4444] hover:bg-[#DC2626]"
                : "bg-[#6366F1] hover:bg-[#4F46E5]"
            }`}
          >
            {isLoading ? "Processing..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

