"use client";

import React, { useState, useEffect } from "react";
import { Plus, Database, X, ExternalLink, Terminal } from "lucide-react";
import { checkV2HealthDetails, listStoredEndpoints, getV2BaseUrl } from "@/lib/api-adapter";

interface ChatHeaderProps {
  onNewChat: () => void;
  isDemo?: boolean;
}

export function ChatHeader({ onNewChat, isDemo = false }: ChatHeaderProps) {
  const [health, setHealth] = useState<{ connected: boolean; url: string; version?: string } | null>(null);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [storedEndpoints, setStoredEndpoints] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    let mounted = true;
    const pollHealth = async () => {
      const h = await checkV2HealthDetails();
      if (mounted) setHealth(h);
    };

    pollHealth();
    const interval = setInterval(pollHealth, 10000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const openHistory = async () => {
    setShowHistoryModal(true);
    setLoadingHistory(true);
    try {
      const endpoints = await listStoredEndpoints();
      setStoredEndpoints(endpoints);
    } catch {
      setStoredEndpoints([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  return (
    <>
      <header className="sticky top-0 z-30 w-full h-14 bg-[#10171B]/90 backdrop-blur-md border-b border-[#3A4A50] flex items-center justify-between px-4 sm:px-6 font-sans">
        {/* Brand Wordmark & V2 Status */}
        <div className="flex items-center gap-3.5">
          <span className="font-syne font-bold text-[22px] leading-none tracking-[-0.02em] text-[#EDF1EE]">
            MorphAPI
          </span>

          {/* V2 Live Health Badge */}
          {health && (
            <div
              className={`hidden sm:inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[12px] font-mono border ${
                health.connected
                  ? "bg-[#A7C4A2]/10 text-[#A7C4A2] border-[#A7C4A2]/30"
                  : "bg-[#DDC38A]/10 text-[#DDC38A] border-[#DDC38A]/30"
              }`}
              title={`Gateway: ${health.url} (${health.connected ? "Operational" : "Offline"})`}
            >
              <div
                className={`w-1.5 h-1.5 rounded-full ${
                  health.connected ? "bg-[#A7C4A2] animate-pulse" : "bg-[#DDC38A]"
                }`}
              />
              <span>{health.connected ? `V2 Gateway :8001` : `V2 Offline :8001`}</span>
            </div>
          )}
        </div>

        {/* Actions: Stored Endpoints & New Chat */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={openHistory}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[13px] font-medium font-sans text-[#ADBAB9] hover:text-[#EDF1EE] hover:bg-[#202C32] border border-transparent hover:border-[#3A4A50] transition-colors"
            title="View saved endpoints in database"
          >
            <Database className="w-3.5 h-3.5 text-[#ADBAB9]" />
            <span>Stored APIs</span>
          </button>

          <button
            type="button"
            onClick={onNewChat}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[14px] font-medium font-sans text-[#EDF1EE] bg-[#202C32] hover:bg-[#2A3940] border border-[#3A4A50] transition-colors focus:outline-hidden focus:ring-1 focus:ring-[#AEC8D0]"
            title="Start new conversation"
          >
            <Plus className="w-3.5 h-3.5 text-[#ADBAB9]" />
            <span>New chat</span>
          </button>
        </div>
      </header>

      {/* Stored Endpoints Slide-over / Modal */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-2xl bg-[#151E23] border border-[#3A4A50] rounded-2xl shadow-2xl flex flex-col max-h-[80vh] overflow-hidden">
            <div className="px-5 py-4 border-b border-[#3A4A50] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-[#AEC8D0]" />
                <h3 className="font-syne font-semibold text-[17px] text-[#EDF1EE]">
                  Stored V2 Endpoints ({storedEndpoints.length})
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowHistoryModal(false)}
                className="p-1 rounded-md text-[#ADBAB9] hover:text-[#EDF1EE] hover:bg-[#202C32] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-3 font-sans text-[13px]">
              {loadingHistory ? (
                <div className="py-8 text-center text-[#ADBAB9]">Loading stored endpoints...</div>
              ) : storedEndpoints.length === 0 ? (
                <div className="py-8 text-center text-[#ADBAB9] space-y-1">
                  <p>No endpoints stored yet.</p>
                  <p className="text-[12px] text-[#ADBAB9]/70">
                    Synthesize an API from any website to persist it in the local SQLite repository.
                  </p>
                </div>
              ) : (
                storedEndpoints.map((ep) => {
                  const queryUrl = `${getV2BaseUrl()}/v2/api/${ep.user_id}/${ep.slug}`;
                  const docsUrl = `${queryUrl}/docs`;
                  const openapiUrl = `${queryUrl}/openapi.json`;

                  return (
                    <div
                      key={ep.endpoint_id}
                      className="p-3.5 rounded-xl bg-[#10171B] border border-[#3A4A50] space-y-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="font-medium text-[#EDF1EE] text-[14px]">
                          {ep.api_name || ep.slug}
                        </div>
                        <span className="font-mono text-[12px] text-[#AEC8D0] bg-[#AEC8D0]/10 px-2 py-0.5 rounded">
                          /v2/api/{ep.user_id}/{ep.slug}
                        </span>
                      </div>
                      <div className="text-[12px] text-[#ADBAB9] truncate">
                        Target: <span className="text-[#EDF1EE]">{ep.target_url}</span>
                      </div>
                      <div className="flex items-center gap-3 pt-1 text-[12px] font-sans">
                        <a
                          href={docsUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-[#C3D1B8] hover:underline"
                        >
                          <ExternalLink className="w-3 h-3" />
                          <span>Swagger Docs</span>
                        </a>
                        <a
                          href={openapiUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-[#AEC8D0] hover:underline"
                        >
                          <Terminal className="w-3 h-3" />
                          <span>OpenAPI 3.1 Spec</span>
                        </a>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <div className="px-5 py-3 border-t border-[#3A4A50] bg-[#10171B]/50 flex justify-end">
              <button
                type="button"
                onClick={() => setShowHistoryModal(false)}
                className="px-4 py-1.5 rounded-lg bg-[#202C32] hover:bg-[#2A3940] text-[#EDF1EE] border border-[#3A4A50] text-[13px] font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
