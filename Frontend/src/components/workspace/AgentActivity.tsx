"use client";

import React from "react";
import { RunSession } from "@/lib/types";
import { InspectionCard } from "./InspectionCard";
import { RunStepCard } from "./RunStepCard";
import { FieldDiscoveryCard } from "./FieldDiscoveryCard";
import { WebsitePreview } from "./WebsitePreview";
import { LogStream } from "./LogStream";
import { ApprovalCard } from "./ApprovalCard";
import { RunErrorCard } from "./RunErrorCard";

interface AgentActivityProps {
  session: RunSession;
  onApprove?: () => void;
  onReject?: () => void;
  onRetry?: () => void;
  onEditPrompt?: () => void;
}

export function AgentActivity({
  session,
  onApprove,
  onReject,
  onRetry,
  onEditPrompt,
}: AgentActivityProps) {
  return (
    <div className="w-full space-y-4 font-sans">
      {/* Governance Approval Gate */}
      {session.status === "awaiting_approval" && onApprove && onReject && (
        <ApprovalCard
          message={session.approvalMessage}
          onApprove={onApprove}
          onReject={onReject}
        />
      )}

      {/* Error Recovery Card */}
      {session.status === "failed" && onRetry && onEditPrompt && (
        <RunErrorCard
          errorMessage={session.errorMessage}
          onRetry={onRetry}
          onEditPrompt={onEditPrompt}
        />
      )}

      {/* Target Page Inspection */}
      <InspectionCard
        metadata={session.pageMetadata}
        targetUrl={session.targetUrl}
      />

      {/* Synthesis Step Pipeline */}
      {session.steps.length > 0 && <RunStepCard steps={session.steps} />}

      {/* Discovered Schema Fields */}
      {session.discoveredFields.length > 0 && (
        <FieldDiscoveryCard fields={session.discoveredFields} />
      )}

      {/* Sandboxed Website Viewport Preview */}
      <WebsitePreview
        metadata={session.pageMetadata}
        targetUrl={session.targetUrl}
        discoveredFields={session.discoveredFields}
      />

      {/* Telemetry Logs Disclosure */}
      <LogStream logs={session.logs} />
    </div>
  );
}
