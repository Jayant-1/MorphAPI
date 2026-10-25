"use client";

import React, { useState, useEffect } from "react";
import { Plus, ExternalLink } from "lucide-react";
import { checkV2HealthDetails } from "@/lib/api-adapter";

interface ChatHeaderProps {
  onNewChat: () => void;
  isDemo?: boolean;
  showNavLinks?: boolean;
  onGoLanding?: () => void;
}

export function ChatHeader({
  onNewChat,
  isDemo = false,
  showNavLinks = false,
  onGoLanding,
}: ChatHeaderProps) {
  const [health, setHealth] = useState<{ connected: boolean; url: string; version?: string } | null>(null);

  const handleLogoClick = (e?: React.MouseEvent) => {
    if (e && (e.ctrlKey || e.metaKey || e.button === 1)) {
      window.open("/", "_blank");
      return;
    }
    if (onGoLanding) {
      onGoLanding();
    } else if (onNewChat) {
      onNewChat();
    }

    if (typeof window !== "undefined") {
      if (window.location.pathname !== "/") {
        window.location.href = "/";
      } else {
        if (window.location.hash || window.location.search) {
          window.history.pushState(null, "", "/");
        }
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    }
  };

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

  return (
    <>
      <header className="sticky top-0 z-30 w-full h-14 bg-[#10171B]/90 backdrop-blur-md border-b border-[#3A4A50] flex items-center justify-between px-4 sm:px-6 font-sans">
        {/* Brand Wordmark & V2 Status */}
        <div className="flex items-center gap-3.5">
          <span
            onClick={handleLogoClick}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                handleLogoClick();
              }
            }}
            role="button"
            tabIndex={0}
            title="MorphAPI - Return to landing page"
            className="font-syne font-bold text-[22px] leading-none tracking-[-0.02em] text-[#EDF1EE] cursor-pointer hover:opacity-80 transition-opacity select-none"
          >
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

        {/* Center: Landing Page Navigation Links */}
        {showNavLinks && (
          <nav className="hidden md:flex items-center gap-1 text-[13px] text-[#ADBAB9] font-sans">
            <a
              href="#how-it-works"
              className="px-3 py-1.5 rounded-md hover:text-[#EDF1EE] hover:bg-[#202C32] transition-colors"
            >
              How It Works
            </a>
            <a
              href="#failure-analysis"
              className="px-3 py-1.5 rounded-md hover:text-[#EDF1EE] hover:bg-[#202C32] transition-colors"
            >
              Failure Analysis
            </a>
            <a
              href="#architecture"
              className="px-3 py-1.5 rounded-md hover:text-[#EDF1EE] hover:bg-[#202C32] transition-colors"
            >
              Architecture
            </a>
            <a
              href="#protocols"
              className="px-3 py-1.5 rounded-md hover:text-[#EDF1EE] hover:bg-[#202C32] transition-colors"
            >
              Protocols
            </a>
            <a
              href="https://github.com/Jayant-1/MorphAPI"
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded-md hover:text-[#EDF1EE] hover:bg-[#202C32] transition-colors inline-flex items-center gap-1 text-[#C3D1B8]"
            >
              <span>GitHub</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </nav>
        )}

        {/* Actions: New Chat */}
        <div className="flex items-center gap-2">
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
    </>
  );
}
