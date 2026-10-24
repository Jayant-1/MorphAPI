"use client";

import React, { useState } from "react";
import { Play, Copy, Check, ChevronDown, ChevronRight, Loader2, Globe, ShieldCheck } from "lucide-react";
import { EndpointDefinition, TestExecutionResult, HttpMethod } from "@/lib/types";
import { executeEndpointTest } from "@/lib/api-adapter";

interface InlineApiTesterProps {
  endpoint: EndpointDefinition;
}

export function InlineApiTester({ endpoint }: InlineApiTesterProps) {
  const supportedMethods: HttpMethod[] =
    endpoint.supportedMethods && endpoint.supportedMethods.length > 0
      ? endpoint.supportedMethods
      : [endpoint.method];

  const [selectedMethod, setSelectedMethod] = useState<HttpMethod>(supportedMethods[0] || "GET");

  // Initialize parameter values from contract
  const defaultParams: Record<string, string> = {};
  endpoint.parameters.forEach((p) => {
    defaultParams[p.name] = p.defaultValue != null ? String(p.defaultValue) : "";
  });

  const [paramValues, setParamValues] = useState<Record<string, string>>(defaultParams);
  const [requestBody, setRequestBody] = useState(
    JSON.stringify(defaultParams, null, 2)
  );
  const [showHeaders, setShowHeaders] = useState(false);
  const [headers, setHeaders] = useState<Record<string, string>>({
    Accept: "application/json",
  });
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<TestExecutionResult | null>(null);
  const [copiedResponse, setCopiedResponse] = useState(false);
  const [showResponseHeaders, setShowResponseHeaders] = useState(false);

  const handleRunTest = async () => {
    setIsRunning(true);
    try {
      const res = await executeEndpointTest(
        endpoint,
        paramValues,
        headers,
        selectedMethod === "POST" ? requestBody : undefined,
        selectedMethod
      );
      setResult(res);
    } catch (err: any) {
      setResult({
        endpointId: endpoint.id,
        status: 500,
        statusText: "Internal Error",
        durationMs: 0,
        sizeBytes: 0,
        headers: {},
        data: { error: err.message || "Failed to execute endpoint test" },
        rawText: JSON.stringify({ error: err.message }, null, 2),
        executedAt: new Date().toISOString(),
        method: selectedMethod,
        isError: true,
        errorMessage: err.message,
      });
    } finally {
      setIsRunning(false);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedResponse(true);
    setTimeout(() => setCopiedResponse(false), 2000);
  };

  return (
    <div className="w-full mt-3 pt-3 border-t border-[#3A4A50]/50 font-sans text-[14px] space-y-3.5">
      {/* Method Switcher & Target URL */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-[#10171B] p-2 rounded-lg border border-[#3A4A50]/60">
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-medium uppercase text-[#ADBAB9] tracking-wider">
            Method:
          </span>
          <div className="flex items-center gap-1">
            {supportedMethods.map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setSelectedMethod(m)}
                className={`px-2.5 py-1 rounded text-[12px] font-mono font-semibold transition-colors ${
                  selectedMethod === m
                    ? m === "GET"
                      ? "bg-[#AEC8D0] text-[#10171B]"
                      : "bg-[#C3D1B8] text-[#10171B]"
                    : "bg-[#202C32] text-[#ADBAB9] hover:text-[#EDF1EE]"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-1 text-[12px] font-mono text-[#ADBAB9] truncate">
          <Globe className="w-3.5 h-3.5 text-[#ADBAB9] shrink-0" />
          <span className="truncate">{endpoint.fullUrl || endpoint.path}</span>
        </div>
      </div>

      {/* Dynamic Parameters from Contract */}
      {endpoint.parameters.length > 0 && (
        <div className="space-y-1.5">
          <label className="text-[12px] font-medium font-sans text-[#ADBAB9] uppercase tracking-wider">
            Request Parameters ({endpoint.parameters.length})
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {endpoint.parameters.map((p) => (
              <div key={p.name} className="flex flex-col gap-1">
                <div className="flex items-center justify-between text-[12px]">
                  <span className="font-mono text-[#EDF1EE] font-medium">{p.name}</span>
                  <span className="text-[#ADBAB9] font-sans text-[11px]">
                    {p.in} · {p.type} {p.required && <span className="text-[#E3A29E]">*</span>}
                  </span>
                </div>
                {p.type === "bool" ? (
                  <select
                    value={paramValues[p.name] || ""}
                    onChange={(e) => {
                      const updated = { ...paramValues, [p.name]: e.target.value };
                      setParamValues(updated);
                      setRequestBody(JSON.stringify(updated, null, 2));
                    }}
                    className="w-full h-9 px-3 rounded-md bg-[#10171B] border border-[#3A4A50] text-[13px] font-mono text-[#EDF1EE] focus:outline-hidden focus:border-[#AEC8D0]"
                  >
                    <option value="">(default)</option>
                    <option value="true">true</option>
                    <option value="false">false</option>
                  </select>
                ) : (
                  <input
                    type="text"
                    value={paramValues[p.name] || ""}
                    onChange={(e) => {
                      const updated = { ...paramValues, [p.name]: e.target.value };
                      setParamValues(updated);
                      setRequestBody(JSON.stringify(updated, null, 2));
                    }}
                    placeholder={p.defaultValue != null && p.defaultValue !== "" ? String(p.defaultValue) : `value for ${p.name}`}
                    className="w-full h-9 px-3 rounded-md bg-[#10171B] border border-[#3A4A50] text-[13px] font-mono tracking-normal text-[#EDF1EE] placeholder:text-[#ADBAB9]/40 focus:outline-hidden focus:border-[#AEC8D0]"
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* JSON Body (for POST) */}
      {selectedMethod === "POST" && (
        <div className="space-y-1.5">
          <label className="text-[12px] font-medium font-sans text-[#ADBAB9] uppercase tracking-wider">
            POST JSON Body
          </label>
          <textarea
            value={requestBody}
            onChange={(e) => setRequestBody(e.target.value)}
            rows={3}
            className="w-full p-2.5 rounded-md bg-[#10171B] border border-[#3A4A50] text-[13px] font-mono tracking-normal text-[#EDF1EE] placeholder:text-[#ADBAB9]/40 focus:outline-hidden focus:border-[#AEC8D0] leading-relaxed resize-none"
          />
        </div>
      )}

      {/* Headers & Auth Disclosure */}
      <div>
        <button
          type="button"
          onClick={() => setShowHeaders(!showHeaders)}
          className="flex items-center gap-1.5 text-[12px] text-[#ADBAB9] hover:text-[#EDF1EE] transition-colors"
        >
          {showHeaders ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          <span>Headers & Authentication</span>
        </button>

        {showHeaders && (
          <div className="mt-2 p-3 rounded-md bg-[#10171B] border border-[#3A4A50] space-y-1.5 font-mono text-[12px] tracking-normal">
            <div className="flex items-center justify-between">
              <span className="text-[#ADBAB9]">Accept</span>
              <span className="text-[#EDF1EE]">application/json</span>
            </div>
            {endpoint.apiKey && (
              <div className="flex items-center justify-between">
                <span className="text-[#ADBAB9]">X-API-Key</span>
                <span className="text-[#EDF1EE] truncate max-w-[240px]">{endpoint.apiKey}</span>
              </div>
            )}
            <div className="text-[11px] text-[#A7C4A2] font-sans flex items-center gap-1 pt-1">
              <ShieldCheck className="w-3 h-3" />
              <span>Dev mode: API Key validation is optional in local gateway</span>
            </div>
          </div>
        )}
      </div>

      {/* Execute Test Button */}
      <div className="flex items-center justify-between pt-1">
        <button
          type="button"
          onClick={handleRunTest}
          disabled={isRunning}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-lg bg-[#C3D1B8] hover:bg-[#D5DFCD] text-[#17201C] font-medium text-[13px] font-sans transition-colors disabled:opacity-50"
        >
          {isRunning ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Play className="w-3.5 h-3.5 fill-current" />
          )}
          <span>{isRunning ? "Executing Query..." : `Send ${selectedMethod} Request`}</span>
        </button>
      </div>

      {/* Live Response Panel */}
      {result && (
        <div className="mt-3 p-3.5 rounded-xl bg-[#10171B] border border-[#3A4A50] space-y-2.5">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2.5">
              <span
                className={`px-2 py-0.5 rounded-md font-mono text-[12px] font-semibold tracking-normal ${
                  result.status >= 200 && result.status < 300
                    ? "bg-[#A7C4A2]/20 text-[#A7C4A2]"
                    : "bg-[#E3A29E]/20 text-[#E3A29E]"
                }`}
              >
                {result.status} {result.statusText}
              </span>
              <span className="text-[12px] font-mono tracking-normal text-[#ADBAB9]">
                {result.durationMs}ms
              </span>
              {result.method && (
                <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-[#202C32] text-[#AEC8D0]">
                  {result.method}
                </span>
              )}
            </div>

            <button
              type="button"
              onClick={() => handleCopy(result.rawText || JSON.stringify(result.data, null, 2))}
              className="inline-flex items-center gap-1.5 text-[12px] font-sans text-[#ADBAB9] hover:text-[#EDF1EE] transition-colors"
            >
              {copiedResponse ? <Check className="w-3.5 h-3.5 text-[#A7C4A2]" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedResponse ? "Copied" : "Copy response"}</span>
            </button>
          </div>

          {/* Formatted JSON Body */}
          <pre className="p-3 rounded-lg bg-[#151E23] border border-[#3A4A50]/60 overflow-x-auto text-[13px] font-mono tracking-normal text-[#EDF1EE] leading-relaxed max-h-60">
            {result.rawText || JSON.stringify(result.data, null, 2)}
          </pre>

          {/* Response Headers */}
          {result.headers && Object.keys(result.headers).length > 0 && (
            <div>
              <button
                type="button"
                onClick={() => setShowResponseHeaders(!showResponseHeaders)}
                className="flex items-center gap-1.5 text-[12px] font-sans text-[#ADBAB9] hover:text-[#EDF1EE] transition-colors"
              >
                {showResponseHeaders ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                <span>Response Headers ({Object.keys(result.headers).length})</span>
              </button>

              {showResponseHeaders && (
                <div className="mt-1.5 p-2.5 rounded-md bg-[#151E23] font-mono text-[11px] tracking-normal space-y-1">
                  {Object.entries(result.headers).map(([k, v]) => (
                    <div key={k} className="flex items-start justify-between gap-2 text-[#ADBAB9]">
                      <span className="text-[#ADBAB9] shrink-0">{k}:</span>
                      <span className="text-[#EDF1EE] truncate max-w-[280px]">{v}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
