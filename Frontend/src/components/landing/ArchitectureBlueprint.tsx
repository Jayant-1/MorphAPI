"use client";

import React from "react";
import { Cpu, Terminal, ShieldCheck, GitBranch, ArrowRight, Zap, Network } from "lucide-react";

export function ArchitectureBlueprint() {
  const modules = [
    {
      index: "01",
      title: "FAST-PATH DETERMINISTIC EXTRACTION",
      badge: "< 400MS // MODEL-FREE",
      description:
        "Standard production traffic does not invoke an LLM. Playwright evaluates active CSS/XPath selector maps directly on rendered headless Chromium DOM. 100% deterministic, zero hallucination risk, and zero inference cost.",
      specs: ["Latency: <400ms", "Cost: $0.00 / req", "Engine: Chromium AST", "Validation: Pydantic v2"],
      icon: Zap,
      accent: "#10B981",
    },
    {
      index: "02",
      title: "NVIDIA NIM SPATIAL & VISUAL INFERENCE",
      badge: "LLAMA-3.1-70B // SELECTOR SYNTHESIS",
      description:
        "When DOM mutation causes 0 matches, the sanitized DOM tree is passed to NVIDIA NIM. The model infers visual-spatial coordinates and candidate CSS selectors based on semantic content and structural container patterns.",
      specs: ["Model: Llama 3.1 70B", "DOM Sanitizer: 42kb AST", "Hypothesis Rate: 99.4%", "Inference: GPU NIM"],
      icon: Cpu,
      accent: "#F59E0B",
    },
    {
      index: "03",
      title: "LANGGRAPH AGENTIC HEALING LOOPS",
      badge: "STATE MACHINE // HUMAN APPROVAL GATE",
      description:
        "A cyclic graph manages the self-healing workflow: detect failure → isolate DOM → propose candidates → verify in Playwright → compute AST diff → hold at human review gate or auto-promote per endpoint policy.",
      specs: ["Stages: 6 Steps", "Diff Engine: Unified AST", "Approval: Configurable Gate", "Persistence: SQLite Async"],
      icon: GitBranch,
      accent: "#38BDF8",
    },
    {
      index: "04",
      title: "SSRF ENCLAVE & SCOPE FIREWALL",
      badge: "RFC 1918 FILTER // CLOUD METADATA QUARANTINE",
      description:
        "Browser workers operate within a locked network jail. DNS resolution enforces private subnet blocking (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, AWS 169.254.169.254) with strict wildcard scope matching.",
      specs: ["Subnets: RFC 1918 Block", "DNS: Pre-flight Resolve", "Scope: Regex Wildcards", "Headers: Sanitized"],
      icon: ShieldCheck,
      accent: "#A78BFA",
    },
  ];

  return (
    <section id="architecture" className="py-16 md:py-24 border-b border-[#1A1A20] bg-[#070709] font-mono text-xs">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-10">
        {/* Section Index Header */}
        <div className="flex items-center gap-3 text-[11px] uppercase tracking-widest text-[#71717A] mb-4">
          <span className="text-[#10B981] font-bold">[03 {"//"} ARCHITECTURE_AST]</span>
          <span className="text-[#3F3F46]">{"///"}</span>
          <span>DUAL_ENGINE_PIPELINE</span>
          <span className="text-[#3F3F46]">{"///"}</span>
          <span>SYSTEM_SPECIFICATION</span>
        </div>

        <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-[-0.03em] text-[#FAFAFA] leading-tight uppercase font-sans mb-4">
          THE DUAL-ENGINE GATEWAY PIPELINE.
        </h2>

        <p className="max-w-3xl text-sm sm:text-base text-[#A1A1AA] font-normal leading-relaxed mb-12 font-sans">
          Engineered as a hybrid runtime: the speed and determinism of raw headless browser evaluation paired with the spatial reasoning of high-parameter generative AI when layouts break.
        </p>

        {/* 4-Module Architectural Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {modules.map((mod) => {
            const Icon = mod.icon;
            return (
              <div
                key={mod.index}
                className="border border-[#22222A] bg-[#0D0D10] p-6 rounded-sm space-y-4 hover:border-[#33333F] transition-colors shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] flex flex-col justify-between"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between border-b border-[#1A1A22] pb-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-6 h-6 rounded-xs bg-[#16161C] border border-[#272730] flex items-center justify-center">
                        <Icon className="w-3.5 h-3.5" style={{ color: mod.accent }} />
                      </div>
                      <span className="text-[#E4E4E7] font-bold tracking-wider text-xs">
                        MODULE {mod.index} {"//"} {mod.title}
                      </span>
                    </div>
                  </div>

                  <span
                    className="inline-block text-[10px] font-bold px-2 py-0.5 rounded-xs"
                    style={{
                      backgroundColor: `${mod.accent}15`,
                      color: mod.accent,
                      border: `1px solid ${mod.accent}30`,
                    }}
                  >
                    {mod.badge}
                  </span>

                  <p className="text-[12px] text-[#A1A1AA] leading-relaxed font-sans">
                    {mod.description}
                  </p>
                </div>

                {/* Micro Technical Specs */}
                <div className="pt-4 border-t border-[#181820] grid grid-cols-2 gap-2 text-[10px] text-[#71717A]">
                  {mod.specs.map((s, i) => (
                    <div key={i} className="flex items-center gap-1.5">
                      <span className="w-1 h-1 rounded-full bg-[#3F3F46]" />
                      <span className="text-[#D4D4D8]">{s}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
