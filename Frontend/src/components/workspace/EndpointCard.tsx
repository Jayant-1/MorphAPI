"use client";

import React, { useState } from "react";
import {
  Copy,
  Check,
  ExternalLink,
  Play,
  Code2,
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  Lock,
  Globe,
} from "lucide-react";
import { EndpointDefinition, HttpMethod } from "@/lib/types";

interface EndpointCardProps {
  endpoint: EndpointDefinition;
  isSelected?: boolean;
  onSelectTest: (endpoint: EndpointDefinition) => void;
}

export function EndpointCard({
  endpoint,
  isSelected = false,
  onSelectTest,
}: EndpointCardProps) {
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null);
  const [showCodeSnippets, setShowCodeSnippets] = useState(false);
  const [showSchema, setShowSchema] = useState(false);
  const [activeSnippetTab, setActiveSnippetTab] = useState<"curl" | "js" | "py" | "mcp">("curl");

  const fullApiUrl = `http://localhost:8000${endpoint.path}`;

  const handleCopyUrl = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(fullApiUrl);
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  const getCurlSnippet = () => {
    const authHeader = endpoint.authRequired
      ? ' \\\n  -H "Authorization: Bearer <YOUR_MORPH_API_KEY>"'
      : "";
    if (endpoint.method === "GET") {
      return `curl -X GET "${fullApiUrl}" \\\n  -H "Accept: application/json"${authHeader}`;
    }
    const sampleBody = endpoint.requestBodySchema
      ? JSON.stringify({ query: "example" }, null, 2)
      : "{}";
    return `curl -X ${endpoint.method} "${fullApiUrl}" \\\n  -H "Content-Type: application/json" \\\n  -H "Accept: application/json"${authHeader} \\\n  -d '${sampleBody}'`;
  };

  const getJsSnippet = () => {
    const headersObj = endpoint.authRequired
      ? `{\n    "Accept": "application/json",\n    "Authorization": "Bearer <YOUR_MORPH_API_KEY>"\n  }`
      : `{ "Accept": "application/json" }`;
    return `const response = await fetch("${fullApiUrl}", {\n  method: "${endpoint.method}",\n  headers: ${headersObj},\n});\nconst data = await response.json();\nconsole.log(data);`;
  };

  const getPySnippet = () => {
    const headersLine = endpoint.authRequired
      ? `headers = {"Authorization": "Bearer <YOUR_MORPH_API_KEY>", "Accept": "application/json"}\nresponse = requests.${endpoint.method.toLowerCase()}(url, headers=headers)\n`
      : `response = requests.${endpoint.method.toLowerCase()}(url)\n`;
    return `import requests\n\nurl = "${fullApiUrl}"\n${headersLine}data = response.json()\nprint(data)`;
  };

  const getMcpSnippet = () => {
    const tool = {
      name: `morph_${endpoint.id.replace(/^ep_/, "")}`,
      description: endpoint.description,
      inputSchema: {
        type: "object",
        properties: Object.fromEntries(
          endpoint.parameters.map((p) => [
            p.name,
            { type: p.type, description: p.description || p.name },
          ])
        ),
        required: endpoint.parameters.filter((p) => p.required).map((p) => p.name),
      },
    };
    return JSON.stringify(tool, null, 2);
  };

  const handleCopySnippet = (code: string, type: string) => {
    navigator.clipboard.writeText(code);
    setCopiedSnippet(type);
    setTimeout(() => setCopiedSnippet(null), 2000);
  };

  // Method badge colors using storm palette: AEC8D0 for GET, C3D1B8 for POST, DDC38A for PUT/PATCH, E3A29E for DELETE
  const getMethodBadgeClass = (m: HttpMethod) => {
    switch (m) {
      case "GET":
        return "bg-[#AEC8D0]/15 text-[#AEC8D0] border-[#3A4A50]";
      case "POST":
        return "bg-[#C3D1B8]/15 text-[#C3D1B8] border-[#3A4A50]";
      case "PUT":
      case "PATCH":
        return "bg-[#DDC38A]/15 text-[#DDC38A] border-[#3A4A50]";
      case "DELETE":
        return "bg-[#E3A29E]/15 text-[#E3A29E] border-[#3A4A50]";
    }
  };

  const isTestable = endpoint.status === "ready" || endpoint.status === "validating";

  return (
    <div
      className={`w-full rounded-xl bg-[#202C32] border transition-all font-sans text-xs p-4 shadow-md ${
        isSelected
          ? "border-[#AEC8D0] ring-1 ring-[#AEC8D0]/40"
          : "border-[#3A4A50] hover:border-[#4B5E66]"
      }`}
    >
      {/* Top Row: Method, Path, Copy URL, and Status */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          {/* Method Badge */}
          <span
            className={`px-2 py-0.5 rounded-sm font-mono text-[11px] font-bold border ${getMethodBadgeClass(
              endpoint.method
            )}`}
          >
            {endpoint.method}
          </span>

          {/* Endpoint Path (Copyable) */}
          <code className="font-mono text-xs text-[#EDF1EE] font-semibold truncate max-w-[280px] sm:max-w-[360px] bg-[#151E23] px-2 py-0.5 rounded-sm border border-[#3A4A50]">
            {endpoint.path}
          </code>

          <button
            type="button"
            onClick={handleCopyUrl}
            className="text-[#ADBAB9] hover:text-[#EDF1EE] p-1 rounded-sm hover:bg-[#2A3940] transition-colors"
            title="Copy full API endpoint URL"
            aria-label="Copy full API endpoint URL"
          >
            {copiedUrl ? (
              <Check className="w-3.5 h-3.5 text-[#A7C4A2]" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
          </button>
        </div>

        {/* Status / Auth Badge */}
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] text-[#ADBAB9] bg-[#151E23] px-2 py-0.5 rounded-sm border border-[#3A4A50]">
            {endpoint.version}
          </span>
          <span
            className={`font-mono text-[10px] px-2 py-0.5 rounded-sm border ${
              endpoint.authRequired
                ? "bg-[#DDC38A]/15 text-[#DDC38A] border-[#DDC38A]/30"
                : "bg-[#151E23] text-[#ADBAB9] border-[#3A4A50]"
            }`}
          >
            {endpoint.authRequired ? (endpoint.authType || "API Key Required") : "No Auth"}
          </span>
          <span
            className={`font-mono text-[10px] px-2 py-0.5 rounded-sm border ${
              endpoint.status === "ready"
                ? "bg-[#A7C4A2]/15 text-[#A7C4A2] border-[#A7C4A2]/30"
                : endpoint.status === "approval_required"
                ? "bg-[#DDC38A]/15 text-[#DDC38A] border-[#DDC38A]/30"
                : "bg-[#151E23] text-[#ADBAB9] border-[#3A4A50]"
            }`}
          >
            {endpoint.status === "ready"
              ? "Live"
              : endpoint.status === "approval_required"
              ? "Draft (Approval Req)"
              : endpoint.status}
          </span>
        </div>
      </div>

      {/* Endpoint Name and Purpose */}
      <h4 className="font-semibold text-sm text-[#F4F5F7] mb-1">{endpoint.name}</h4>
      <p className="text-[#A9B0BA] leading-relaxed text-xs mb-3">{endpoint.description}</p>

      {/* Visually Separate Source Website Link */}
      <div className="p-2 rounded-lg bg-[#0B0D10] border border-white/5 flex items-center justify-between text-[11px] font-mono text-[#89929F] mb-3">
        <span className="flex items-center gap-1.5">
          <Globe className="w-3.5 h-3.5 text-[#10B981]" />
          <span>Extracted From:</span>
        </span>
        <a
          href={endpoint.sourceUrl}
          target="_blank"
          rel="noreferrer"
          className="text-[#38BDF8] hover:underline flex items-center gap-1 truncate max-w-[240px]"
        >
          <span className="truncate">{endpoint.sourceUrl}</span>
          <ExternalLink className="w-3 h-3 shrink-0" />
        </a>
      </div>

      {/* Actions Strip: Test Endpoint, Schema, Code Snippets */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-white/5">
        <div className="flex items-center gap-2">
          {/* Schema Viewer Trigger */}
          <button
            type="button"
            onClick={() => setShowSchema(!showSchema)}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#181D23] hover:bg-[#202730] border border-white/10 text-[11px] font-mono text-[#A9B0BA] hover:text-[#F4F5F7] transition-colors"
          >
            {showSchema ? (
              <ChevronDown className="w-3 h-3" />
            ) : (
              <ChevronRight className="w-3 h-3" />
            )}
            <span>Schema</span>
          </button>

          {/* Code Snippets Trigger */}
          <button
            type="button"
            onClick={() => setShowCodeSnippets(!showCodeSnippets)}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#181D23] hover:bg-[#202730] border border-white/10 text-[11px] font-mono text-[#A9B0BA] hover:text-[#F4F5F7] transition-colors"
          >
            <Code2 className="w-3 h-3 text-[#38BDF8]" />
            <span>Code</span>
          </button>
        </div>

        {/* Primary Test Endpoint Button */}
        <button
          type="button"
          onClick={() => onSelectTest(endpoint)}
          disabled={!isTestable}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all focus:outline-hidden focus:ring-1 focus:ring-[#AEC8D0] ${
            isSelected
              ? "bg-[#2A3940] text-[#C3D1B8] border border-[#AEC8D0]/40 shadow-xs"
              : isTestable
              ? "bg-[#151E23] hover:bg-[#2A3940] text-[#ADBAB9] hover:text-[#EDF1EE] border border-[#3A4A50]"
              : "bg-[#151E23] text-[#ADBAB9]/40 border border-[#3A4A50]/40 cursor-not-allowed"
          }`}
        >
          <Play className="w-3 h-3 fill-current" />
          <span>{isSelected ? "Active Tester" : "Test Endpoint"}</span>
        </button>
      </div>

      {/* Collapsible Schema Inspector */}
      {showSchema && (
        <div className="mt-3 p-3 rounded-lg bg-[#151E23] border border-[#3A4A50] font-mono text-[11px] space-y-2">
          <div className="text-[#ADBAB9] text-[10px] uppercase font-semibold">
            Parameters ({endpoint.parameters.length})
          </div>
          {endpoint.parameters.length === 0 ? (
            <div className="text-[#ADBAB9]/60 italic">No URL parameters required.</div>
          ) : (
            endpoint.parameters.map((p) => (
              <div key={p.name} className="flex items-center justify-between text-[#EDF1EE]">
                <span>{p.name}</span>
                <span className="text-[#ADBAB9]">
                  ({p.in}, {p.type}, {p.required ? "required" : "optional"})
                </span>
              </div>
            ))
          )}

          <div className="text-[#ADBAB9] text-[10px] uppercase font-semibold pt-2 border-t border-[#3A4A50]">
            Response Schema (JSON)
          </div>
          <pre className="text-[#A7C4A2] max-h-36 overflow-y-auto overflow-x-auto p-1 text-[10px]">
            {JSON.stringify(endpoint.responseSchema, null, 2)}
          </pre>
        </div>
      )}

      {/* Collapsible Code Snippets (cURL first, then JS, Python) */}
      {showCodeSnippets && (
        <div className="mt-3 p-3 rounded-lg bg-[#151E23] border border-[#3A4A50] font-mono text-[11px] space-y-2">
          <div className="flex items-center justify-between border-b border-[#3A4A50] pb-1.5">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setActiveSnippetTab("curl")}
                className={`px-2 py-0.5 rounded-sm ${
                  activeSnippetTab === "curl"
                    ? "bg-[#202C32] text-[#EDF1EE] border border-[#3A4A50]"
                    : "text-[#ADBAB9] hover:text-[#EDF1EE]"
                }`}
              >
                cURL
              </button>
              <button
                type="button"
                onClick={() => setActiveSnippetTab("js")}
                className={`px-2 py-0.5 rounded-sm ${
                  activeSnippetTab === "js"
                    ? "bg-[#202C32] text-[#EDF1EE] border border-[#3A4A50]"
                    : "text-[#ADBAB9] hover:text-[#EDF1EE]"
                }`}
              >
                JavaScript
              </button>
              <button
                type="button"
                onClick={() => setActiveSnippetTab("py")}
                className={`px-2 py-0.5 rounded-sm ${
                  activeSnippetTab === "py"
                    ? "bg-[#202C32] text-[#EDF1EE] border border-[#3A4A50]"
                    : "text-[#ADBAB9] hover:text-[#EDF1EE]"
                }`}
              >
                Python
              </button>
              <button
                type="button"
                onClick={() => setActiveSnippetTab("mcp")}
                className={`px-2 py-0.5 rounded-sm ${
                  activeSnippetTab === "mcp"
                    ? "bg-[#202C32] text-[#C3D1B8] border border-[#3A4A50] font-semibold"
                    : "text-[#ADBAB9] hover:text-[#C3D1B8]"
                }`}
              >
                MCP Tool
              </button>
            </div>

            <button
              type="button"
              onClick={() => {
                const code =
                  activeSnippetTab === "curl"
                    ? getCurlSnippet()
                    : activeSnippetTab === "js"
                    ? getJsSnippet()
                    : activeSnippetTab === "py"
                    ? getPySnippet()
                    : getMcpSnippet();
                handleCopySnippet(code, activeSnippetTab);
              }}
              className="text-[#ADBAB9] hover:text-[#EDF1EE] flex items-center gap-1 text-[10px]"
            >
              {copiedSnippet === activeSnippetTab ? (
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
          </div>

          <pre className="text-[#AEC8D0] max-h-36 overflow-y-auto overflow-x-auto p-1 text-[10px]">
            {activeSnippetTab === "curl"
              ? getCurlSnippet()
              : activeSnippetTab === "js"
              ? getJsSnippet()
              : activeSnippetTab === "py"
              ? getPySnippet()
              : getMcpSnippet()}
          </pre>
        </div>
      )}
    </div>
  );
}
