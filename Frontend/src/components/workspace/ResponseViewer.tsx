"use client";

import React, { useState } from "react";
import {
  Copy,
  Check,
  Download,
  AlertCircle,
  Clock,
  HardDrive,
  FileText,
  Code2,
} from "lucide-react";
import { TestExecutionResult } from "@/lib/types";

interface ResponseViewerProps {
  result?: TestExecutionResult | null;
  isRunning?: boolean;
}

export function ResponseViewer({ result, isRunning = false }: ResponseViewerProps) {
  const [activeTab, setActiveTab] = useState<"json" | "raw" | "headers">("json");
  const [copied, setCopied] = useState(false);

  if (isRunning) {
    return (
      <div className="w-full min-h-[220px] rounded-xl bg-[#151E23] border border-[#3A4A50] p-6 flex flex-col items-center justify-center gap-3 font-sans text-xs">
        <div className="w-8 h-8 rounded-full border-2 border-[#C3D1B8] border-t-transparent animate-spin" />
        <div className="text-[#EDF1EE] font-semibold">Executing test against gateway...</div>
        <div className="text-[11px] font-mono text-[#ADBAB9]">
          Capturing live response &amp; evaluating Pydantic v2 schema
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="w-full min-h-[200px] rounded-xl bg-[#151E23] border border-[#3A4A50] p-6 flex flex-col items-center justify-center text-center gap-2 font-sans text-xs select-none">
        <div className="w-8 h-8 rounded-lg bg-[#202C32] border border-[#3A4A50] flex items-center justify-center text-[#ADBAB9] mb-1">
          <Code2 className="w-4 h-4" />
        </div>
        <div className="text-[#EDF1EE] font-medium">Run a test to see the response.</div>
        <div className="text-[11px] text-[#ADBAB9] max-w-xs">
          Click &quot;Run Test&quot; above to execute this endpoint with your configured parameters.
        </div>
      </div>
    );
  }

  const isSuccess = result.status >= 200 && result.status < 300;
  const jsonText =
    typeof result.data === "object"
      ? JSON.stringify(result.data, null, 2)
      : String(result.data || "");

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([jsonText], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `response_${result.endpointId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full rounded-xl bg-[#151E23] border border-[#3A4A50] overflow-hidden font-sans text-xs shadow-md">
      {/* Response Status Bar: HTTP Code, Latency, Size */}
      <div className="px-4 py-2.5 bg-[#202C32] border-b border-[#3A4A50] flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {/* Status Badge */}
          <span
            className={`px-2 py-0.5 rounded-sm font-mono text-[11px] font-bold border ${
              isSuccess
                ? "bg-[#A7C4A2]/15 text-[#A7C4A2] border-[#A7C4A2]/30"
                : "bg-[#E3A29E]/15 text-[#E3A29E] border-[#E3A29E]/30"
            }`}
          >
            {result.status} {result.statusText}
          </span>

          {/* Latency */}
          <span className="flex items-center gap-1 font-mono text-[11px] text-[#ADBAB9] bg-[#151E23] px-2 py-0.5 rounded-sm border border-[#3A4A50]">
            <Clock className="w-3 h-3 text-[#ADBAB9]" />
            <span>{result.durationMs}ms</span>
          </span>

          {/* Payload Size */}
          <span className="flex items-center gap-1 font-mono text-[11px] text-[#ADBAB9] bg-[#151E23] px-2 py-0.5 rounded-sm border border-[#3A4A50]">
            <HardDrive className="w-3 h-3 text-[#ADBAB9]" />
            <span>{(result.sizeBytes / 1024).toFixed(1)} KB</span>
          </span>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={handleCopy}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#151E23] hover:bg-[#2A3940] border border-[#3A4A50] text-[11px] font-mono text-[#ADBAB9] hover:text-[#EDF1EE] transition-colors"
            title="Copy response body"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-[#A7C4A2]" />
                <span>Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span>Copy</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={handleDownload}
            className="p-1 rounded-md bg-[#151E23] hover:bg-[#2A3940] border border-[#3A4A50] text-[#ADBAB9] hover:text-[#EDF1EE] transition-colors"
            title="Download response JSON"
          >
            <Download className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Tabs: JSON / Raw / Headers */}
      <div className="px-4 py-1.5 bg-[#151E23] border-b border-[#3A4A50] flex items-center gap-1 text-[11px] font-mono">
        <button
          type="button"
          onClick={() => setActiveTab("json")}
          className={`px-2.5 py-0.5 rounded-sm transition-colors ${
            activeTab === "json"
              ? "bg-[#202C32] text-[#C3D1B8] border border-[#3A4A50] font-semibold"
              : "text-[#ADBAB9] hover:text-[#EDF1EE]"
          }`}
        >
          JSON
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("raw")}
          className={`px-2.5 py-0.5 rounded-sm transition-colors ${
            activeTab === "raw"
              ? "bg-[#202C32] text-[#C3D1B8] border border-[#3A4A50] font-semibold"
              : "text-[#ADBAB9] hover:text-[#EDF1EE]"
          }`}
        >
          Raw
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("headers")}
          className={`px-2.5 py-0.5 rounded-sm transition-colors ${
            activeTab === "headers"
              ? "bg-[#202C32] text-[#C3D1B8] border border-[#3A4A50] font-semibold"
              : "text-[#ADBAB9] hover:text-[#EDF1EE]"
          }`}
        >
          Headers ({Object.keys(result.headers).length})
        </button>
      </div>

      {/* Content Body */}
      <div className="p-3 max-h-[300px] overflow-y-auto font-mono text-[11px]">
        {activeTab === "json" && (
          <pre
            className={`overflow-x-auto ${
              isSuccess ? "text-[#EDF1EE]" : "text-[#E3A29E]"
            }`}
          >
            {jsonText}
          </pre>
        )}

        {activeTab === "raw" && (
          <pre className="text-[#EDF1EE] overflow-x-auto whitespace-pre-wrap">
            {result.rawText || jsonText}
          </pre>
        )}

        {activeTab === "headers" && (
          <div className="space-y-1">
            {Object.entries(result.headers).map(([k, v]) => (
              <div key={k} className="flex items-start gap-2 text-[11px]">
                <span className="text-[#ADBAB9] font-semibold shrink-0">{k}:</span>
                <span className="text-[#AEC8D0] break-all">{v}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
