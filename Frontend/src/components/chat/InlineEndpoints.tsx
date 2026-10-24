"use client";

import React, { useState } from "react";
import { Copy, Check, Code2, ExternalLink, Terminal, ShieldCheck } from "lucide-react";
import { EndpointDefinition } from "@/lib/types";
import { InlineApiTester } from "./InlineApiTester";

interface InlineEndpointsProps {
  endpoints: EndpointDefinition[];
}

export function InlineEndpoints({ endpoints }: InlineEndpointsProps) {
  const [activeTestEndpointId, setActiveTestEndpointId] = useState<string | null>(null);
  const [copiedPathId, setCopiedPathId] = useState<string | null>(null);
  const [expandedDetailsId, setExpandedDetailsId] = useState<string | null>(null);

  const handleCopy = (ep: EndpointDefinition) => {
    navigator.clipboard.writeText(ep.cUrlTemplate || `curl "${ep.fullUrl || ep.path}"`);
    setCopiedPathId(ep.id);
    setTimeout(() => setCopiedPathId(null), 2000);
  };

  const toggleTest = (id: string) => {
    setActiveTestEndpointId(activeTestEndpointId === id ? null : id);
  };

  const toggleDetails = (id: string) => {
    setExpandedDetailsId(expandedDetailsId === id ? null : id);
  };

  if (!endpoints || endpoints.length === 0) {
    return (
      <div className="text-xs text-[#ADBAB9] italic py-2">
        No endpoints were synthesized from this page.
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col font-sans text-sm mt-3 space-y-3">
      {/* Heading: Syne, selective brand prominence */}
      <div className="space-y-1">
        <h2 className="font-syne font-semibold text-[20px] sm:text-[22px] leading-[1.15] tracking-[-0.02em] text-[#EDF1EE]">
          Your API is ready
        </h2>
        <p className="font-sans text-[14px] text-[#ADBAB9] leading-relaxed">
          The extraction plan is verified and live on the gateway:
        </p>
      </div>

      {/* Endpoints List */}
      <div className="w-full divide-y divide-[#3A4A50]/60 rounded-xl bg-[#202C32] border border-[#3A4A50] overflow-hidden shadow-sm">
        {endpoints.map((ep) => {
          const isTesting = activeTestEndpointId === ep.id;
          const isDetailsOpen = expandedDetailsId === ep.id;
          const methods = ep.supportedMethods && ep.supportedMethods.length > 0
            ? ep.supportedMethods
            : [ep.method];

          return (
            <div key={ep.id} className="p-3.5 sm:p-4 flex flex-col gap-2.5">
              {/* Endpoint Header Row */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  {methods.map((m) => (
                    <span
                      key={m}
                      className={`px-2 py-0.5 rounded text-[12px] font-mono font-semibold tracking-normal ${
                        m === "GET"
                          ? "bg-[#AEC8D0]/15 text-[#AEC8D0] border border-[#AEC8D0]/30"
                          : m === "POST"
                          ? "bg-[#C3D1B8]/15 text-[#C3D1B8] border border-[#C3D1B8]/30"
                          : "bg-[#DDC38A]/15 text-[#DDC38A] border border-[#DDC38A]/30"
                      }`}
                    >
                      {m}
                    </span>
                  ))}

                  {/* Route path */}
                  <span className="font-mono text-[13px] sm:text-[14px] tracking-normal text-[#EDF1EE] font-medium selection:bg-[#C3D1B8]/20">
                    {ep.path}
                  </span>
                </div>

                {/* Actions: Details, Copy, Test */}
                <div className="flex items-center gap-2 self-start sm:self-auto">
                  <button
                    type="button"
                    onClick={() => toggleDetails(ep.id)}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[13px] font-medium font-sans text-[#ADBAB9] hover:text-[#EDF1EE] hover:bg-[#2A3940] transition-colors"
                    title="View cURL and OpenAPI details"
                  >
                    <Code2 className="w-3.5 h-3.5" />
                    <span>Details</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleCopy(ep)}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[13px] font-medium font-sans text-[#ADBAB9] hover:text-[#EDF1EE] hover:bg-[#2A3940] transition-colors"
                    title="Copy cURL command"
                  >
                    {copiedPathId === ep.id ? (
                      <Check className="w-3.5 h-3.5 text-[#A7C4A2]" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                    <span>{copiedPathId === ep.id ? "Copied" : "Copy"}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => toggleTest(ep.id)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-[13px] font-medium font-sans transition-colors ${
                      isTesting
                        ? "bg-[#C3D1B8] text-[#17201C] hover:bg-[#D5DFCD]"
                        : "bg-[#151E23] hover:bg-[#2A3940] text-[#EDF1EE] border border-[#3A4A50]"
                    }`}
                  >
                    <span>{isTesting ? "Close Test" : "Test"}</span>
                  </button>
                </div>
              </div>

              {/* Title & Description */}
              <div className="space-y-0.5">
                <div className="text-[16px] font-medium font-sans text-[#EDF1EE]">
                  {ep.name}
                </div>
                <p className="text-[13px] text-[#ADBAB9] font-sans leading-relaxed">
                  {ep.description}
                </p>
              </div>

              {/* Links to Swagger UI Docs & OpenAPI 3.1 Spec */}
              {(ep.docsUrl || ep.openapiUrl) && (
                <div className="flex items-center gap-4 text-[12px] pt-1">
                  {ep.docsUrl && (
                    <a
                      href={ep.docsUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 text-[#C3D1B8] hover:underline"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span>Interactive Swagger UI Docs</span>
                    </a>
                  )}
                  {ep.openapiUrl && (
                    <a
                      href={ep.openapiUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 text-[#AEC8D0] hover:underline"
                    >
                      <Terminal className="w-3.5 h-3.5" />
                      <span>OpenAPI 3.1 JSON</span>
                    </a>
                  )}
                </div>
              )}

              {/* Expandable Details: cURL and Schema */}
              {isDetailsOpen && (
                <div className="mt-2 p-3 rounded-lg bg-[#10171B] border border-[#3A4A50]/60 space-y-2.5 font-mono text-[13px] tracking-normal">
                  <div className="text-[13px] font-sans font-medium text-[#EDF1EE] flex items-center gap-1.5">
                    <Terminal className="w-3.5 h-3.5 text-[#ADBAB9]" />
                    <span>cURL Command</span>
                  </div>
                  <pre className="p-2.5 rounded bg-[#151E23] border border-[#3A4A50]/40 overflow-x-auto text-[13px] text-[#EDF1EE] font-mono tracking-normal leading-relaxed">
                    {ep.cUrlTemplate || `curl "${ep.fullUrl || ep.path}"`}
                  </pre>

                  {ep.responseSchema && (
                    <div className="space-y-1 pt-1">
                      <div className="text-[13px] font-sans font-medium text-[#EDF1EE]">
                        Contract Schema Definition
                      </div>
                      <pre className="p-2.5 rounded bg-[#151E23] border border-[#3A4A50]/40 overflow-x-auto text-[13px] text-[#ADBAB9] font-mono tracking-normal leading-relaxed max-h-40">
                        {JSON.stringify(ep.responseSchema, null, 2)}
                      </pre>
                    </div>
                  )}

                  {/* Dev note on authentication */}
                  <div className="flex items-center gap-1.5 text-[12px] text-[#ADBAB9] pt-1 font-sans">
                    <ShieldCheck className="w-3.5 h-3.5 text-[#A7C4A2]" />
                    <span>Development Mode: API Key validation is optional on local gateway.</span>
                  </div>
                </div>
              )}

              {/* Inline API Tester Expands Directly Beneath This Endpoint */}
              {isTesting && <InlineApiTester endpoint={ep} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
