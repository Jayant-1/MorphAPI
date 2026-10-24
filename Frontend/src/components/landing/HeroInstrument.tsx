"use client";

import React, { useState } from "react";
import {
  Globe,
  Play,
  Flame,
  Check,
  Copy,
  Code2,
  Bot,
  RefreshCw,
  Zap,
  ArrowRight,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

interface Preset {
  id: string;
  name: string;
  category: string;
  url: string;
  prompt: string;
  endpoint: string;
  mcpTool: string;
  normalSelector: string;
  brokenSelector: string;
  healedSelector: string;
  previewItems: { title: string; meta1: string; meta2: string }[];
  normalData: any[];
}

const PRESETS: Preset[] = [
  {
    id: "books",
    name: "Books Catalog",
    category: "E-Commerce",
    url: "https://books.toscrape.com/catalogue/category/books/travel_2",
    prompt: "Extract book title, price in GBP as float, and in-stock availability",
    endpoint: "https://gateway.morphapi.io/v1/extract/books-travel",
    mcpTool: "morph_extract_books_travel",
    normalSelector: "article.product_pod h3 a",
    brokenSelector: "div.product_pod_broken",
    healedSelector: "div.catalog-grid article h3 a",
    previewItems: [
      { title: "It's Only the Himalayas", meta1: "£45.17", meta2: "In stock" },
      { title: "Full Moon over Noah's Ark", meta1: "£49.43", meta2: "In stock" },
      { title: "See America: A Celebration", meta1: "£48.87", meta2: "In stock" },
    ],
    normalData: [
      { title: "It's Only the Himalayas", price: 45.17, currency: "GBP", stock: "In stock" },
      { title: "Full Moon over Noah's Ark", price: 49.43, currency: "GBP", stock: "In stock" },
      { title: "See America: A Celebration", price: 48.87, currency: "GBP", stock: "In stock" },
    ],
  },
  {
    id: "mandi",
    name: "Mandi Crop Prices",
    category: "Agriculture",
    url: "https://msamb.com/market-prices/bulletin",
    prompt: "Extract crop name in English & Marathi, market district, and modal auction price",
    endpoint: "https://gateway.morphapi.io/v1/extract/mandi-prices",
    mcpTool: "morph_extract_mandi_prices",
    normalSelector: "table#mandi-bulletin tr td.price",
    brokenSelector: "table#mandi-v2-broken",
    healedSelector: "div.mandi-grid table tr td[data-col='price']",
    previewItems: [
      { title: "Onion (लाल कांदा)", meta1: "₹2,450/Qtl", meta2: "Nashik APMC" },
      { title: "Soybean (पिवळी सोयाबीन)", meta1: "₹4,820/Qtl", meta2: "Latur Mandi" },
      { title: "Cotton (कापूस)", meta1: "₹7,280/Qtl", meta2: "Akola APMC" },
    ],
    normalData: [
      { crop: "Onion (लाल कांदा)", district: "Nashik APMC", modal_price: 2450, unit: "INR/Qtl" },
      { crop: "Soybean (पिवळी सोयाबीन)", district: "Latur Mandi", modal_price: 4820, unit: "INR/Qtl" },
      { crop: "Cotton (कापूस)", district: "Akola APMC", modal_price: 7280, unit: "INR/Qtl" },
    ],
  },
  {
    id: "fastapi",
    name: "FastAPI Releases",
    category: "Software",
    url: "https://github.com/tiangolo/fastapi/releases",
    prompt: "Extract release version tag, published ISO timestamp, and commit hash",
    endpoint: "https://gateway.morphapi.io/v1/extract/fastapi-releases",
    mcpTool: "morph_extract_fastapi_releases",
    normalSelector: "div[data-test-selector='release-card'] h2 a",
    brokenSelector: "div.release-entry-broken",
    healedSelector: "section.release-card-v2 h2 a.Link--primary",
    previewItems: [
      { title: "Release 0.115.6", meta1: "2026-10-18", meta2: "commit b91a0c4" },
      { title: "Release 0.115.5", meta1: "2026-10-12", meta2: "commit f44e190" },
      { title: "Release 0.115.4", meta1: "2026-10-04", meta2: "commit a29d71c" },
    ],
    normalData: [
      { version: "0.115.6", published_at: "2026-10-18T10:00:00Z", commit: "b91a0c4" },
      { version: "0.115.5", published_at: "2026-10-12T14:30:00Z", commit: "f44e190" },
      { version: "0.115.4", published_at: "2026-10-04T08:15:00Z", commit: "a29d71c" },
    ],
  },
];

export function HeroInstrument() {
  const [activePreset, setActivePreset] = useState<Preset>(PRESETS[0]);
  const [isRedesigned, setIsRedesigned] = useState(false);
  const [isHealing, setIsHealing] = useState(false);
  const [activeOutputTab, setActiveOutputTab] = useState<"json" | "curl" | "mcp">("json");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [requestPinging, setRequestPinging] = useState(false);

  const handleSelectPreset = (p: Preset) => {
    setActivePreset(p);
    setIsRedesigned(false);
    setIsHealing(false);
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleToggleRedesign = () => {
    if (isRedesigned) {
      // Reset back to normal
      setIsRedesigned(false);
      setIsHealing(false);
    } else {
      // Trigger simulation: shows healing in flight
      setIsHealing(true);
      setTimeout(() => {
        setIsHealing(false);
        setIsRedesigned(true);
      }, 1200);
    }
  };

  const handleSendProbe = () => {
    setRequestPinging(true);
    setTimeout(() => {
      setRequestPinging(false);
    }, 250);
  };

  // Generate current response JSON
  const getResponseJson = () => {
    if (isRedesigned) {
      return {
        status: 200,
        latency_ms: 1240,
        healed: true,
        autonomous_healing: {
          original_selector: activePreset.normalSelector,
          healed_selector: activePreset.healedSelector,
          downtime: "0s",
          action: "Vision AI hot-patched selector in-flight on TimeoutError",
        },
        data: activePreset.normalData,
      };
    }

    return {
      status: 200,
      latency_ms: requestPinging ? 34 : 38,
      healed: false,
      selector: activePreset.normalSelector,
      data: activePreset.normalData,
    };
  };

  const curlSnippet = `curl -X GET "${activePreset.endpoint}" \\\n  -H "Authorization: Bearer morph_live_sec_9941a8f_healer" \\\n  -H "Accept: application/json"`;

  const mcpSnippet = JSON.stringify(
    {
      name: activePreset.mcpTool,
      description: `Extracts structured data from ${activePreset.url}`,
      inputSchema: {
        type: "object",
        properties: {
          refresh: { type: "boolean", default: false, description: "Bypass cache" },
        },
      },
    },
    null,
    2
  );

  return (
    <section id="demo" className="relative w-full py-16 md:py-24 border-b border-[#1A1A20] bg-[#070709] font-sans">
      <div className="max-w-[1360px] mx-auto px-4 sm:px-6 lg:px-8">
        {/* Crisp, Direct Section Header */}
        <div className="text-center max-w-2xl mx-auto mb-10 space-y-2">
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold tracking-tight text-white">
            How MorphAPI Works
          </h2>
          <p className="text-sm text-[#A1A1AA] leading-relaxed">
            Provide any webpage and what data you need. MorphAPI turns it into a typed, production-ready API that self-heals when layout classes change.
          </p>
        </div>

        {/* Clean, All-in-One Interactive Instrument */}
        <div className="w-full rounded-xl border border-[#22242F] bg-[#0B0C11] shadow-2xl overflow-hidden font-mono text-xs">
          {/* Top Configuration Strip: Presets, URL, and Target Prompt */}
          <div className="p-4 sm:p-5 bg-[#0E1016] border-b border-[#1E2028] space-y-3">
            {/* Presets Row */}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 overflow-x-auto">
                <span className="text-[10px] text-[#71717A] uppercase tracking-wider font-semibold mr-1 shrink-0">
                  Select Example:
                </span>
                {PRESETS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => handleSelectPreset(p)}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors shrink-0 cursor-pointer ${
                      activePreset.id === p.id
                        ? "bg-[#1C1F2E] text-white border border-[#2F3447]"
                        : "text-[#71717A] hover:text-white hover:bg-[#141620]"
                    }`}
                  >
                    {p.name}
                  </button>
                ))}
              </div>

              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 shrink-0">
                {activePreset.category}
              </span>
            </div>

            {/* Input & Prompt Grid */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-2.5 pt-1">
              {/* URL */}
              <div className="md:col-span-5 flex items-center bg-[#12141C] border border-[#22242F] rounded-lg px-3 py-2 text-xs">
                <Globe className="w-3.5 h-3.5 text-[#71717A] mr-2 shrink-0" />
                <span className="text-white truncate select-all">{activePreset.url}</span>
              </div>

              {/* What to Return (Prompt) */}
              <div className="md:col-span-7 flex items-center bg-[#12141C] border border-[#22242F] rounded-lg px-3 py-2 text-xs text-[#A1A1AA]">
                <span className="text-[#71717A] shrink-0 mr-2 font-medium">Extract:</span>
                <span className="text-white truncate">{activePreset.prompt}</span>
              </div>
            </div>
          </div>

          {/* Interactive Split View: Webpage Source (Left) ──> Live API Output (Right) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-[#1E2028]">
            {/* =========================================================================
                LEFT: TARGET WEBPAGE & AG-UI DOM MAPPING
               ========================================================================= */}
            <div className="p-4 sm:p-5 flex flex-col justify-between space-y-4 bg-[#090A0E]">
              <div className="space-y-3">
                {/* Header with Simulate Redesign Toggle */}
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white text-xs">Target Webpage</span>
                    <span className="text-[10px] text-[#71717A]">(Playwright DOM)</span>
                  </div>

                  {/* Redesign Simulation Button */}
                  <button
                    onClick={handleToggleRedesign}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                      isRedesigned
                        ? "bg-amber-500/15 border border-amber-500/40 text-amber-400"
                        : "bg-[#181A24] hover:bg-[#202330] border border-[#272B3B] text-[#D4D4D8] hover:text-white"
                    }`}
                  >
                    <Flame className={`w-3.5 h-3.5 ${isRedesigned ? "text-amber-400" : "text-[#71717A]"}`} />
                    <span>{isRedesigned ? "Reset to Original DOM" : "Simulate Website Redesign"}</span>
                  </button>
                </div>

                {/* Status Callout when Broken / Healed */}
                {isHealing ? (
                  <div className="p-2.5 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs flex items-center gap-2 animate-pulse">
                    <span className="w-2 h-2 rounded-full bg-amber-400" />
                    <span>Selector Timeout detected. Holding connection and synthesizing vision hot-patch...</span>
                  </div>
                ) : isRedesigned ? (
                  <div className="p-2.5 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-emerald-400" />
                      <span>DOM redesign detected. Hot-patched in 1.2s with 0 downtime.</span>
                    </div>
                    <span className="text-[10px] text-[#A1A1AA] font-mono">200 OK</span>
                  </div>
                ) : (
                  <div className="text-[11px] text-[#71717A] flex items-center justify-between">
                    <span>Active selector: <code className="text-emerald-400">{activePreset.normalSelector}</code></span>
                    <span className="text-[10px] text-[#52525B]">Fast Path &lt;40ms</span>
                  </div>
                )}

                {/* Simulated Webpage Cards */}
                <div className="space-y-2 pt-1">
                  {activePreset.previewItems.map((item, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg border transition-all ${
                        isRedesigned
                          ? "bg-[#141520] border-amber-500/40 shadow-[0_0_12px_rgba(245,158,11,0.06)]"
                          : "bg-[#11131B] border-[#222532] hover:border-emerald-500/40"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-white font-semibold text-xs">{item.title}</span>
                        <span className="text-emerald-400 font-bold">{item.meta1}</span>
                      </div>
                      <div className="mt-1 flex items-center justify-between text-[11px] text-[#71717A]">
                        <span>{item.meta2}</span>
                        <span className="text-[10px] font-mono text-[#52525B]">
                          {isRedesigned ? `class: ${activePreset.brokenSelector}` : "matched"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Bottom Guidance */}
              <div className="pt-2 border-t border-[#1A1C24] text-[11px] text-[#52525B] flex items-center justify-between">
                <span>Click &quot;Simulate Website Redesign&quot; to test autonomous healing.</span>
                <span className="text-emerald-400">Pydantic v2 Verified</span>
              </div>
            </div>

            {/* =========================================================================
                RIGHT: LIVE API ENDPOINT & TEST EXECUTION
               ========================================================================= */}
            <div className="p-4 sm:p-5 flex flex-col justify-between space-y-4 bg-[#0A0B0E]">
              <div className="space-y-3">
                {/* Header with Output Tabs */}
                <div className="flex items-center justify-between gap-2 pb-1">
                  <div className="flex items-center gap-1 bg-[#12141C] p-1 rounded-md border border-[#22242F]">
                    <button
                      onClick={() => setActiveOutputTab("json")}
                      className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                        activeOutputTab === "json"
                          ? "bg-[#1E2230] text-white"
                          : "text-[#71717A] hover:text-white"
                      }`}
                    >
                      JSON Response
                    </button>
                    <button
                      onClick={() => setActiveOutputTab("curl")}
                      className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                        activeOutputTab === "curl"
                          ? "bg-[#1E2230] text-white"
                          : "text-[#71717A] hover:text-white"
                      }`}
                    >
                      cURL Command
                    </button>
                    <button
                      onClick={() => setActiveOutputTab("mcp")}
                      className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                        activeOutputTab === "mcp"
                          ? "bg-[#1E2230] text-white"
                          : "text-[#71717A] hover:text-white"
                      }`}
                    >
                      MCP Tool Schema
                    </button>
                  </div>

                  {/* Send Live Request Probe Button */}
                  {activeOutputTab === "json" && (
                    <button
                      onClick={handleSendProbe}
                      disabled={requestPinging}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-500 hover:bg-emerald-400 text-black font-bold text-xs transition-colors cursor-pointer shadow-[0_0_12px_rgba(16,185,129,0.25)]"
                    >
                      <Play className="w-3 h-3 fill-black" />
                      <span>{requestPinging ? "Pinging..." : "Test Request"}</span>
                    </button>
                  )}
                </div>

                {/* JSON TAB */}
                {activeOutputTab === "json" && (
                  <div className="space-y-2">
                    {/* Status pill strip */}
                    <div className="flex items-center justify-between text-[11px] p-2 rounded bg-[#12141C] border border-[#202330]">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-emerald-400">HTTP 200 OK</span>
                        <span className="text-[#52525B]">•</span>
                        <span className="text-[#A1A1AA]">
                          Latency:{" "}
                          <strong className={isRedesigned ? "text-amber-400" : "text-emerald-400"}>
                            {isRedesigned ? "1240ms (Healed)" : "38ms"}
                          </strong>
                        </span>
                      </div>
                      <button
                        onClick={() => handleCopy(JSON.stringify(getResponseJson(), null, 2), "json")}
                        className="text-[10px] text-[#71717A] hover:text-white flex items-center gap-1 cursor-pointer"
                      >
                        {copiedKey === "json" ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedKey === "json" ? "Copied" : "Copy"}</span>
                      </button>
                    </div>

                    {/* Pre Code Box */}
                    <pre className="p-3.5 rounded-lg bg-[#0E1017] border border-[#1E2028] text-xs font-mono text-[#D4D4D8] overflow-x-auto max-h-[290px] leading-relaxed">
                      <code>{JSON.stringify(getResponseJson(), null, 2)}</code>
                    </pre>
                  </div>
                )}

                {/* CURL TAB */}
                {activeOutputTab === "curl" && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-[11px] p-2 rounded bg-[#12141C] border border-[#202330]">
                      <span className="text-[#A1A1AA]">Direct Terminal Execution</span>
                      <button
                        onClick={() => handleCopy(curlSnippet, "curl")}
                        className="text-[10px] text-[#71717A] hover:text-white flex items-center gap-1 cursor-pointer"
                      >
                        {copiedKey === "curl" ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedKey === "curl" ? "Copied" : "Copy Command"}</span>
                      </button>
                    </div>
                    <pre className="p-3.5 rounded-lg bg-[#0E1017] border border-[#1E2028] text-xs font-mono text-emerald-400 overflow-x-auto leading-relaxed">
                      <code>{curlSnippet}</code>
                    </pre>
                  </div>
                )}

                {/* MCP TAB */}
                {activeOutputTab === "mcp" && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-[11px] p-2 rounded bg-[#12141C] border border-[#202330]">
                      <span className="text-cyan-400 font-semibold">Claude Desktop &amp; Cursor MCP Tool</span>
                      <button
                        onClick={() => handleCopy(mcpSnippet, "mcp")}
                        className="text-[10px] text-[#71717A] hover:text-white flex items-center gap-1 cursor-pointer"
                      >
                        {copiedKey === "mcp" ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedKey === "mcp" ? "Copied" : "Copy MCP Tool"}</span>
                      </button>
                    </div>
                    <pre className="p-3.5 rounded-lg bg-[#0E1017] border border-[#22242F] text-xs font-mono text-cyan-300 overflow-x-auto max-h-[290px] leading-relaxed">
                      <code>{mcpSnippet}</code>
                    </pre>
                  </div>
                )}
              </div>

              {/* Bottom API Link */}
              <div className="pt-2 border-t border-[#1A1C24] text-[11px] text-[#52525B] flex items-center justify-between">
                <span className="truncate mr-2">Endpoint: {activePreset.endpoint}</span>
                <span className="text-white shrink-0 font-medium">Ready</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
