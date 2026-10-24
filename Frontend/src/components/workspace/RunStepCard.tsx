"use client";

import React, { useState } from "react";
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronRight,
  ListOrdered,
} from "lucide-react";
import { PipelineStep } from "@/lib/types";

interface RunStepCardProps {
  steps: PipelineStep[];
}

export function RunStepCard({ steps }: RunStepCardProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const completedCount = steps.filter((s) => s.status === "success").length;
  const isAllComplete = completedCount === steps.length && steps.length > 0;

  return (
    <div className="w-full rounded-xl bg-[#202C32] border border-[#3A4A50] p-4 font-sans text-xs shadow-md">
      <div
        className="flex items-center justify-between pb-2 mb-2 border-b border-[#3A4A50] cursor-pointer select-none"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-[#151E23] border border-[#3A4A50] flex items-center justify-center text-[#C3D1B8]">
            <ListOrdered className="w-3.5 h-3.5" />
          </div>
          <div>
            <h4 className="font-semibold text-[#EDF1EE] text-xs">Synthesis Pipeline</h4>
            <p className="text-[11px] font-mono text-[#ADBAB9]">
              {completedCount} of {steps.length} steps completed
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`text-[10px] font-mono px-2 py-0.5 rounded-sm border ${
              isAllComplete
                ? "bg-[#A7C4A2]/15 text-[#A7C4A2] border-[#A7C4A2]/30"
                : "bg-[#151E23] text-[#ADBAB9] border-[#3A4A50]"
            }`}
          >
            {isAllComplete ? "Verified" : "Processing"}
          </span>
          <button
            type="button"
            className="text-[#ADBAB9] hover:text-[#EDF1EE] p-1"
            aria-label={isExpanded ? "Collapse pipeline steps" : "Expand pipeline steps"}
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="space-y-2.5 pt-1">
          {steps.map((step, idx) => {
            const isSuccess = step.status === "success";
            const isRunning = step.status === "running";
            const isWarning = step.status === "warning";
            const isError = step.status === "error";

            return (
              <div
                key={step.id || idx}
                className={`p-2.5 rounded-lg border transition-all ${
                  isRunning
                    ? "bg-[#151E23] border-[#DDC38A]/40"
                    : isSuccess
                    ? "bg-[#151E23] border-[#3A4A50]/60"
                    : isError
                    ? "bg-[#E3A29E]/15 border-[#E3A29E]/40"
                    : "bg-[#151E23]/40 border-transparent opacity-60"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="shrink-0">
                      {isSuccess ? (
                        <CheckCircle2 className="w-4 h-4 text-[#A7C4A2]" />
                      ) : isRunning ? (
                        <Loader2 className="w-4 h-4 text-[#DDC38A] animate-spin" />
                      ) : isWarning ? (
                        <AlertTriangle className="w-4 h-4 text-[#DDC38A]" />
                      ) : isError ? (
                        <AlertCircle className="w-4 h-4 text-[#E3A29E]" />
                      ) : (
                        <div className="w-4 h-4 rounded-full border border-[#3A4A50] flex items-center justify-center text-[9px] font-mono text-[#ADBAB9]">
                          {idx + 1}
                        </div>
                      )}
                    </div>
                    <div>
                      <div className="font-medium text-[#EDF1EE] text-xs flex items-center gap-2">
                        <span>{step.title}</span>
                      </div>
                      <div className="text-[11px] text-[#ADBAB9] mt-0.5 font-normal">
                        {step.description}
                      </div>
                    </div>
                  </div>

                  {step.durationMs !== undefined && step.durationMs > 0 && (
                    <span className="shrink-0 font-mono text-[10px] text-[#ADBAB9] bg-[#202C32] px-1.5 py-0.5 rounded-xs border border-[#3A4A50]">
                      {step.durationMs}ms
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
