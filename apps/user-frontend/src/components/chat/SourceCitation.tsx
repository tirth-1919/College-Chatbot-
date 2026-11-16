"use client";

import { useState } from "react";
import { SourceCitationData } from "@/services/chat-service";
import { ExternalLink, FileText, Globe, ChevronDown, ChevronUp } from "lucide-react";

interface SourceCitationProps {
  citations: SourceCitationData[];
}

export function SourceCitation({ citations }: SourceCitationProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-[#2A2A30] text-xs">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1.5 text-[#A1A1AA] hover:text-[#F5F5F5] font-medium transition mb-2"
      >
        <span>Grounded Sources ({citations.length})</span>
        {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
      </button>

      {isExpanded && (
        <div className="space-y-2 mt-2">
          {citations.map((cite, idx) => (
            <div
              key={idx}
              className="p-2.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23]/60 flex items-start justify-between gap-3"
            >
              <div className="flex items-start gap-2.5">
                <div className="p-1 rounded bg-[#111114] text-[#6366F1] mt-0.5">
                  {cite.source_type === "PDF" ? (
                    <FileText className="h-3.5 w-3.5" />
                  ) : (
                    <Globe className="h-3.5 w-3.5" />
                  )}
                </div>
                <div>
                  <div className="font-medium text-[#F5F5F5] leading-snug">
                    {cite.title}
                  </div>
                  <div className="text-[11px] text-[#A1A1AA] mt-0.5 space-x-2">
                    {cite.page_number && (
                      <span className="font-mono bg-[#111114] px-1.5 py-0.5 rounded border border-[#2A2A30]">
                        Page {cite.page_number}
                      </span>
                    )}
                    {cite.section && <span>Section: {cite.section}</span>}
                    {cite.similarity_score && (
                      <span className="text-[#10B981] font-mono">
                        {(cite.similarity_score * 100).toFixed(0)}% match
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {cite.url && (
                <a
                  href={cite.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1 rounded hover:bg-[#111114] text-[#A1A1AA] hover:text-[#6366F1] transition shrink-0"
                  title="Open official source link"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

