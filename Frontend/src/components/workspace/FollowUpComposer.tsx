"use client";

import React, { useState } from "react";
import { Send, CornerDownLeft, Sparkles, Loader2 } from "lucide-react";

interface FollowUpComposerProps {
  isProcessing?: boolean;
  onSendFollowUp: (prompt: string) => void;
}

export function FollowUpComposer({
  isProcessing = false,
  onSendFollowUp,
}: FollowUpComposerProps) {
  const [input, setInput] = useState("");

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isProcessing) return;
    onSendFollowUp(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full pt-3 border-t border-[#3A4A50] flex items-center gap-2 font-sans select-none"
    >
      <div className="relative flex-1">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Refine extraction: e.g. 'Format price as float' or 'Add stock count'..."
          disabled={isProcessing}
          className="w-full h-10 pl-3.5 pr-10 rounded-xl bg-[#202C32] border border-[#3A4A50] hover:border-[#4B5E66] focus:border-[#AEC8D0] focus:ring-1 focus:ring-[#AEC8D0] text-xs text-[#EDF1EE] placeholder:text-[#ADBAB9] focus:outline-hidden transition-all disabled:opacity-50"
        />
        <div className="absolute right-2.5 top-1/2 -translate-y-1/2 hidden sm:flex items-center gap-1 text-[10px] font-mono text-[#ADBAB9] pointer-events-none">
          <CornerDownLeft className="w-3 h-3" />
        </div>
      </div>

      <button
        type="submit"
        disabled={!input.trim() || isProcessing}
        className="h-10 px-3.5 rounded-xl bg-[#C3D1B8] hover:bg-[#D5DFCD] active:translate-y-0.5 text-[#17201C] font-semibold text-xs transition-all disabled:opacity-40 disabled:pointer-events-none flex items-center gap-1.5 shrink-0 focus:outline-hidden focus:ring-2 focus:ring-[#AEC8D0]"
        aria-label="Send follow-up instruction"
      >
        {isProcessing ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-[#17201C]" />
        ) : (
          <>
            <Send className="w-3.5 h-3.5 text-[#17201C]" />
            <span className="hidden sm:inline">Refine</span>
          </>
        )}
      </button>
    </form>
  );
}
