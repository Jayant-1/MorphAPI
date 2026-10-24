"use client";

import React, { useState } from "react";
import { Search, Layers, Server, AlertCircle } from "lucide-react";
import { EndpointDefinition } from "@/lib/types";
import { EndpointCard } from "./EndpointCard";

interface EndpointCollectionProps {
  endpoints: EndpointDefinition[];
  selectedEndpointId?: string;
  onSelectTest: (endpoint: EndpointDefinition) => void;
}

export function EndpointCollection({
  endpoints,
  selectedEndpointId,
  onSelectTest,
}: EndpointCollectionProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredEndpoints = endpoints.filter((ep) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      ep.name.toLowerCase().includes(q) ||
      ep.path.toLowerCase().includes(q) ||
      ep.method.toLowerCase().includes(q)
    );
  });

  return (
    <div className="w-full flex flex-col gap-3 font-sans">
      {/* Header with real count and search */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-1 border-b border-[#3A4A50]">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-[#C3D1B8]/15 border border-[#C3D1B8]/30 flex items-center justify-center text-[#C3D1B8]">
            <Server className="w-3.5 h-3.5" />
          </div>
          <h3 className="font-semibold text-sm text-[#EDF1EE]">
            Active Endpoints
            <span className="ml-2 font-mono text-xs font-normal text-[#ADBAB9] px-2 py-0.5 rounded-full bg-[#151E23] border border-[#3A4A50]">
              {endpoints.length} {endpoints.length === 1 ? "endpoint" : "endpoints"}
            </span>
          </h3>
        </div>

        {endpoints.length > 2 && (
          <div className="relative w-full sm:w-48">
            <Search className="w-3 h-3 text-[#ADBAB9] absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter routes..."
              className="w-full h-7 pl-7 pr-2.5 rounded-lg bg-[#202C32] border border-[#3A4A50] text-xs font-mono text-[#EDF1EE] placeholder:text-[#ADBAB9] focus:outline-hidden focus:border-[#AEC8D0]"
            />
          </div>
        )}
      </div>

      {/* Endpoint List or Zero-Endpoints State */}
      {endpoints.length === 0 ? (
        <div className="w-full p-8 rounded-xl bg-[#202C32] border border-[#3A4A50] text-center flex flex-col items-center justify-center gap-2">
          <div className="w-10 h-10 rounded-xl bg-[#151E23] border border-[#3A4A50] flex items-center justify-center text-[#ADBAB9] mb-1">
            <AlertCircle className="w-5 h-5" />
          </div>
          <h4 className="font-semibold text-[#EDF1EE] text-sm">No Endpoints Generated</h4>
          <p className="text-xs text-[#ADBAB9] max-w-sm leading-relaxed">
            The target website does not appear to contain items matching your request. Try refining your prompt or verifying that the page is accessible.
          </p>
        </div>
      ) : filteredEndpoints.length === 0 ? (
        <div className="w-full p-6 rounded-xl bg-[#202C32] border border-[#3A4A50] text-center text-xs text-[#ADBAB9]">
          No endpoints match &quot;{searchQuery}&quot;. Clear search to view all {endpoints.length} routes.
        </div>
      ) : (
        <div className="space-y-3">
          {filteredEndpoints.map((ep) => (
            <EndpointCard
              key={ep.id}
              endpoint={ep}
              isSelected={ep.id === selectedEndpointId}
              onSelectTest={onSelectTest}
            />
          ))}
        </div>
      )}
    </div>
  );
}
