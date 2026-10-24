"use client";

import React from "react";
import { Globe, ExternalLink, ShieldCheck, CheckCircle2, AlertTriangle, AlertCircle } from "lucide-react";
import { PageMetadata } from "@/lib/types";

interface InspectionCardProps {
  metadata?: PageMetadata;
  targetUrl: string;
}

export function InspectionCard({ metadata, targetUrl }: InspectionCardProps) {
  const hostname = metadata?.hostname || "website.target";
  const httpStatus = metadata?.httpStatus ?? 200;
  const isHttpOk = httpStatus >= 200 && httpStatus < 300;
  const isChallenge = httpStatus === 403;
  const statusLabel = isHttpOk
    ? `${httpStatus} OK`
    : isChallenge
    ? `${httpStatus} Challenge`
    : `${httpStatus} Error`;

  return (
    <div className="w-full rounded-xl bg-[#202C32] border border-[#3A4A50] p-4 font-sans text-xs shadow-md">
      <div className="flex items-center justify-between pb-2.5 mb-3 border-b border-[#3A4A50]">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-[#C3D1B8]/15 border border-[#C3D1B8]/30 flex items-center justify-center text-[#C3D1B8]">
            <Globe className="w-3.5 h-3.5" />
          </div>
          <div>
            <h4 className="font-semibold text-[#EDF1EE] text-xs">Target Inspection</h4>
            <p className="text-[11px] font-mono text-[#ADBAB9] truncate max-w-[240px]">
              {hostname}
            </p>
          </div>
        </div>

        <a
          href={targetUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#151E23] hover:bg-[#2A3940] border border-[#3A4A50] text-[11px] font-mono text-[#ADBAB9] hover:text-[#EDF1EE] transition-colors"
        >
          <span>Open Source</span>
          <ExternalLink className="w-3 h-3 text-[#ADBAB9]" />
        </a>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 font-mono text-[11px]">
        <div className="p-2 rounded-lg bg-[#151E23] border border-[#3A4A50]">
          <div className="text-[#ADBAB9] text-[10px] uppercase">HTTP Status</div>
          <div
            className={`font-semibold flex items-center gap-1 mt-0.5 ${
              isHttpOk
                ? "text-[#A7C4A2]"
                : isChallenge
                ? "text-[#DDC38A]"
                : "text-[#E3A29E]"
            }`}
          >
            {isHttpOk ? (
              <CheckCircle2 className="w-3 h-3 text-[#A7C4A2]" />
            ) : isChallenge ? (
              <AlertTriangle className="w-3 h-3 text-[#DDC38A]" />
            ) : (
              <AlertCircle className="w-3 h-3 text-[#E3A29E]" />
            )}
            <span>{statusLabel}</span>
          </div>
        </div>

        <div className="p-2 rounded-lg bg-[#151E23] border border-[#3A4A50]">
          <div className="text-[#ADBAB9] text-[10px] uppercase">DOM Elements</div>
          <div className="text-[#EDF1EE] font-semibold mt-0.5">
            {metadata?.elementsInspected !== undefined
              ? `${metadata.elementsInspected} Analyzed`
              : "Scanning..."}
          </div>
        </div>

        <div className="col-span-2 sm:col-span-1 p-2 rounded-lg bg-[#151E23] border border-[#3A4A50]">
          <div className="text-[#ADBAB9] text-[10px] uppercase">Engine</div>
          <div className="text-[#AEC8D0] font-semibold flex items-center gap-1 mt-0.5 truncate">
            <ShieldCheck className="w-3 h-3" />
            <span>Playwright AST</span>
          </div>
        </div>
      </div>
    </div>
  );
}
