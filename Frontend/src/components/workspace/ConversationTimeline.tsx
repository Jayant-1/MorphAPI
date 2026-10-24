"use client";

import React from "react";
import { User, Bot, Globe, ExternalLink, Edit3, CheckCircle2 } from "lucide-react";
import { RunSession } from "@/lib/types";
import { AgentActivity } from "./AgentActivity";
import { FollowUpComposer } from "./FollowUpComposer";

interface ConversationTimelineProps {
  session: RunSession;
  onEditPrompt: () => void;
  onSendFollowUp: (prompt: string) => void;
  onApprove?: () => void;
  onReject?: () => void;
  onRetry?: () => void;
}

export function ConversationTimeline({
  session,
  onEditPrompt,
  onSendFollowUp,
  onApprove,
  onReject,
  onRetry,
}: ConversationTimelineProps) {
  const isRunning =
    session.status === "submitting" ||
    session.status === "connecting" ||
    session.status === "processing";

  return (
    <div className="w-full flex flex-col gap-4 font-sans text-xs">
      {/* 
        Original Submitted Request (User Message Surface)
        Keeps original prompt visible at top as context
      */}
      <div className="w-full rounded-2xl bg-[#11151A] border border-white/10 p-4 shadow-sm flex flex-col gap-2.5">
        <div className="flex items-center justify-between text-[#89929F]">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-md bg-[#181D23] border border-white/10 flex items-center justify-center text-[#F4F5F7]">
              <User className="w-3 h-3" />
            </div>
            <span className="font-semibold text-[#F4F5F7] text-xs">Extraction Request</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-[#6A7382]">
              {new Date(session.createdAt).toLocaleTimeString()}
            </span>
            <button
              type="button"
              onClick={onEditPrompt}
              className="text-[#89929F] hover:text-[#10B981] p-1 rounded-sm transition-colors"
              title="Edit original request"
            >
              <Edit3 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* User Prompt Text */}
        <p className="text-sm text-[#F4F5F7] leading-relaxed font-normal whitespace-pre-wrap">
          {session.prompt}
        </p>

        {/* Source Target URL Anchor */}
        <div className="pt-2 border-t border-white/5 flex items-center gap-1.5 text-[11px] font-mono text-[#89929F]">
          <Globe className="w-3 h-3 text-[#10B981]" />
          <span className="truncate max-w-[420px] text-[#A9B0BA]">{session.targetUrl}</span>
        </div>
      </div>

      {/* Assistant Acknowledgement & AG-UI Stream */}
      <div className="w-full flex flex-col gap-3">
        <div className="flex items-center gap-2 text-[#A9B0BA] px-1">
          <div className="w-5 h-5 rounded-md bg-[#10B981]/15 border border-[#10B981]/30 flex items-center justify-center text-[#10B981]">
            <Bot className="w-3 h-3" />
          </div>
          <span className="font-semibold text-xs text-[#F4F5F7]">MorphAPI Agent</span>
          <span className="font-mono text-[10px] text-[#89929F]">
            {isRunning ? "Inspecting live DOM..." : "Synthesis complete"}
          </span>
        </div>

        {/* Assistant Intro Message */}
        <div className="p-3.5 rounded-xl bg-[#11151A]/80 border border-white/5 text-[#A9B0BA] leading-relaxed">
          {session.status === "completed" ? (
            <div className="flex items-center gap-2 text-[#C3D1B8] font-medium font-sans flex-wrap">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span className="font-syne font-semibold text-[15px] tracking-[-0.01em] text-[#EDF1EE]">
                Your API is ready.
              </span>
              <span className="font-sans text-[14px] text-[#ADBAB9]">
                Review the generated endpoints on the right and run a live test.
              </span>
            </div>
          ) : session.status === "awaiting_approval" ? (
            <span>
              I have inspected the target website. Operator review is required to confirm schema compliance before activating the API.
            </span>
          ) : session.status === "failed" ? (
            <span className="text-[#F87171]">
              The target website could not be mapped to the requested fields. Review the technical logs and error details below.
            </span>
          ) : (
            <span>
              I&apos;m inspecting the page and identifying the fields you requested. Testing candidate DOM selectors in Playwright.
            </span>
          )}
        </div>

        {/* Structured AG-UI Activity Cards */}
        <AgentActivity
          session={session}
          onApprove={onApprove}
          onReject={onReject}
          onRetry={onRetry}
          onEditPrompt={onEditPrompt}
        />
      </div>

      {/* Follow-up Composer at Bottom */}
      <FollowUpComposer
        isProcessing={isRunning}
        onSendFollowUp={onSendFollowUp}
      />
    </div>
  );
}
