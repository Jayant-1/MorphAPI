"use client";

import React, { useState } from "react";
import {
  Globe,
  ExternalLink,
  Square,
  RefreshCw,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Radio,
  Layers,
  Edit3,
  ChevronDown,
  ChevronUp,
  Info,
} from "lucide-react";
import { RunSession, RunStatus } from "@/lib/types";
import { extractHostname } from "@/lib/api-adapter";

interface RunContextHeaderProps {
  session: RunSession;
  onStop: () => void;
  onNewRun: () => void;
  onBackToOverview: () => void;
  onEditPrompt?: () => void;
}

export function RunContextHeader({
  session,
  onStop,
  onNewRun,
  onBackToOverview,
  onEditPrompt,
}: RunContextHeaderProps) {
  const hostname = extractHostname(session.targetUrl);
  const [showFullUrl, setShowFullUrl] = useState(false);
  const [isExpandedRequest, setIsExpandedRequest] = useState(false);

  const isRunning =
    session.status === "submitting" ||
    session.status === "connecting" ||
    session.status === "processing";

  return (
    <header className="w-full bg-[#151E23]/95 backdrop-blur-md border-b border-[#3A4A50] px-4 sm:px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 sticky top-14 z-30 font-sans">
      {/* Left: Back button + Hostname + Accessible Full URL Popover */}
      <div className="flex items-center gap-2.5 flex-wrap">
        <button
          type="button"
          onClick={onBackToOverview}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono text-[#ADBAB9] hover:text-[#EDF1EE] hover:bg-[#202C32] border border-[#3A4A50] transition-colors"
          title="Return to homepage overview"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Overview</span>
        </button>

        <div className="h-4 w-[1px] bg-[#3A4A50] hidden sm:block" />

        {/* Target Hostname pill with accessible full URL expansion */}
        <div className="relative flex items-center">
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-[#202C32] border border-[#3A4A50] text-xs font-mono">
            <Globe className="w-3.5 h-3.5 text-[#C3D1B8]" />
            <span className="font-semibold text-[#EDF1EE] truncate max-w-[130px] sm:max-w-[180px]">
              {hostname}
            </span>
            <button
              type="button"
              onClick={() => setShowFullUrl(!showFullUrl)}
              className="text-[#ADBAB9] hover:text-[#AEC8D0] p-0.5"
              title="Show complete target URL"
              aria-label="Show complete target URL"
            >
              <Info className="w-3 h-3" />
            </button>
            <a
              href={session.targetUrl}
              target="_blank"
              rel="noreferrer"
              className="text-[#ADBAB9] hover:text-[#EDF1EE]"
              title="Open original website in new tab"
            >
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>

          {/* Accessible Full URL Tooltip/Popover */}
          {showFullUrl && (
            <div className="absolute left-0 top-full mt-1.5 z-50 p-2.5 rounded-lg bg-[#202C32] border border-[#3A4A50] shadow-2xl text-[11px] font-mono text-[#EDF1EE] max-w-[340px] break-all">
              <div className="text-[10px] text-[#ADBAB9] uppercase mb-1">Full Target URL:</div>
              <div className="text-[#AEC8D0] select-all">{session.targetUrl}</div>
            </div>
          )}
        </div>

        {/* Run Identifier */}
        <div className="hidden md:flex items-center gap-1.5 text-xs font-mono text-[#ADBAB9]">
          <span>Run:</span>
          <code className="text-[#EDF1EE] bg-[#202C32] px-1.5 py-0.5 rounded-sm border border-[#3A4A50]">
            {session.id}
          </code>
        </div>
      </div>

      {/* Center: Compact Submitted Request Context with expansion */}
      <div className="hidden lg:flex items-center gap-2 flex-1 max-w-[500px] px-3 py-1 rounded-lg bg-[#202C32] border border-[#3A4A50] text-xs">
        <span className="font-mono text-[10px] text-[#ADBAB9] uppercase shrink-0">Request:</span>
        <span
          className={`text-[#EDF1EE] text-xs font-sans ${
            isExpandedRequest ? "max-w-none" : "truncate"
          }`}
          title={session.prompt}
        >
          {session.prompt}
        </span>
        {session.prompt.length > 40 && (
          <button
            type="button"
            onClick={() => setIsExpandedRequest(!isExpandedRequest)}
            className="text-[#C3D1B8] hover:underline font-mono text-[10px] shrink-0 ml-auto"
          >
            {isExpandedRequest ? "Less" : "Expand"}
          </button>
        )}
        {onEditPrompt && (
          <button
            type="button"
            onClick={onEditPrompt}
            className="text-[#ADBAB9] hover:text-[#C3D1B8] p-1 rounded-sm transition-colors shrink-0"
            title="Edit original request"
          >
            <Edit3 className="w-3 h-3" />
          </button>
        )}
      </div>

      {/* Right: Status Indicator + Action Controls */}
      <div className="flex items-center gap-2.5">
        {/* Live Status Badge */}
        <div
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium border ${
            session.status === "completed"
              ? "bg-[#A7C4A2]/15 text-[#A7C4A2] border-[#A7C4A2]/30"
              : isRunning
              ? "bg-[#DDC38A]/15 text-[#DDC38A] border-[#DDC38A]/30"
              : session.status === "awaiting_approval"
              ? "bg-[#AEC8D0]/15 text-[#AEC8D0] border-[#AEC8D0]/30"
              : session.status === "failed"
              ? "bg-[#E3A29E]/15 text-[#E3A29E] border-[#E3A29E]/30"
              : "bg-[#3A4A50]/20 text-[#ADBAB9] border-[#3A4A50]"
          }`}
          role="status"
          aria-live="polite"
        >
          {session.status === "completed" ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5 text-[#A7C4A2]" />
              <span>Ready ({session.endpoints.length} APIs)</span>
            </>
          ) : isRunning ? (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-[#DDC38A] animate-pulse" />
              <span>Streaming Activity</span>
            </>
          ) : session.status === "awaiting_approval" ? (
            <>
              <AlertTriangle className="w-3.5 h-3.5 text-[#AEC8D0]" />
              <span>Approval Required</span>
            </>
          ) : session.status === "failed" ? (
            <>
              <AlertCircle className="w-3.5 h-3.5 text-[#E3A29E]" />
              <span>Synthesis Failed</span>
            </>
          ) : (
            <>
              <Square className="w-3.5 h-3.5 text-[#ADBAB9]" />
              <span>Halted</span>
            </>
          )}
        </div>

        {/* Stop Action */}
        {isRunning && (
          <button
            type="button"
            onClick={onStop}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono bg-[#202C32] hover:bg-[#2A3940] border border-[#3A4A50] text-[#E3A29E] hover:border-[#E3A29E]/40 transition-colors"
            title="Stop current agent observation"
          >
            <Square className="w-3 h-3 fill-current" />
            <span className="hidden sm:inline">Stop</span>
          </button>
        )}

        {/* Edit / New Run Action */}
        <button
          type="button"
          onClick={onNewRun}
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono bg-[#202C32] hover:bg-[#2A3940] border border-[#3A4A50] text-[#EDF1EE] transition-colors"
          title="Start a new API creation session"
        >
          <RefreshCw className="w-3 h-3 text-[#C3D1B8]" />
          <span>New Run</span>
        </button>
      </div>
    </header>
  );
}
