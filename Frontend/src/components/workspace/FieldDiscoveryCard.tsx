"use client";

import React from "react";
import { Check, ShieldCheck, Tag, Code2 } from "lucide-react";
import { FieldDefinition } from "@/lib/types";

interface FieldDiscoveryCardProps {
  fields: FieldDefinition[];
}

export function FieldDiscoveryCard({ fields }: FieldDiscoveryCardProps) {
  if (fields.length === 0) return null;

  return (
    <div className="w-full rounded-xl bg-[#11151A] border border-white/10 p-4 font-sans text-xs shadow-md">
      <div className="flex items-center justify-between pb-2 mb-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-[#38BDF8]/10 border border-[#38BDF8]/25 flex items-center justify-center text-[#38BDF8]">
            <Tag className="w-3.5 h-3.5" />
          </div>
          <div>
            <h4 className="font-semibold text-[#F4F5F7] text-xs">Field Discovery</h4>
            <p className="text-[11px] font-mono text-[#89929F]">
              {fields.length} typed attributes mapped from DOM
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-sm bg-[#10B981]/10 border border-[#10B981]/25 text-[10px] font-mono text-[#10B981]">
          <ShieldCheck className="w-3 h-3" />
          <span>Pydantic v2 Strict</span>
        </div>
      </div>

      <div className="space-y-2">
        {fields.map((field) => (
          <div
            key={field.name}
            className="p-2.5 rounded-lg bg-[#0B0D10] border border-white/5 flex flex-col gap-1.5"
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="font-mono font-semibold text-[#F4F5F7] text-xs">
                  {field.name}
                </span>
                <span className="font-mono text-[10px] px-1.5 py-0.2 rounded-xs bg-[#181D23] text-[#38BDF8] border border-white/5">
                  {field.type}
                </span>
                {field.required && (
                  <span className="font-mono text-[9px] px-1 rounded-xs bg-white/5 text-[#A9B0BA]">
                    required
                  </span>
                )}
              </div>

              {field.selector && (
                <code className="hidden sm:inline font-mono text-[10px] text-[#89929F] truncate max-w-[180px] bg-[#11151A] px-1.5 py-0.5 rounded-xs border border-white/5">
                  {field.selector}
                </code>
              )}
            </div>

            {field.sampleValue !== undefined && (
              <div className="flex items-center gap-1.5 text-[11px] text-[#A9B0BA] font-mono truncate">
                <span className="text-[#89929F] text-[10px]">Sample:</span>
                <span className="text-[#A7F3D0] truncate">
                  {typeof field.sampleValue === "boolean"
                    ? field.sampleValue
                      ? "true"
                      : "false"
                    : String(field.sampleValue)}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
