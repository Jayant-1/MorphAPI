"use client";

import React, { useState } from "react";
import {
  Globe,
  CheckCircle2,
  Cpu,
  ArrowRight,
  ShieldCheck,
  Zap,
  Terminal,
  RefreshCw,
  GitBranch,
} from "lucide-react";

export function InteractivePipeline() {
  const [activeStep, setActiveStep] = useState<1 | 2 | 3>(1);

  const steps = [
    {
      id: 1,
      title: "1. Inspect & Extract",
      subtitle: "Headless Chromium rendered in isolated sandboxes",
      badge: "PLAYWRIGHT AST",
      badgeColor: "emerald",
      icon: Globe,
    },
    {
      id: 2,
      title: "2. Deterministic Validation",
      subtitle: "Strict Pydantic v2 type checking — no AI hallucinations",
      badge: "PYDANTIC V2",
      badgeColor: "cyan",
      icon: ShieldCheck,
    },
    {
      id: 3,
      title: "3. Autonomous Self-Healing",
      subtitle: "LangGraph + NVIDIA NIM repairs selectors when layouts break",
      badge: "LANGGRAPH + NIM",
      badgeColor: "amber",
      icon: RefreshCw,
    },
  ];

  return (
    <section id="how-it-works" className="py-16 md:py-24 border-b border-[#1A1A20] bg-[#09090C] font-sans">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-2xl mx-auto mb-12 space-y-3">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            How MorphAPI Works
          </h2>
          <p className="text-sm sm:text-base text-[#A1A1AA]">
            Click through the three stages of the deterministic extraction pipeline.
          </p>
        </div>

        {/* Interactive Step Selector */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-8">
          {steps.map((s) => {
            const Icon = s.icon;
            const isSelected = activeStep === s.id;
            return (
              <button
                key={s.id}
                onClick={() => setActiveStep(s.id as 1 | 2 | 3)}
                className={`p-4 rounded-sm border text-left transition-all ${
                  isSelected
                    ? "bg-[#14141A] border-[#3F3F4E] shadow-md"
                    : "bg-[#0C0C0F] border-[#1E1E26] hover:border-[#2E2E38] opacity-70 hover:opacity-100"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2.5">
                    <div
                      className={`w-7 h-7 rounded-sm flex items-center justify-center ${
                        isSelected ? "bg-[#10B981]/20 text-[#10B981]" : "bg-[#181820] text-[#71717A]"
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className="font-bold text-sm text-white">{s.title}</span>
                  </div>
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-xs bg-[#1E1E26] text-[#A1A1AA]">
                    {s.badge}
                  </span>
                </div>
                <p className="text-xs text-[#71717A] pl-9.5">{s.subtitle}</p>
              </button>
            );
          })}
        </div>

        {/* Interactive Dynamic Display Panel */}
        <div className="border border-[#22222A] bg-[#0C0C0F] rounded-sm p-6 lg:p-8 font-mono text-xs">
          {activeStep === 1 && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
              <div className="lg:col-span-5 space-y-4 font-sans">
                <span className="text-xs font-mono text-[#10B981] font-semibold uppercase">
                  Stage 01 // Headless Browser Inspection
                </span>
                <h3 className="text-2xl font-bold text-white">
                  Real Chromium Rendering. Zero Scraping Guesswork.
                </h3>
                <p className="text-sm text-[#A1A1AA] leading-relaxed">
                  MorphAPI navigates to target URLs using isolated Playwright workers. It renders dynamic JavaScript, client-side hydration, and dynamic DOM trees before testing candidate selectors.
                </p>
                <div className="grid grid-cols-2 gap-3 pt-2 font-mono text-xs">
                  <div className="p-3 bg-[#121216] border border-[#1E1E26] rounded-sm">
                    <span className="text-[#71717A] block text-[10px]">EXECUTION TIME</span>
                    <strong className="text-white text-sm">&lt; 380ms</strong>
                  </div>
                  <div className="p-3 bg-[#121216] border border-[#1E1E26] rounded-sm">
                    <span className="text-[#71717A] block text-[10px]">SECURITY ENCLAVE</span>
                    <strong className="text-[#10B981] text-sm">SSRF Filtered</strong>
                  </div>
                </div>
              </div>

              {/* Visual Simulated DOM Inspector */}
              <div className="lg:col-span-7 bg-[#070709] border border-[#1E1E26] rounded-sm p-4 font-mono text-xs">
                <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#181820] text-[#71717A]">
                  <span className="flex items-center gap-2 text-white">
                    <Globe className="w-3.5 h-3.5 text-[#10B981]" />
                    Playwright Live Inspector: https://books.toscrape.com
                  </span>
                  <span className="text-[#10B981] text-[10px]">200 OK</span>
                </div>
                <div className="space-y-1.5 text-[#A1A1AA]">
                  <div className="text-[#71717A]">&lt;!-- DOM Structure Verified --&gt;</div>
                  <div>
                    &lt;article class=&quot;<span className="text-[#10B981]">product_pod</span>&quot;&gt;
                  </div>
                  <div className="pl-4">
                    &lt;h3&gt;&lt;a href=&quot;...&quot;&gt;<span className="text-white bg-[#10B981]/20 px-1">It&apos;s Only the Himalayas</span>&lt;/a&gt;&lt;/h3&gt;
                  </div>
                  <div className="pl-4">
                    &lt;p class=&quot;price_color&quot;&gt;<span className="text-white bg-[#10B981]/20 px-1">£45.17</span>&lt;/p&gt;
                  </div>
                  <div className="pl-4">
                    &lt;p class=&quot;instock availability&quot;&gt;<span className="text-white bg-[#10B981]/20 px-1">In stock</span>&lt;/p&gt;
                  </div>
                  <div>&lt;/article&gt;</div>
                  <div className="pt-2 text-[#10B981] flex items-center gap-1.5 font-bold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Selector &apos;article.product_pod h3 a&apos; matched 11 items</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeStep === 2 && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
              <div className="lg:col-span-5 space-y-4 font-sans">
                <span className="text-xs font-mono text-[#38BDF8] font-semibold uppercase">
                  Stage 02 // Deterministic Schema Gate
                </span>
                <h3 className="text-2xl font-bold text-white">
                  Deterministic Pydantic v2. The LLM Is Never the Verifier.
                </h3>
                <p className="text-sm text-[#A1A1AA] leading-relaxed">
                  Extracted values must satisfy strict customer-defined schemas. If an element changes from a price float to an error string, the system blocks corruption before data ever reaches your database.
                </p>
                <div className="grid grid-cols-2 gap-3 pt-2 font-mono text-xs">
                  <div className="p-3 bg-[#121216] border border-[#1E1E26] rounded-sm">
                    <span className="text-[#71717A] block text-[10px]">HALLUCINATION RISK</span>
                    <strong className="text-[#38BDF8] text-sm">0.00% (Strict)</strong>
                  </div>
                  <div className="p-3 bg-[#121216] border border-[#1E1E26] rounded-sm">
                    <span className="text-[#71717A] block text-[10px]">DOWNSTREAM UPTIME</span>
                    <strong className="text-white text-sm">100% Guaranteed</strong>
                  </div>
                </div>
              </div>

              {/* Visual Schema Validator */}
              <div className="lg:col-span-7 bg-[#070709] border border-[#1E1E26] rounded-sm p-4 font-mono text-xs">
                <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#181820] text-[#71717A]">
                  <span className="flex items-center gap-2 text-white">
                    <ShieldCheck className="w-3.5 h-3.5 text-[#38BDF8]" />
                    Pydantic v2 Field Contract Validation
                  </span>
                  <span className="text-[#38BDF8] text-[10px]">ALL PASS</span>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-2 rounded-xs bg-[#121216] border border-[#1E1E26]">
                    <span className="text-[#E4E4E7]">field: &quot;title&quot; (str)</span>
                    <span className="text-[#10B981] font-bold flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> &quot;It&apos;s Only the Himalayas&quot;
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-xs bg-[#121216] border border-[#1E1E26]">
                    <span className="text-[#E4E4E7]">field: &quot;price&quot; (str / currency)</span>
                    <span className="text-[#10B981] font-bold flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> &quot;£45.17&quot;
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-xs bg-[#121216] border border-[#1E1E26]">
                    <span className="text-[#E4E4E7]">field: &quot;stock&quot; (str)</span>
                    <span className="text-[#10B981] font-bold flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> &quot;In stock&quot;
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeStep === 3 && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
              <div className="lg:col-span-5 space-y-4 font-sans">
                <span className="text-xs font-mono text-[#F59E0B] font-semibold uppercase">
                  Stage 03 // Autonomous Recovery
                </span>
                <h3 className="text-2xl font-bold text-white">
                  When Websites Change, MorphAPI Heals Itself.
                </h3>
                <p className="text-sm text-[#A1A1AA] leading-relaxed">
                  When a selector fails (0 DOM matches), LangGraph catches the error, passes sanitized structural DOM to NVIDIA NIM, and tests replacement candidates in Playwright before promoting version 2.
                </p>
                <div className="grid grid-cols-2 gap-3 pt-2 font-mono text-xs">
                  <div className="p-3 bg-[#121216] border border-[#1E1E26] rounded-sm">
                    <span className="text-[#71717A] block text-[10px]">AI MODEL</span>
                    <strong className="text-white text-sm">NVIDIA NIM 70B</strong>
                  </div>
                  <div className="p-3 bg-[#121216] border border-[#1E1E26] rounded-sm">
                    <span className="text-[#71717A] block text-[10px]">PROMOTION</span>
                    <strong className="text-[#F59E0B] text-sm">Zero Downtime</strong>
                  </div>
                </div>
              </div>

              {/* Visual Self-Healing Recovery Graph */}
              <div className="lg:col-span-7 bg-[#070709] border border-[#1E1E26] rounded-sm p-4 font-mono text-xs space-y-3">
                <div className="flex items-center justify-between pb-3 border-b border-[#181820] text-[#71717A]">
                  <span className="flex items-center gap-2 text-white">
                    <GitBranch className="w-3.5 h-3.5 text-[#F59E0B]" />
                    LangGraph Healing State Machine
                  </span>
                  <span className="text-[#F59E0B] text-[10px]">ACTIVE WORKFLOW</span>
                </div>

                <div className="space-y-1.5 text-xs">
                  <div className="p-2 bg-[#7F1D1D]/20 border border-[#991B1B]/40 text-[#FCA5A5] rounded-xs flex items-center justify-between">
                    <span>1. SELECTOR DRIFT DETECTED: 0 DOM nodes</span>
                    <span className="text-[10px] bg-[#991B1B] text-white px-1.5 py-0.5 rounded-xs">TRIGGER</span>
                  </div>
                  <div className="p-2 bg-[#14141A] border border-[#22222A] text-[#A1A1AA] rounded-xs flex items-center justify-between">
                    <span>2. NVIDIA NIM: Synthesized candidate selector</span>
                    <span className="text-[10px] bg-[#2A2A38] text-white px-1.5 py-0.5 rounded-xs">HYPOTHESIS</span>
                  </div>
                  <div className="p-2 bg-[#064E3B]/20 border border-[#059669]/40 text-[#86EFAC] rounded-xs flex items-center justify-between">
                    <span>3. PLAYWRIGHT: Verified 10 matches on live page</span>
                    <span className="text-[10px] bg-[#059669] text-white px-1.5 py-0.5 rounded-xs">VERIFIED</span>
                  </div>
                  <div className="p-2 bg-[#10B981]/15 border border-[#10B981]/30 text-[#10B981] rounded-xs flex items-center justify-between font-bold">
                    <span>4. PROMOTED: Atomically upgraded to v2</span>
                    <span className="text-[10px] bg-[#10B981] text-black px-1.5 py-0.5 rounded-xs">ACTIVE</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
