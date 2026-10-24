"use client";

import React, { useState } from "react";
import {
  Check,
  ChevronDown,
  ChevronRight,
  Loader2,
  AlertCircle,
  FileCode,
  Table,
  Terminal,
  ShieldAlert,
} from "lucide-react";
import { PipelineStep, FieldDefinition, PageMetadata, LogEntry, RunSession } from "@/lib/types";

interface InlineAgentActivityProps {
  session: RunSession;
  onApprove?: () => void;
  onReject?: () => void;
  onRetry?: () => void;
}

export function InlineAgentActivity({
  session,
  onApprove,
  onReject,
  onRetry,
}: InlineAgentActivityProps) {
  const isFinished = session.status === "completed" || session.status === "failed";
  const [isActivityOpen, setIsActivityOpen] = useState(!isFinished);
  const [expandedStepId, setExpandedStepId] = useState<string | null>(null);
  const [showLogs, setShowLogs] = useState(false);

  const completedStepsCount = session.steps.filter((s) => s.status === "success").length;
  const totalSteps = session.steps.length;

  const toggleStep = (id: string) => {
    setExpandedStepId(expandedStepId === id ? null : id);
  };

  return (
    <div className="w-full flex flex-col font-sans text-[14px] text-[#EDF1EE] my-2 select-text">
      {/* Finished Summary Pill (when completed, can be toggled) */}
      {isFinished && (
        <button
          type="button"
          onClick={() => setIsActivityOpen(!isActivityOpen)}
          className="inline-flex items-center gap-2 self-start py-1.5 px-3 rounded-lg bg-[#202C32] hover:bg-[#2A3940] text-[14px] font-medium font-sans text-[#ADBAB9] hover:text-[#EDF1EE] transition-colors border border-[#3A4A50] mb-2"
        >
          <div className="w-4 h-4 rounded-full bg-[#A7C4A2]/20 text-[#A7C4A2] flex items-center justify-center">
            <Check className="w-2.5 h-2.5" />
          </div>
          <span>
            {session.status === "completed"
              ? `Completed ${completedStepsCount} step${completedStepsCount === 1 ? "" : "s"} · ${isActivityOpen ? "Hide" : "View"} activity`
              : `Run failed at step ${completedStepsCount + 1} · ${isActivityOpen ? "Hide" : "View"} activity`}
          </span>
          {isActivityOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </button>
      )}

      {/* Activity Group: Storm surface container with comfortable spacing */}
      {isActivityOpen && (
        <div className="w-full rounded-xl bg-[#202C32] border border-[#3A4A50] p-3.5 sm:p-4 space-y-3 mb-3">
          {/* List of Steps: 14-15px with comfortable spacing */}
          <div className="space-y-2.5">
            {session.steps.map((step, idx) => {
              const isExpanded = expandedStepId === step.id;
              const hasFieldData = step.id.includes("field") && session.discoveredFields.length > 0;
              const hasMetadata = (step.id.includes("inspect") || step.id.includes("page")) && session.pageMetadata;
              const hasSampleData = (step.id.includes("validate") || step.id.includes("extract")) && session.endpoints.length > 0 && session.endpoints[0].sampleResponse;
              const canExpand = hasFieldData || hasMetadata || hasSampleData || !!step.details;

              return (
                <div key={step.id} className="text-[14px] sm:text-[15px] font-sans">
                  <div
                    onClick={() => canExpand && toggleStep(step.id)}
                    className={`flex items-start gap-3 py-2 px-2.5 rounded-md transition-colors ${
                      canExpand ? "cursor-pointer hover:bg-[#2A3940]" : ""
                    }`}
                  >
                    {/* Status Icon */}
                    <div className="mt-0.5 shrink-0">
                      {step.status === "running" ? (
                        <Loader2 className="w-4 h-4 animate-spin text-[#AEC8D0]" />
                      ) : step.status === "success" ? (
                        <div className="w-4 h-4 rounded-full bg-[#A7C4A2]/20 text-[#A7C4A2] flex items-center justify-center">
                          <Check className="w-2.5 h-2.5" />
                        </div>
                      ) : step.status === "error" ? (
                        <AlertCircle className="w-4 h-4 text-[#E3A29E]" />
                      ) : (
                        <div className="w-4 h-4 rounded-full border border-[#3A4A50]" />
                      )}
                    </div>

                    {/* Step Title & Description: Uncut Sans 14-15px with comfortable spacing */}
                    <div className="flex-1 flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1 sm:gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-[#EDF1EE]">{step.title}</span>
                        {step.description && (
                          <span className="text-[#ADBAB9] text-[13px] sm:text-[14px]">— {step.description}</span>
                        )}
                      </div>

                      <div className="flex items-center gap-1.5 text-[12px] sm:text-[13px] text-[#ADBAB9] font-mono tracking-normal shrink-0">
                        {step.durationMs && <span>{step.durationMs}ms</span>}
                        {canExpand && (
                          <span className="text-[#ADBAB9] hover:text-[#EDF1EE]">
                            {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Expandable Step Details */}
                  {isExpanded && (
                    <div className="mt-2 ml-7 p-3 rounded-lg bg-[#10171B] border border-[#3A4A50] space-y-2.5 text-[13px]">
                      {hasMetadata && session.pageMetadata && (
                        <div className="space-y-1 font-mono text-[13px] tracking-normal text-[#ADBAB9]">
                          <div className="text-[#EDF1EE] font-sans font-medium mb-1">Target Page Metadata</div>
                          <div>Host: <span className="text-[#EDF1EE]">{session.pageMetadata.hostname}</span></div>
                          <div>Elements Inspected: <span className="text-[#EDF1EE]">{session.pageMetadata.elementsInspected || 84}</span></div>
                          {session.pageMetadata.title && (
                            <div className="truncate">Title: <span className="text-[#EDF1EE]">{session.pageMetadata.title}</span></div>
                          )}
                        </div>
                      )}

                      {hasFieldData && (
                        <div className="space-y-1.5">
                          <div className="text-[#EDF1EE] font-medium font-sans flex items-center gap-1.5">
                            <Table className="w-3.5 h-3.5 text-[#ADBAB9]" />
                            <span>Discovered Field Schema ({session.discoveredFields.length})</span>
                          </div>
                          <div className="overflow-x-auto">
                            <table className="w-full text-[13px] font-mono tracking-normal">
                              <thead>
                                <tr className="border-b border-[#3A4A50] text-[#ADBAB9] text-left">
                                  <th className="pb-1.5">Field</th>
                                  <th className="pb-1.5">Type</th>
                                  <th className="pb-1.5">Selector</th>
                                  <th className="pb-1.5">Confidence</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-[#3A4A50]/30">
                                {session.discoveredFields.map((f) => (
                                  <tr key={f.name}>
                                    <td className="py-1.5 text-[#EDF1EE] font-medium">{f.name}</td>
                                    <td className="py-1.5 text-[#ADBAB9]">{f.type}</td>
                                    <td className="py-1.5 text-[#ADBAB9] truncate max-w-[200px]" title={f.selector}>{f.selector || "auto"}</td>
                                    <td className="py-1.5 text-[#A7C4A2]">{Math.round((f.confidence || 0.95) * 100)}%</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {hasSampleData && session.endpoints[0]?.sampleResponse && (
                        <div className="space-y-1">
                          <div className="text-[#EDF1EE] font-medium font-sans flex items-center gap-1.5">
                            <FileCode className="w-3.5 h-3.5 text-[#ADBAB9]" />
                            <span>Sample Extracted Payload</span>
                          </div>
                          <pre className="p-2.5 rounded-md bg-[#151E23] border border-[#3A4A50]/40 overflow-x-auto text-[13px] font-mono tracking-normal leading-relaxed text-[#ADBAB9] max-h-40">
                            {JSON.stringify(session.endpoints[0].sampleResponse, null, 2)}
                          </pre>
                        </div>
                      )}

                      {step.details && !hasFieldData && !hasMetadata && !hasSampleData && (
                        <p className="text-[#ADBAB9] leading-relaxed font-sans">{step.details}</p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Inline Operator Approval Gate: Buttons 14px, weight 500 */}
          {session.status === "awaiting_approval" && onApprove && onReject && (
            <div className="p-3.5 rounded-lg bg-[#DDC38A]/10 border border-[#DDC38A]/30 text-[14px] space-y-2.5 mt-2">
              <div className="flex items-center gap-2 text-[#DDC38A] font-medium font-sans">
                <ShieldAlert className="w-4 h-4" />
                <span>Operator Approval Required</span>
              </div>
              <p className="text-[#EDF1EE] leading-relaxed font-sans">
                {session.approvalMessage || "The extraction agent has identified the required fields and proposes endpoints. Approve to deploy to live gateway."}
              </p>
              <div className="flex items-center gap-2.5 pt-1">
                <button
                  type="button"
                  onClick={onApprove}
                  className="px-3.5 py-1.5 rounded-md bg-[#C3D1B8] hover:bg-[#D5DFCD] text-[#17201C] font-sans text-[14px] font-medium transition-colors"
                >
                  Approve & Deploy
                </button>
                <button
                  type="button"
                  onClick={onReject}
                  className="px-3.5 py-1.5 rounded-md bg-[#202C32] hover:bg-[#2A3940] text-[#EDF1EE] border border-[#3A4A50]/60 font-sans text-[14px] font-medium transition-colors"
                >
                  Reject
                </button>
              </div>
            </div>
          )}

          {/* Inline Error & Retry */}
          {session.status === "failed" && session.errorMessage && (
            <div className="p-3.5 rounded-lg bg-[#E3A29E]/10 border border-[#E3A29E]/30 text-[14px] space-y-2 mt-2">
              <div className="flex items-center gap-2 text-[#E3A29E] font-medium font-sans">
                <AlertCircle className="w-4 h-4" />
                <span>Agent Execution Interrupted</span>
              </div>
              <p className="text-[#EDF1EE] leading-relaxed font-sans">{session.errorMessage}</p>
              {onRetry && (
                <button
                  type="button"
                  onClick={onRetry}
                  className="px-3.5 py-1.5 rounded-md bg-[#202C32] hover:bg-[#2A3940] text-[#EDF1EE] border border-[#3A4A50]/60 font-sans text-[14px] font-medium transition-colors"
                >
                  Retry Execution
                </button>
              )}
            </div>
          )}

          {/* Technical Logs Disclosure: IBM Plex Mono 13px */}
          {session.logs.length > 0 && (
            <div className="pt-2 border-t border-[#3A4A50]/40">
              <button
                type="button"
                onClick={() => setShowLogs(!showLogs)}
                className="flex items-center gap-1.5 text-[14px] font-medium font-sans text-[#ADBAB9] hover:text-[#EDF1EE] transition-colors"
              >
                <Terminal className="w-3.5 h-3.5" />
                <span>{showLogs ? "Hide technical logs" : `View technical logs (${session.logs.length})`}</span>
                {showLogs ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
              </button>

              {showLogs && (
                <div className="mt-2 p-3 rounded-lg bg-[#10171B] border border-[#3A4A50]/60 font-mono text-[13px] tracking-normal max-h-48 overflow-y-auto space-y-1.5">
                  {session.logs.map((log) => (
                    <div key={log.id} className="flex items-start gap-2.5 text-[#ADBAB9]">
                      <span className="text-[#ADBAB9]/50 shrink-0">{log.timestamp}</span>
                      <span className="text-[#C3D1B8]/70 shrink-0">[{log.source}]</span>
                      <span className={log.severity === "error" ? "text-[#E3A29E]" : log.severity === "warning" ? "text-[#DDC38A]" : "text-[#EDF1EE]"}>
                        {log.message}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
