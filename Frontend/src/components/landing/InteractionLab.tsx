"use client";

import React, { useState } from "react";
import { AlertOctagon, CheckCircle2, ShieldAlert, Cpu, ArrowRight } from "lucide-react";

export function InteractionLab() {
  const [selectedCase, setSelectedCase] = useState<"legacy" | "morph">("morph");

  return (
    <section id="failure-analysis" className="py-16 md:py-24 border-b border-[#1A1A20] bg-[#09090C] font-mono text-xs text-[#A1A1AA]">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-10">
        {/* Section Index Header */}
        <div className="flex items-center gap-3 text-[11px] uppercase tracking-widest text-[#71717A] mb-4">
          <span className="text-[#10B981] font-bold">[02 {"//"} FAILURE_ANALYSIS_LAB]</span>
          <span className="text-[#3F3F46]">{"///"}</span>
          <span>THE_2AM_OUTAGE_PROBLEM</span>
          <span className="text-[#3F3F46]">{"///"}</span>
          <span>AUTONOMOUS_RESILIENCE</span>
        </div>

        <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-[-0.03em] text-[#FAFAFA] leading-tight uppercase font-sans mb-6">
          THE ANATOMY OF A WEB-TO-API FRACTURE.
        </h2>

        <p className="max-w-3xl text-sm sm:text-base text-[#A1A1AA] font-normal leading-relaxed mb-10 font-sans">
          Every web scraper eventually fails because websites are living, unstable documents. When frontend teams redesign or randomize CSS hash names, hardcoded selectors die—taking production pipelines with them. MorphAPI turns fragile scrapers into self-healing, type-safe API infrastructure.
        </p>

        {/* High-Contrast Comparative Chassis */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Card A: The Traditional 2:00 AM Failure */}
          <div className="border border-[#261E1E] bg-[#0E0A0A] p-6 rounded-sm space-y-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
            <div className="flex items-center justify-between border-b border-[#281818] pb-3">
              <div className="flex items-center gap-2 text-[#EF4444] font-bold uppercase tracking-wider text-xs">
                <AlertOctagon className="w-4 h-4" />
                <span>TRADITIONAL SCRAPER {"//"} FRAGILE</span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded-xs bg-[#450A0A] text-[#F87171]">
                STATUS: 502 CRASH
              </span>
            </div>

            <div className="space-y-2 text-[11px]">
              <div className="p-2.5 rounded-xs bg-[#160D0D] border border-[#2F1515] font-mono text-[#FCA5A5]">
                <code>$ curl https://api.legacy-scraper.internal/v1/pricing</code>
                <div className="mt-1 text-[#EF4444] font-bold">
                  HTTP/1.1 502 Bad Gateway: Selector &apos;.price-tag-v1&apos; matched 0 DOM nodes.
                </div>
              </div>

              <ul className="space-y-2 text-[#A1A1AA] pt-2">
                <li className="flex items-start gap-2">
                  <span className="text-[#EF4444] font-bold">[-]</span>
                  <span>Hardcoded CSS selectors break permanently on frontend class renames.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-[#EF4444] font-bold">[-]</span>
                  <span>Silent data drops corrupt downstream databases until an on-call engineer wakes up.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-[#EF4444] font-bold">[-]</span>
                  <span>Manual selector repair requires hours of DevTools inspection and redeploy cycles.</span>
                </li>
              </ul>
            </div>
          </div>

          {/* Card B: The MorphAPI Self-Healing Engine */}
          <div className="border border-[#1E2922] bg-[#0A0E0B] p-6 rounded-sm space-y-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
            <div className="flex items-center justify-between border-b border-[#18281F] pb-3">
              <div className="flex items-center gap-2 text-[#10B981] font-bold uppercase tracking-wider text-xs">
                <CheckCircle2 className="w-4 h-4" />
                <span>MORPHAPI GATEWAY {"//"} AUTONOMOUS</span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded-xs bg-[#064E3B] text-[#A7F3D0]">
                STATUS: 200 OK (SELF-HEALED)
              </span>
            </div>

            <div className="space-y-2 text-[11px]">
              <div className="p-2.5 rounded-xs bg-[#0D1812] border border-[#153823] font-mono text-[#86EFAC]">
                <code>$ curl https://gateway.morphapi.local/v1/extract/pricing</code>
                <div className="mt-1 text-[#10B981] font-bold">
                  HTTP/1.1 200 OK: Playwright AST extraction verified. Version promoted to v2.
                </div>
              </div>

              <ul className="space-y-2 text-[#A1A1AA] pt-2">
                <li className="flex items-start gap-2">
                  <span className="text-[#10B981] font-bold">[+]</span>
                  <span>Fast-path deterministic execution (&lt;400ms) with zero LLM token cost during normal traffic.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-[#10B981] font-bold">[+]</span>
                  <span>LangGraph state machine isolates mutated DOM nodes and hypothesizes resilient selectors.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-[#10B981] font-bold">[+]</span>
                  <span>Unified AST diff inspection with human-in-the-loop review or autonomous auto-promotion.</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
