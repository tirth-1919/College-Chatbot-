"use client";

import { useState } from "react";
import { College } from "@/types/college";
import { Building2, X, ArrowLeftRight, Check, AlertCircle } from "lucide-react";

interface SwitchCollegeModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentCollegeId: string;
  colleges: College[];
  onSwitch: (targetCollege: College) => Promise<void>;
}

export function SwitchCollegeModal({
  isOpen,
  onClose,
  currentCollegeId,
  colleges,
  onSwitch,
}: SwitchCollegeModalProps) {
  const [selectedCollege, setSelectedCollege] = useState<College | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSelect = (college: College) => {
    if (college.id === currentCollegeId) return;
    setSelectedCollege(college);
    setIsConfirming(true);
    setError(null);
  };

  const handleConfirmSwitch = async () => {
    if (!selectedCollege) return;
    setIsSwitching(true);
    setError(null);
    try {
      await onSwitch(selectedCollege);
      setIsSwitching(false);
      setIsConfirming(false);
      setSelectedCollege(null);
      onClose();
    } catch (err: any) {
      setIsSwitching(false);
      setError(err?.message || "Failed to switch college. Please try again.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-lg rounded-2xl border border-[#2A2A30] bg-[#111114] p-6 shadow-2xl relative">
        <button
          onClick={() => {
            setIsConfirming(false);
            setSelectedCollege(null);
            onClose();
          }}
          className="absolute right-4 top-4 text-[#A1A1AA] hover:text-[#F5F5F5] transition p-1 rounded-lg hover:bg-[#1F1F23]"
          title="Close"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex items-center gap-3 mb-5">
          <div className="h-10 w-10 rounded-xl bg-[#6366F1]/10 border border-[#6366F1]/20 flex items-center justify-center text-[#6366F1]">
            <ArrowLeftRight className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-[#F5F5F5]">Switch College Institution</h3>
            <p className="text-xs text-[#A1A1AA]">Select another registered college for this conversation</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 p-3 rounded-lg border border-red-500/30 bg-red-950/40 text-xs text-red-200">
            <AlertCircle className="h-4 w-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {!isConfirming ? (
          <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
            {colleges.map((col) => {
              const isCurrent = col.id === currentCollegeId;
              return (
                <button
                  key={col.id}
                  type="button"
                  onClick={() => handleSelect(col)}
                  disabled={isCurrent}
                  className={`w-full text-left p-3.5 rounded-xl border transition flex items-center justify-between ${
                    isCurrent
                      ? "border-[#6366F1]/40 bg-[#6366F1]/10 cursor-default"
                      : "border-[#2A2A30] bg-[#1F1F23] hover:border-[#6366F1] hover:bg-[#25252A]"
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="h-8 w-8 rounded-lg bg-[#2A2A30] flex items-center justify-center text-[#A1A1AA] shrink-0">
                      <Building2 className="h-4 w-4" />
                    </div>
                    <div className="truncate">
                      <div className="text-xs font-semibold text-[#F5F5F5] truncate">{col.name}</div>
                      <div className="text-[11px] text-[#A1A1AA] truncate">{col.official_domain}</div>
                    </div>
                  </div>
                  {isCurrent ? (
                    <span className="text-[11px] font-medium text-[#10B981] bg-[#10B981]/10 px-2 py-0.5 rounded-full border border-[#10B981]/20 shrink-0">
                      Current
                    </span>
                  ) : (
                    <span className="text-xs text-[#6366F1] font-medium shrink-0">
                      Select
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="p-4 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5]">
              <p className="mb-2 text-xs text-[#A1A1AA]">
                Switch current conversation to:
              </p>
              <div className="font-semibold text-sm text-white flex items-center gap-2">
                <Building2 className="h-4 w-4 text-[#6366F1]" />
                {selectedCollege?.name}
              </div>
              <p className="text-[11px] text-[#A1A1AA] mt-2">
                Subsequent questions will be answered using {selectedCollege?.name}&apos;s verified knowledge base.
              </p>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                type="button"
                onClick={() => {
                  setIsConfirming(false);
                  setSelectedCollege(null);
                }}
                disabled={isSwitching}
                className="px-4 py-2 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-xs font-medium text-[#A1A1AA] hover:text-[#F5F5F5] transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmSwitch}
                disabled={isSwitching}
                className="px-4 py-2 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] text-xs font-semibold text-white transition flex items-center gap-2 shadow-md shadow-[#6366F1]/20 disabled:opacity-50"
              >
                {isSwitching ? (
                  <span>Switching...</span>
                ) : (
                  <>
                    <Check className="h-4 w-4" />
                    <span>Confirm Switch</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
