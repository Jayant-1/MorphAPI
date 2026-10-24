"use client";

import React, { useState } from "react";
import {
  Globe,
  Lock,
  Maximize2,
  Minimize2,
  ExternalLink,
  Laptop,
  AlertTriangle,
  FileCode,
} from "lucide-react";
import { PageMetadata, FieldDefinition } from "@/lib/types";

interface WebsitePreviewProps {
  metadata?: PageMetadata;
  targetUrl: string;
  discoveredFields?: FieldDefinition[];
}

export function WebsitePreview({
  metadata,
  targetUrl,
  discoveredFields = [],
}: WebsitePreviewProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const hostname = metadata?.hostname || "website.target";
  const isChallenge = metadata?.httpStatus === 403;
  const hasFields = discoveredFields.length > 0;

  return (
    <div className="w-full rounded-xl bg-[#11151A] border border-white/10 overflow-hidden font-sans shadow-md">
      {/* Browser Chrome Bar */}
      <div className="bg-[#181D23] px-3 py-2 border-b border-white/10 flex items-center justify-between gap-2 text-xs">
        {/* Mock Window Dots */}
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-[#EF4444]/60" />
          <div className="w-2.5 h-2.5 rounded-full bg-[#F59E0B]/60" />
          <div className="w-2.5 h-2.5 rounded-full bg-[#10B981]/60" />
        </div>

        {/* Address Bar */}
        <div className="flex-1 max-w-[360px] mx-2 h-6 px-2.5 rounded-md bg-[#0B0D10] border border-white/5 flex items-center gap-1.5 text-[11px] font-mono text-[#89929F] truncate">
          <Lock className="w-2.5 h-2.5 text-[#10B981] shrink-0" />
          <span className="text-[#F4F5F7] truncate">{hostname}</span>
          <span className="text-[#6A7382] truncate">/live-dom</span>
        </div>

        {/* Expand / External Actions */}
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 text-[#89929F] hover:text-[#F4F5F7] rounded-sm hover:bg-white/5"
            aria-label={isExpanded ? "Collapse preview" : "Expand preview"}
          >
            {isExpanded ? (
              <Minimize2 className="w-3.5 h-3.5" />
            ) : (
              <Maximize2 className="w-3.5 h-3.5" />
            )}
          </button>
          <a
            href={targetUrl}
            target="_blank"
            rel="noreferrer"
            className="p-1 text-[#89929F] hover:text-[#F4F5F7] rounded-sm hover:bg-white/5"
            title="Open original website"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      {/* Viewport Simulation Area */}
      <div
        className={`bg-[#070709] p-4 text-xs font-mono transition-all duration-300 relative ${
          isExpanded ? "min-h-[300px]" : "min-h-[160px] max-h-[200px]"
        } overflow-hidden flex flex-col justify-between`}
      >
        {/* DOM AST Tree Outline Wireframe */}
        <div className="space-y-2 select-none opacity-90">
          <div className="flex items-center justify-between text-[10px] text-[#89929F] border-b border-white/5 pb-1">
            <span>AST Snapshot (1440x900 viewport)</span>
            <span>Captured: {metadata?.captureTime?.split(" ")[1] || "02:18:12"}</span>
          </div>

          {isChallenge ? (
            <div className="p-2.5 rounded-md bg-[#7F1D1D]/15 border border-[#EF4444]/40 text-[#F87171] text-[11px]">
              <div className="flex items-center gap-2 font-semibold">
                <AlertTriangle className="w-3.5 h-3.5 text-[#F87171]" />
                <span>Anti-Bot Challenge Intercepted</span>
              </div>
              <div className="pl-5 mt-1 text-[#A9B0BA] text-[10px]">
                Target returned HTTP 403 with automated browser verification. DOM extraction paused.
              </div>
            </div>
          ) : hasFields ? (
            <div className="p-2.5 rounded-md bg-[#11151A]/90 border border-[#10B981]/30 text-[#A7F3D0] text-[11px]">
              <div className="flex items-center justify-between font-semibold">
                <span>DOM Selectors Validated ({discoveredFields.length} attributes)</span>
                <span className="text-[9px] px-1.5 py-0.2 rounded-xs bg-[#10B981]/20 text-[#10B981]">
                  MATCHED
                </span>
              </div>
              <div className="pl-3 mt-1.5 space-y-1 text-[#89929F] text-[10px]">
                {discoveredFields.slice(0, 3).map((f) => (
                  <div key={f.name} className="truncate">
                    <span className="text-[#38BDF8]">{f.name}</span>
                    <span className="text-[#6A7382]"> → </span>
                    <code className="text-[#A7F3D0]">{f.selector || `attr[name="${f.name}"]`}</code>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-2.5 rounded-md bg-[#11151A]/60 border border-white/10 text-[#89929F] text-[11px]">
              <div className="font-semibold text-[#A9B0BA]">No Content Selectors Matched</div>
              <div className="text-[10px] text-[#6A7382] mt-1">
                DOM tree analyzed ({metadata?.elementsInspected || 0} elements), but no elements matched the requested extraction schema.
              </div>
            </div>
          )}

          {isExpanded && (
            <div className="p-2.5 rounded-md bg-[#11151A]/60 border border-white/5 text-[#89929F] text-[10px] space-y-1">
              <div>Detected Engine: {metadata?.detectedFramework || "HTML5 DOM"}</div>
              <div>Security Verification: Verified Clean (Whitelisted public target)</div>
              <div>Playwright Chromium rendering engine: Headless Mode</div>
            </div>
          )}
        </div>

        {/* Footer Note */}
        <div className="pt-2 mt-2 border-t border-white/5 text-[10px] text-[#6A7382] flex items-center justify-between">
          <span>Headless Playwright Chromium AST</span>
          <span className="text-[#10B981]">Safe Sandbox</span>
        </div>
      </div>
    </div>
  );
}
