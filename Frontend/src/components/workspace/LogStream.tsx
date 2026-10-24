"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Terminal,
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
  ArrowDown,
  Filter,
} from "lucide-react";
import { LogEntry } from "@/lib/types";

interface LogStreamProps {
  logs: LogEntry[];
}

export function LogStream({ logs }: LogStreamProps) {
  const [isOpen, setIsOpen] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);
  const [hasNewActivity, setHasNewActivity] = useState(false);
  const [copied, setCopied] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<string>("all");

  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logic with user scroll detection
  useEffect(() => {
    if (!isOpen) return;

    const el = scrollRef.current;
    if (!el) return;

    if (autoScroll) {
      el.scrollTop = el.scrollHeight;
      setHasNewActivity(false);
    } else {
      setHasNewActivity(true);
    }
  }, [logs, autoScroll, isOpen]);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;

    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    if (isNearBottom) {
      setAutoScroll(true);
      setHasNewActivity(false);
    } else {
      setAutoScroll(false);
    }
  };

  const handleCopyLogs = () => {
    const text = logs
      .map((l) => `[${l.timestamp}] [${l.severity.toUpperCase()}] [${l.source}] ${l.message}`)
      .join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const filteredLogs = logs.filter((log) => {
    if (severityFilter === "all") return true;
    return log.severity === severityFilter;
  });

  return (
    <div className="w-full rounded-xl bg-[#11151A] border border-white/10 overflow-hidden font-sans shadow-md text-xs">
      {/* Header / Disclosure Control */}
      <div className="px-4 py-2.5 bg-[#181D23] flex items-center justify-between border-b border-white/10 select-none">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 text-[#F4F5F7] font-semibold hover:text-[#10B981] transition-colors"
          aria-expanded={isOpen}
        >
          {isOpen ? (
            <ChevronDown className="w-4 h-4 text-[#89929F]" />
          ) : (
            <ChevronRight className="w-4 h-4 text-[#89929F]" />
          )}
          <Terminal className="w-3.5 h-3.5 text-[#10B981]" />
          <span>Technical Telemetry Logs</span>
          <span className="font-mono text-[10px] text-[#89929F] px-1.5 py-0.2 rounded-xs bg-[#0B0D10] border border-white/5">
            {logs.length}
          </span>
        </button>

        {isOpen && (
          <div className="flex items-center gap-2">
            {/* Severity Filter */}
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-[#0B0D10] text-[#A9B0BA] font-mono text-[11px] px-2 py-0.5 rounded-md border border-white/10 focus:outline-hidden"
              aria-label="Filter logs by severity"
            >
              <option value="all">All severities</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
            </select>

            {/* Copy Logs Button */}
            <button
              type="button"
              onClick={handleCopyLogs}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#0B0D10] hover:bg-white/5 border border-white/10 text-[11px] font-mono text-[#A9B0BA] hover:text-[#F4F5F7] transition-colors"
              title="Copy all technical logs to clipboard"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-[#10B981]" />
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
        )}
      </div>

      {/* Log Output Stream Box: 220-280px tall bounded height */}
      {isOpen && (
        <div className="relative">
          <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="p-3 bg-[#070709] font-mono text-[11px] h-[240px] overflow-y-auto space-y-1.5 select-text"
          >
            {filteredLogs.length === 0 ? (
              <div className="text-[#6A7382] p-2 italic">No logs recorded yet.</div>
            ) : (
              filteredLogs.map((log) => (
                <div key={log.id} className="flex items-start gap-2 leading-relaxed">
                  <span className="text-[#6A7382] shrink-0 select-none">[{log.timestamp}]</span>
                  <span
                    className={`shrink-0 font-semibold text-[10px] px-1 py-0.2 rounded-xs select-none ${
                      log.severity === "error"
                        ? "bg-[#EF4444]/20 text-[#F87171]"
                        : log.severity === "warning"
                        ? "bg-[#F59E0B]/20 text-[#FBBF24]"
                        : "bg-white/5 text-[#38BDF8]"
                    }`}
                  >
                    {log.source}
                  </span>
                  <span
                    className={`break-all ${
                      log.severity === "error"
                        ? "text-[#F87171]"
                        : log.severity === "warning"
                        ? "text-[#FBBF24]"
                        : "text-[#C2C9D6]"
                    }`}
                  >
                    {log.message}
                  </span>
                </div>
              ))
            )}
          </div>

          {/* New Activity Floating Pill when scrolled up */}
          {hasNewActivity && (
            <button
              type="button"
              onClick={() => {
                setAutoScroll(true);
                const el = scrollRef.current;
                if (el) el.scrollTop = el.scrollHeight;
              }}
              className="absolute bottom-3 left-1/2 -translate-x-1/2 inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#10B981] text-[#070709] font-semibold text-xs shadow-lg animate-bounce"
            >
              <ArrowDown className="w-3 h-3" />
              <span>New activity</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
