"use client";

import React from "react";
import { ShieldAlert, Check, X } from "lucide-react";

interface ApprovalCardProps {
  message?: string;
  onApprove: () => void;
  onReject: () => void;
}

export function ApprovalCard({
  message = "Operator confirmation required before promoting endpoints to production.",
  onApprove,
  onReject,
}: ApprovalCardProps) {
  return (
    <div className="w-full rounded-xl bg-[#11151A] border border-[#38BDF8]/40 p-4 font-sans text-xs shadow-lg animate-in fade-in">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg bg-[#38BDF8]/15 border border-[#38BDF8]/30 flex items-center justify-center text-[#38BDF8] shrink-0 mt-0.5">
          <ShieldAlert className="w-4 h-4" />
        </div>

        <div className="flex-1">
          <h4 className="font-semibold text-[#F4F5F7] text-sm mb-1">
            Governance Approval Gate
          </h4>
          <p className="text-[#A9B0BA] text-xs leading-relaxed mb-4">{message}</p>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onApprove}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#10B981] hover:bg-[#34D399] text-[#070709] font-semibold text-xs transition-colors"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Approve &amp; Activate</span>
            </button>

            <button
              type="button"
              onClick={onReject}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#181D23] hover:bg-[#202730] border border-white/10 text-[#F4F5F7] text-xs transition-colors"
            >
              <X className="w-3.5 h-3.5 text-[#F87171]" />
              <span>Reject</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
