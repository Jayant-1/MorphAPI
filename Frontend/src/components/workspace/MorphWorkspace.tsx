"use client";

import React, { useState } from "react";
import { RunSession, EndpointDefinition } from "@/lib/types";
import { RunContextHeader } from "./RunContextHeader";
import { ConversationTimeline } from "./ConversationTimeline";
import { EndpointCollection } from "./EndpointCollection";
import { ApiTestPanel } from "./ApiTestPanel";
import { HeroArtwork } from "@/components/hero/HeroArtwork";
import { Activity, Server, Play, ChevronRight } from "lucide-react";

interface MorphWorkspaceProps {
  session: RunSession;
  onStop: () => void;
  onNewRun: () => void;
  onBackToOverview: () => void;
  onEditPrompt: () => void;
  onSendFollowUp: (prompt: string) => void;
  onApprove?: () => void;
  onReject?: () => void;
  onRetry?: () => void;
}

export function MorphWorkspace({
  session,
  onStop,
  onNewRun,
  onBackToOverview,
  onEditPrompt,
  onSendFollowUp,
  onApprove,
  onReject,
  onRetry,
}: MorphWorkspaceProps) {
  // Currently selected endpoint for interactive testing
  const [selectedEndpoint, setSelectedEndpoint] = useState<EndpointDefinition | null>(
    session.endpoints[0] || null
  );

  // Tab state for mobile/tablet responsive layouts (<1200px)
  const [mobileTab, setMobileTab] = useState<"activity" | "endpoints" | "test">("activity");

  // Keep selected endpoint synchronized when new endpoints arrive
  React.useEffect(() => {
    if (session.endpoints.length > 0 && !selectedEndpoint) {
      setSelectedEndpoint(session.endpoints[0]);
    }
  }, [session.endpoints, selectedEndpoint]);

  // Focus management: move focus to workspace container on mount without stealing during streaming
  const workspaceRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    workspaceRef.current?.focus();
  }, []);

  const hasEndpoints = session.endpoints.length > 0;

  const handleSelectEndpointForTest = (ep: EndpointDefinition) => {
    setSelectedEndpoint(ep);
    setMobileTab("test");
  };

  return (
    <div
      ref={workspaceRef}
      tabIndex={-1}
      role="region"
      aria-label="MorphAPI Active Workspace"
      className="relative w-full min-h-[calc(100dvh-3.5rem)] flex flex-col bg-[#0B0D10] text-[#F4F5F7] font-sans focus:outline-hidden"
    >
      {/* Dimmed atmospheric background artwork */}
      <HeroArtwork dimmed />

      {/* Workspace Sticky Context Header */}
      <RunContextHeader
        session={session}
        onStop={onStop}
        onNewRun={onNewRun}
        onBackToOverview={onBackToOverview}
        onEditPrompt={onEditPrompt}
      />

      {/* Main Responsive Workspace Surface */}
      <div className="relative z-10 flex-1 w-full max-w-[1520px] mx-auto px-4 sm:px-6 py-6 flex flex-col">
        {/* Mobile/Tablet Tab Bar (<1200px) */}
        <div className="flex xl:hidden items-center justify-between gap-1 p-1 mb-5 rounded-xl bg-[#11151A] border border-white/10 font-mono text-xs">
          <button
            type="button"
            onClick={() => setMobileTab("activity")}
            className={`flex-1 py-2 px-3 rounded-lg flex items-center justify-center gap-1.5 transition-colors ${
              mobileTab === "activity"
                ? "bg-[#181D23] text-[#10B981] font-semibold shadow-xs"
                : "text-[#89929F] hover:text-[#F4F5F7]"
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Activity &amp; Chat</span>
          </button>

          <button
            type="button"
            onClick={() => setMobileTab("endpoints")}
            className={`flex-1 py-2 px-3 rounded-lg flex items-center justify-center gap-1.5 transition-colors ${
              mobileTab === "endpoints"
                ? "bg-[#181D23] text-[#10B981] font-semibold shadow-xs"
                : "text-[#89929F] hover:text-[#F4F5F7]"
            }`}
          >
            <Server className="w-3.5 h-3.5" />
            <span>Endpoints ({session.endpoints.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setMobileTab("test")}
            disabled={!hasEndpoints}
            className={`flex-1 py-2 px-3 rounded-lg flex items-center justify-center gap-1.5 transition-colors ${
              mobileTab === "test"
                ? "bg-[#10B981] text-[#070709] font-bold shadow-xs"
                : hasEndpoints
                ? "text-[#89929F] hover:text-[#F4F5F7]"
                : "text-[#4B5563] cursor-not-allowed"
            }`}
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>API Tester</span>
          </button>
        </div>

        {/* 
          Desktop Viewport Workbench:
          When endpoints are available, splits into:
          - Left column (42%): Conversation Timeline & Activity
          - Right column (58%): Endpoint Collection & Interactive API Tester
        */}
        <div className="w-full flex-1">
          {/* Narrow Single-Column Layout when endpoints are still generating (<1200px or no endpoints) */}
          {!hasEndpoints ? (
            <div className="w-full max-w-[920px] mx-auto">
              <ConversationTimeline
                session={session}
                onEditPrompt={onEditPrompt}
                onSendFollowUp={onSendFollowUp}
                onApprove={onApprove}
                onReject={onReject}
                onRetry={onRetry}
              />
            </div>
          ) : (
            <div className="w-full">
              {/* Desktop Dual-Pane Layout (>=1200px) */}
              <div className="hidden xl:grid xl:grid-cols-12 gap-8 items-start">
                {/* Left Pane: Conversation & Activity (col-span-5, ~42%) */}
                <div className="xl:col-span-5 sticky top-28 space-y-4 max-h-[calc(100vh-8rem)] overflow-y-auto pr-1">
                  <ConversationTimeline
                    session={session}
                    onEditPrompt={onEditPrompt}
                    onSendFollowUp={onSendFollowUp}
                    onApprove={onApprove}
                    onReject={onReject}
                    onRetry={onRetry}
                  />
                </div>

                {/* Right Pane: Endpoints & Interactive Tester (col-span-7, ~58%) */}
                <div className="xl:col-span-7 space-y-6">
                  {/* Endpoints Collection */}
                  <EndpointCollection
                    endpoints={session.endpoints}
                    selectedEndpointId={selectedEndpoint?.id}
                    onSelectTest={handleSelectEndpointForTest}
                  />

                  {/* Interactive Test Bench */}
                  {selectedEndpoint && (
                    <div className="pt-2">
                      <ApiTestPanel endpoint={selectedEndpoint} />
                    </div>
                  )}
                </div>
              </div>

              {/* Mobile / Tablet Tab Content (<1200px) */}
              <div className="xl:hidden w-full">
                {mobileTab === "activity" && (
                  <div className="w-full max-w-[920px] mx-auto">
                    <ConversationTimeline
                      session={session}
                      onEditPrompt={onEditPrompt}
                      onSendFollowUp={onSendFollowUp}
                      onApprove={onApprove}
                      onReject={onReject}
                      onRetry={onRetry}
                    />
                  </div>
                )}

                {mobileTab === "endpoints" && (
                  <div className="w-full max-w-[920px] mx-auto">
                    <EndpointCollection
                      endpoints={session.endpoints}
                      selectedEndpointId={selectedEndpoint?.id}
                      onSelectTest={handleSelectEndpointForTest}
                    />
                  </div>
                )}

                {mobileTab === "test" && selectedEndpoint && (
                  <div className="w-full max-w-[920px] mx-auto">
                    <ApiTestPanel endpoint={selectedEndpoint} />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
