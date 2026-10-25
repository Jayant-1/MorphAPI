"use client";

import React, { useState } from "react";
import {
  Play,
  Square,
  Sliders,
  Send,
  AlertCircle,
  AlertTriangle,
  FileCode,
  Layers,
  Sparkles,
} from "lucide-react";
import { EndpointDefinition, TestExecutionResult } from "@/lib/types";
import { executeEndpointTest } from "@/lib/api-adapter";
import { ResponseViewer } from "./ResponseViewer";

interface ApiTestPanelProps {
  endpoint: EndpointDefinition;
}

interface EndpointTestState {
  paramValues: Record<string, string>;
  headers: Record<string, string>;
  requestBody: string;
  testResult: TestExecutionResult | null;
  activeTab: "params" | "headers" | "body";
}

export function ApiTestPanel({ endpoint }: ApiTestPanelProps) {
  // Store per-endpoint test state keyed by stable ID and version
  const [endpointStates, setEndpointStates] = useState<Record<string, EndpointTestState>>({});
  const [bodyError, setBodyError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const endpointKey = `${endpoint.id}:${endpoint.version}`;

  // Default parameters for this endpoint
  const defaultParams: Record<string, string> = {};
  endpoint.parameters.forEach((p) => {
    defaultParams[p.name] = p.defaultValue != null ? String(p.defaultValue) : "";
  });

  const defaultBody = endpoint.requestBodySchema
    ? JSON.stringify(
        {
          query: "example search",
          sort_by: "price_asc",
        },
        null,
        2
      )
    : "";

  const currentState: EndpointTestState = endpointStates[endpointKey] || {
    paramValues: defaultParams,
    headers: {
      Accept: "application/json",
      "X-Bypass-Cache": "false",
    },
    requestBody: defaultBody,
    testResult: null,
    activeTab: "params",
  };

  const updateCurrentState = (updates: Partial<EndpointTestState>) => {
    setEndpointStates((prev) => {
      const existing = prev[endpointKey] || currentState;
      return {
        ...prev,
        [endpointKey]: {
          ...existing,
          ...updates,
        },
      };
    });
  };

  const activeTab = currentState.activeTab;
  const paramValues = currentState.paramValues;
  const headers = currentState.headers;
  const requestBody = currentState.requestBody;
  const testResult = currentState.testResult;

  // Construct resolved URL with query and path parameters
  const constructResolvedUrl = () => {
    let resolved = endpoint.path;

    // Replace path parameters like {id}
    Object.entries(paramValues).forEach(([k, v]) => {
      resolved = resolved.replace(`{${k}}`, encodeURIComponent(v || `:${k}`));
    });

    // Append query parameters
    const queryParams = new URLSearchParams();
    endpoint.parameters
      .filter((p) => p.in === "query" && paramValues[p.name])
      .forEach((p) => {
        queryParams.set(p.name, paramValues[p.name]);
      });

    const queryString = queryParams.toString();
    const finalPath = queryString ? `${resolved}?${queryString}` : resolved;
    const baseUrl = typeof window !== "undefined" ? (process.env.NEXT_PUBLIC_MORPHAPI_V2_URL || "http://localhost:8001") : "http://localhost:8001";
    return `${baseUrl}${finalPath}`;
  };

  const handleRunTest = async () => {
    if (isRunning) return;

    // Validate body if POST/PUT
    if (endpoint.method === "POST" || endpoint.method === "PUT") {
      if (requestBody.trim()) {
        try {
          JSON.parse(requestBody);
          setBodyError(null);
        } catch {
          setBodyError("Invalid JSON body format.");
          updateCurrentState({ activeTab: "body" });
          return;
        }
      }
    }

    setIsRunning(true);
    try {
      const result = await executeEndpointTest(
        endpoint,
        paramValues,
        headers,
        requestBody
      );
      updateCurrentState({ testResult: result });
    } finally {
      setIsRunning(false);
    }
  };

  const hasParams = endpoint.parameters.length > 0;
  const hasBody = endpoint.method === "POST" || endpoint.method === "PUT";
  const hasSideEffects =
    endpoint.method === "POST" ||
    endpoint.method === "PUT" ||
    endpoint.method === "PATCH" ||
    endpoint.method === "DELETE";

  return (
    <div className="w-full flex flex-col gap-4 font-sans text-xs">
      {/* Test Runner Container */}
      <div className="w-full rounded-xl bg-[#202C32] border border-[#3A4A50] p-4 shadow-md flex flex-col gap-3">
        {/* Side-Effect Warning Banner if mutating method */}
        {hasSideEffects && (
          <div className="flex items-center gap-2 p-2.5 rounded-lg bg-[#DDC38A]/15 border border-[#DDC38A]/30 text-[11px] font-mono text-[#DDC38A]">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-[#DDC38A]" />
            <span>
              Side-Effect Notice: Executing this {endpoint.method} request triggers mutation operations on downstream systems. Verify your payload before running.
            </span>
          </div>
        )}

        {/* Title and resolved URL bar */}
        <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-[#3A4A50]">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold text-xs text-[#C3D1B8]">TEST BENCH</span>
              <span className="text-[#ADBAB9]">·</span>
              <span className="font-semibold text-xs text-[#EDF1EE]">{endpoint.name}</span>
            </div>
            <div className="text-[11px] font-mono text-[#ADBAB9] mt-0.5 truncate max-w-[480px]">
              {constructResolvedUrl()}
            </div>
          </div>

          {/* Run / Cancel Button: Pale Sage with dark text for main action */}
          <div className="flex items-center gap-2">
            {isRunning ? (
              <button
                type="button"
                onClick={() => setIsRunning(false)}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#151E23] hover:bg-[#2A3940] border border-[#3A4A50] text-[#E3A29E] font-semibold text-xs transition-colors focus:outline-hidden focus:ring-1 focus:ring-[#AEC8D0]"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
                <span>Cancel</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={handleRunTest}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-[#C3D1B8] hover:bg-[#D5DFCD] active:translate-y-0.5 text-[#17201C] font-bold text-xs shadow-sm transition-all focus:outline-hidden focus:ring-2 focus:ring-[#AEC8D0]"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>{hasSideEffects ? `Run Test (${endpoint.method})` : "Run Test"}</span>
              </button>
            )}
          </div>
        </div>

        {/* Tab Selection: Params, Headers, Body */}
        <div className="flex items-center gap-1 border-b border-[#3A4A50] pb-1 font-mono text-[11px]">
          <button
            type="button"
            onClick={() => updateCurrentState({ activeTab: "params" })}
            className={`px-3 py-1 rounded-sm transition-colors ${
              activeTab === "params"
                ? "bg-[#151E23] text-[#C3D1B8] border border-[#3A4A50] font-semibold"
                : "text-[#ADBAB9] hover:text-[#EDF1EE]"
            }`}
          >
            Parameters {hasParams && `(${endpoint.parameters.length})`}
          </button>

          <button
            type="button"
            onClick={() => updateCurrentState({ activeTab: "headers" })}
            className={`px-3 py-1 rounded-sm transition-colors ${
              activeTab === "headers"
                ? "bg-[#151E23] text-[#C3D1B8] border border-[#3A4A50] font-semibold"
                : "text-[#ADBAB9] hover:text-[#EDF1EE]"
            }`}
          >
            Headers (2)
          </button>

          {hasBody && (
            <button
              type="button"
              onClick={() => updateCurrentState({ activeTab: "body" })}
              className={`px-3 py-1 rounded-sm transition-colors ${
                activeTab === "body"
                  ? "bg-[#151E23] text-[#C3D1B8] border border-[#3A4A50] font-semibold"
                  : "text-[#ADBAB9] hover:text-[#EDF1EE]"
              }`}
            >
              Body {bodyError && "!"}
            </button>
          )}
        </div>

        {/* Parameters Tab Form */}
        {activeTab === "params" && (
          <div className="space-y-2 pt-1 font-mono">
            {!hasParams ? (
              <div className="text-[#ADBAB9]/70 italic text-xs py-2">
                This endpoint does not require any parameters. Click &quot;Run Test&quot; directly.
              </div>
            ) : (
              endpoint.parameters.map((p) => (
                <div
                  key={p.name}
                  className="p-2.5 rounded-lg bg-[#151E23] border border-[#3A4A50] flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <div className="min-w-[140px]">
                    <div className="font-semibold text-xs text-[#EDF1EE] flex items-center gap-1">
                      <span>{p.name}</span>
                      {p.required && <span className="text-[#E3A29E]">*</span>}
                    </div>
                    <div className="text-[10px] text-[#ADBAB9]">
                      {p.in} · {p.type}
                    </div>
                  </div>

                  <input
                    type="text"
                    value={paramValues[p.name] || ""}
                    onChange={(e) =>
                      updateCurrentState({
                        paramValues: { ...paramValues, [p.name]: e.target.value },
                      })
                    }
                    placeholder={p.defaultValue != null ? String(p.defaultValue) : "value"}
                    className="flex-1 max-w-sm h-7 px-2.5 rounded-md bg-[#202C32] border border-[#3A4A50] text-xs font-mono text-[#EDF1EE] placeholder:text-[#ADBAB9] focus:outline-hidden focus:border-[#AEC8D0] focus:ring-1 focus:ring-[#AEC8D0]"
                  />
                </div>
              ))
            )}
          </div>
        )}

        {/* Headers Tab */}
        {activeTab === "headers" && (
          <div className="space-y-2 pt-1 font-mono text-[11px]">
            {Object.entries(headers).map(([k, v]) => (
              <div
                key={k}
                className="p-2 rounded-lg bg-[#151E23] border border-[#3A4A50] flex items-center justify-between gap-2"
              >
                <span className="text-[#ADBAB9] font-semibold">{k}</span>
                <input
                  type="text"
                  value={v}
                  onChange={(e) =>
                    updateCurrentState({
                      headers: { ...headers, [k]: e.target.value },
                    })
                  }
                  className="max-w-xs h-7 px-2 rounded-md bg-[#202C32] border border-[#3A4A50] text-xs font-mono text-[#EDF1EE] focus:outline-hidden focus:border-[#AEC8D0]"
                />
              </div>
            ))}
          </div>
        )}

        {/* Body Tab */}
        {activeTab === "body" && hasBody && (
          <div className="space-y-2 pt-1 font-mono">
            {bodyError && (
              <div className="text-[#E3A29E] flex items-center gap-1 text-xs">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>{bodyError}</span>
              </div>
            )}
            <textarea
              value={requestBody}
              onChange={(e) => {
                updateCurrentState({ requestBody: e.target.value });
                setBodyError(null);
              }}
              rows={6}
              className="w-full p-2.5 rounded-lg bg-[#151E23] border border-[#3A4A50] text-xs font-mono text-[#EDF1EE] placeholder:text-[#ADBAB9] focus:outline-hidden focus:border-[#AEC8D0]"
              placeholder="Enter JSON request payload"
            />
          </div>
        )}
      </div>

      {/* Response Display */}
      <ResponseViewer result={testResult} isRunning={isRunning} />
    </div>
  );
}
