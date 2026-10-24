"use client";

import React from "react";
import { AlertCircle, RefreshCw, Edit3 } from "lucide-react";

interface RunErrorCardProps {
  errorMessage?: string;
  onRetry: () => void;
  onEditPrompt: () => void;
}

export function RunErrorCard({
  errorMessage = "Extraction failed. The website structure could not be mapped to the requested fields.",
  onRetry,
  onEditPrompt,
}: RunErrorCardProps) {
  return (
    <div className="w-full rounded-xl bg-[#11151A] border border-[#EF4444]/40 p-4 font-sans text-xs shadow-lg animate-in fade-in">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg bg-[#EF4444]/15 border border-[#EF4444]/30 flex items-center justify-center text-[#F87171] shrink-0 mt-0.5">
          <AlertCircle className="w-4 h-4" />
        </div>

        <div className="flex-1">
          <h4 className="font-semibold text-[#F87171] text-sm mb-1">
            Extraction Interrupted
          </h4>
          <p className="text-[#A9B0BA] text-xs leading-relaxed mb-4">{errorMessage}</p>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#181D23] hover:bg-[#202730] border border-white/10 text-[#F4F5F7] font-semibold text-xs transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5 text-[#10B981]" />
              <span>Retry Extraction</span>
            </button>

            <button
              type="button"
              onClick={onEditPrompt}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#11151A] hover:bg-[#181D23] border border-white/10 text-[#A9B0BA] hover:text-[#F4F5F7] text-xs transition-colors"
            >
              <Edit3 className="w-3.5 h-3.5" />
              <span>Refine Request</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
