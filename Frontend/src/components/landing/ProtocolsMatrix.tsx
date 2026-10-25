"use client";

import React, { useState } from "react";
import { Terminal, Layers, Copy, Check } from "lucide-react";

export function ProtocolsMatrix() {
  const [activeProtocol, setActiveProtocol] = useState<"rest" | "mcp">("rest");
  const [copied, setCopied] = useState(false);

  const snippets = {
    rest: {
      title: "Standard REST API Gateway",
      format: "cURL / HTTP 1.1",
      code: `# Fetch extracted data deterministically
curl -X GET "http://localhost:8001/v2/api/default/fastapi-releases" \\
  -H "Accept: application/json" \\
  -H "X-Bypass-Cache: false"

# Response payload: 200 OK (38ms)
{
  "data": [
    { "version": "0.115.6", "releaseDate": "2026-10-18T10:00:00Z" }
  ],
  "meta": { "config_version": 2, "cached": false }
}`,
    },
    mcp: {
      title: "Model Context Protocol (MCP) Server",
      format: "claude_desktop_config.json / Cursor AI",
      code: `{
  "mcpServers": {
    "morphapi": {
      "command": "npx",
      "args": [
        "-y",
        "@morphapi/mcp-server",
        "--endpoint",
        "http://localhost:8001/mcp/sse"
      ]
    }
  }
}

// AI Agent calls tool automatically:
// tool_call: extract_fastapi_releases() -> returns verified DOM objects`,
    },
  };

  const copyCode = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="protocols" className="py-16 md:py-20 border-b border-[#1A1A20] bg-[#070709] font-sans">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-10 space-y-3">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            One Integration. Every Protocol.
          </h2>
          <p className="text-sm sm:text-base text-[#A1A1AA]">
            Consume live web data via standard REST JSON or native Model Context Protocol (MCP) tools for Claude & Cursor.
          </p>
        </div>

        {/* Clean Protocol Switcher */}
        <div className="border border-[#22222A] bg-[#0C0C0F] rounded-sm overflow-hidden font-mono text-xs shadow-lg">
          {/* Top Switcher Strip */}
          <div className="flex flex-wrap items-center justify-between border-b border-[#1E1E26] bg-[#101014] p-3 sm:px-4">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveProtocol("rest")}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-sm text-xs font-semibold transition-all ${
                  activeProtocol === "rest"
                    ? "bg-[#1E1E26] text-white border border-[#33333F]"
                    : "text-[#71717A] hover:text-white"
                }`}
              >
                <Terminal className="w-3.5 h-3.5 text-[#10B981]" />
                <span>REST API</span>
              </button>

              <button
                onClick={() => setActiveProtocol("mcp")}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-sm text-xs font-semibold transition-all ${
                  activeProtocol === "mcp"
                    ? "bg-[#1E1E26] text-white border border-[#33333F]"
                    : "text-[#71717A] hover:text-white"
                }`}
              >
                <Layers className="w-3.5 h-3.5 text-[#38BDF8]" />
                <span>MCP Server (AI Agents)</span>
              </button>
            </div>

            <button
              onClick={() => copyCode(snippets[activeProtocol].code)}
              className="flex items-center gap-1.5 px-3 py-1 rounded-sm bg-[#16161C] hover:bg-[#202028] border border-[#272730] text-white text-xs font-medium transition-colors"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-[#10B981]" />
              ) : (
                <Copy className="w-3.5 h-3.5 text-[#71717A]" />
              )}
              <span>{copied ? "Copied" : "Copy"}</span>
            </button>
          </div>

          {/* Code Viewer */}
          <div className="p-4 sm:p-5 bg-[#08080A]">
            <pre className="text-[#34D399] overflow-x-auto text-xs leading-relaxed font-mono">
              {snippets[activeProtocol].code}
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
}
