"use client";

import React, { useState, useRef, useEffect } from "react";
import { Link2, ArrowUp, AlertCircle, Mic, Loader2 } from "lucide-react";

interface ChatComposerProps {
  mode: "initial" | "followup";
  initialUrl?: string;
  initialPrompt?: string;
  isSubmitting?: boolean;
  onSubmitInitial?: (url: string, prompt: string) => void;
  onSubmitFollowUp?: (prompt: string) => void;
  onSelectSample?: (url: string, prompt: string) => void;
}

export function ChatComposer({
  mode,
  initialUrl = "",
  initialPrompt = "",
  isSubmitting = false,
  onSubmitInitial,
  onSubmitFollowUp,
  onSelectSample,
}: ChatComposerProps) {
  const [url, setUrl] = useState(initialUrl);
  const [prompt, setPrompt] = useState(initialPrompt);
  const [urlError, setUrlError] = useState<string | null>(null);
  const [promptError, setPromptError] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [isRequestingMic, setIsRequestingMic] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);
  const isComposingRef = useRef(false);

  const urlInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  const cleanupAudio = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
      recognitionRef.current = null;
    }
    if (mediaStreamRef.current) {
      try {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      } catch {
        // ignore
      }
      mediaStreamRef.current = null;
    }
    setIsListening(false);
    setIsRequestingMic(false);
  };

  // Clean up recognition and media stream on unmount
  useEffect(() => {
    return () => {
      cleanupAudio();
    };
  }, []);

  const toggleListening = async () => {
    if (isListening || isRequestingMic) {
      cleanupAudio();
      return;
    }

    setMicError(null);
    if (typeof window === "undefined") return;

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setMicError("Microphone access is not supported by your browser environment.");
      setTimeout(() => setMicError(null), 4000);
      return;
    }

    setIsRequestingMic(true);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const SpeechRecognition =
        (window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition;

      if (!SpeechRecognition) {
        setIsListening(true);
        setIsRequestingMic(false);
        setMicError("Microphone connected. (Live transcription requires Chrome/Edge/Safari)");
        setTimeout(() => setMicError(null), 5000);
        return;
      }

      try {
        stream.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
      } catch {
        // ignore
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onstart = () => {
        setIsListening(true);
        setIsRequestingMic(false);
      };

      recognition.onresult = (event: any) => {
        let transcript = "";
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        if (transcript.trim()) {
          setPrompt(transcript.trim());
          if (promptError) setPromptError(null);
        }
      };

      recognition.onerror = (event: any) => {
        if (event.error === "not-allowed" || event.error === "permission-denied") {
          setMicError("Microphone permission denied.");
        } else if (event.error !== "no-speech") {
          setMicError(`Microphone issue: ${event.error}`);
        }
        cleanupAudio();
        setTimeout(() => setMicError(null), 4000);
      };

      recognition.onend = () => {
        setIsListening(false);
        setIsRequestingMic(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch {
      cleanupAudio();
      setMicError("Unable to access microphone.");
      setTimeout(() => setMicError(null), 4000);
    }
  };

  // Sync initial values
  useEffect(() => {
    if (initialUrl) setUrl(initialUrl);
  }, [initialUrl]);

  useEffect(() => {
    if (initialPrompt) setPrompt(initialPrompt);
  }, [initialPrompt]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      const scrollHeight = textareaRef.current.scrollHeight;
      const maxHeight = mode === "initial" ? 220 : 160;
      textareaRef.current.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
    }
  }, [prompt, mode]);

  const validateUrl = (val: string): boolean => {
    const trimmed = val.trim();
    if (!trimmed) {
      setUrlError("Enter a website URL.");
      return false;
    }
    try {
      const parsed = new URL(trimmed.startsWith("http") ? trimmed : `https://${trimmed}`);
      if (!parsed.hostname || !parsed.hostname.includes(".")) {
        setUrlError("Enter a valid web domain.");
        return false;
      }
      setUrlError(null);
      return true;
    } catch {
      setUrlError("Invalid URL format.");
      return false;
    }
  };

  const validatePrompt = (val: string): boolean => {
    const trimmed = val.trim();
    if (!trimmed) {
      setPromptError(mode === "initial" ? "Describe the data you want to extract." : "Enter a follow-up request.");
      return false;
    }
    setPromptError(null);
    return true;
  };

  const handleSend = () => {
    if (isSubmitting) return;

    if (mode === "initial") {
      const isUrlOk = validateUrl(url);
      const isPromptOk = validatePrompt(prompt);

      if (!isUrlOk) {
        urlInputRef.current?.focus();
        return;
      }
      if (!isPromptOk) {
        textareaRef.current?.focus();
        return;
      }

      const formattedUrl = url.trim().startsWith("http") ? url.trim() : `https://${url.trim()}`;
      onSubmitInitial?.(formattedUrl, prompt.trim());
    } else {
      const isPromptOk = validatePrompt(prompt);
      if (!isPromptOk) {
        textareaRef.current?.focus();
        return;
      }
      onSubmitFollowUp?.(prompt.trim());
      setPrompt("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Respect IME composition for Asian language input
    if (isComposingRef.current || e.nativeEvent.isComposing) return;

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const hasValidInput = mode === "initial" ? url.trim().length > 0 && prompt.trim().length > 0 : prompt.trim().length > 0;

  if (mode === "initial") {
    return (
      <div className="w-full max-w-[760px] flex flex-col items-center">
        {/* Initial Heading: Syne, 34-38px desktop, 28px mobile, weight 600, leading 1.15, -0.02em */}
        <h1 className="font-syne font-semibold text-[28px] sm:text-[34px] md:text-[38px] leading-[1.15] tracking-[-0.02em] text-[#EDF1EE] mb-6 text-center">
          What would you like to extract?
        </h1>

        {/* Combined Surface: Nearly opaque #202C32/98 to prevent clouds interfering with text */}
        <div className="w-full rounded-2xl bg-[#202C32]/98 backdrop-blur-md border border-[#3A4A50] shadow-[0_8px_32px_rgba(0,0,0,0.5)] flex flex-col focus-within:border-[#AEC8D0] transition-all">
          {/* URL Row: IBM Plex Mono 13-14px */}
          <div className="flex items-center px-4 pt-3.5 pb-1 gap-2.5">
            <Link2 className="w-4 h-4 text-[#ADBAB9] shrink-0" />
            <input
              ref={urlInputRef}
              type="url"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                if (urlError) validateUrl(e.target.value);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  textareaRef.current?.focus();
                }
              }}
              placeholder="https://example.com"
              disabled={isSubmitting}
              className="w-full bg-transparent text-[#EDF1EE] placeholder:text-[#ADBAB9]/60 text-[13px] sm:text-[14px] border-0 border-none outline-none focus:outline-none focus:ring-0 font-mono tracking-normal"
              aria-label="Website URL"
            />
            {urlError && (
              <span className="text-[12px] text-[#E3A29E] flex items-center gap-1 shrink-0 font-sans">
                <AlertCircle className="w-3.5 h-3.5" />
                {urlError}
              </span>
            )}
          </div>

          {/* Request Textarea & Send Button: Uncut Sans 16px, weight 400, line height 1.65 */}
          <div className="relative px-4 pt-1 pb-14">
            <textarea
              ref={textareaRef}
              value={prompt}
              onChange={(e) => {
                setPrompt(e.target.value);
                if (promptError) validatePrompt(e.target.value);
              }}
              onKeyDown={handleKeyDown}
              onCompositionStart={() => {
                isComposingRef.current = true;
              }}
              onCompositionEnd={() => {
                isComposingRef.current = false;
              }}
              placeholder="Describe the data you want from this website…"
              disabled={isSubmitting}
              rows={3}
              className="w-full bg-transparent text-[#EDF1EE] placeholder:text-[#ADBAB9]/70 font-sans text-[16px] font-normal leading-[1.65] resize-none border-0 border-none outline-none focus:outline-none focus:ring-0"
              aria-label="Extraction request description"
            />

            {(promptError || micError) && (
              <span className="absolute bottom-3 left-4 text-[12px] text-[#E3A29E] flex items-center gap-1 font-sans">
                <AlertCircle className="w-3.5 h-3.5" />
                {promptError || micError}
              </span>
            )}

            {/* Controls Row: Mic button beside Build API action button */}
            <div className="absolute bottom-3 right-3 flex items-center gap-2">
              <button
                type="button"
                onClick={toggleListening}
                disabled={isSubmitting}
                className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
                  isListening
                    ? "bg-[#A7C4A2]/20 text-[#A7C4A2] border border-[#A7C4A2]/50 animate-pulse"
                    : "bg-[#151E23] hover:bg-[#2A3940] border border-[#3A4A50] text-[#ADBAB9] hover:text-[#EDF1EE]"
                }`}
                title={isListening ? "Listening... click to stop" : "Speak to enter requirements"}
                aria-label={isListening ? "Stop voice input" : "Start voice input"}
              >
                <Mic className={`w-3.5 h-3.5 ${isListening ? "animate-pulse" : ""}`} />
              </button>

              <button
                type="button"
                onClick={handleSend}
                disabled={!hasValidInput || isSubmitting}
                className={`h-8 px-3.5 rounded-lg flex items-center gap-1.5 font-sans text-[13px] font-semibold transition-all ${
                  hasValidInput && !isSubmitting
                    ? "bg-[#C3D1B8] text-[#17201C] hover:bg-[#D5DFCD] cursor-pointer shadow-sm"
                    : "bg-[#2A3940] text-[#ADBAB9]/40 cursor-not-allowed"
                }`}
                aria-label="Build API"
              >
                <span>Build API</span>
                <ArrowUp className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Discreet sample prompts: Uncut Sans 13-14px */}
        {onSelectSample && (
          <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-[13px] sm:text-[14px] text-[#ADBAB9] font-sans">
            <span>Try a sample:</span>
            <button
              type="button"
              onClick={() => onSelectSample("http://localhost:8001/demo/mock-store", "Extract product names, prices, and links.")}
              className="text-[#C3D1B8] hover:text-[#D5DFCD] underline decoration-[#3A4A50] hover:decoration-[#C3D1B8] transition-colors font-medium"
            >
              Mock Store (:8001)
            </button>
            <span>·</span>
            <button
              type="button"
              onClick={() => onSelectSample("https://news.ycombinator.com", "Extract top stories with title, URL, and author.")}
              className="text-[#EDF1EE] hover:text-[#C3D1B8] underline decoration-[#3A4A50] hover:decoration-[#C3D1B8] transition-colors"
            >
              Hacker News
            </button>
            <span>·</span>
            <button
              type="button"
              onClick={() => onSelectSample("https://books.toscrape.com", "Extract product names, prices, and availability status.")}
              className="text-[#EDF1EE] hover:text-[#C3D1B8] underline decoration-[#3A4A50] hover:decoration-[#C3D1B8] transition-colors"
            >
              Books Catalogue
            </button>
          </div>
        )}
      </div>
    );
  }

  // Follow-up Mode (pinned to bottom of active conversation)
  return (
    <div className="w-full max-w-[780px] mx-auto px-4 sm:px-0 font-sans">
      <div className="w-full rounded-2xl bg-[#202C32] border border-[#3A4A50] shadow-xl flex flex-col relative focus-within:border-[#AEC8D0] transition-all p-3 sm:p-3.5 pb-11">
        <textarea
          ref={textareaRef}
          value={prompt}
          onChange={(e) => {
            setPrompt(e.target.value);
            if (promptError) validatePrompt(e.target.value);
          }}
          onKeyDown={handleKeyDown}
          onCompositionStart={() => {
            isComposingRef.current = true;
          }}
          onCompositionEnd={() => {
            isComposingRef.current = false;
          }}
          placeholder="Ask a follow-up or refine endpoints…"
          disabled={isSubmitting}
          rows={1}
          className="w-full bg-transparent text-[#EDF1EE] placeholder:text-[#ADBAB9]/70 font-sans text-[16px] font-normal leading-[1.65] resize-none border-0 border-none outline-none focus:outline-none focus:ring-0 pr-20"
          aria-label="Follow-up message"
        />

        {(promptError || micError) && (
          <span className="absolute bottom-2.5 left-4 text-[12px] text-[#E3A29E] flex items-center gap-1 font-sans">
            <AlertCircle className="w-3.5 h-3.5" />
            {promptError || micError}
          </span>
        )}

        <div className="absolute bottom-2.5 right-2.5 flex items-center gap-1.5">
          <button
            type="button"
            onClick={toggleListening}
            disabled={isSubmitting}
            className={`w-7 h-7 sm:w-8 sm:h-8 rounded-lg flex items-center justify-center transition-all ${
              isListening
                ? "bg-[#A7C4A2]/20 text-[#A7C4A2] border border-[#A7C4A2]/50 animate-pulse"
                : "bg-[#151E23] hover:bg-[#2A3940] border border-[#3A4A50] text-[#ADBAB9] hover:text-[#EDF1EE]"
            }`}
            title={isListening ? "Listening... click to stop" : "Speak message"}
            aria-label={isListening ? "Stop voice input" : "Start voice input"}
          >
            <Mic className={`w-3.5 h-3.5 ${isListening ? "animate-pulse" : ""}`} />
          </button>

          <button
            type="button"
            onClick={handleSend}
            disabled={!hasValidInput || isSubmitting}
            className={`w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center transition-all ${
              hasValidInput && !isSubmitting
                ? "bg-[#C3D1B8] text-[#17201C] hover:bg-[#D5DFCD] cursor-pointer shadow-sm"
                : "bg-[#2A3940] text-[#ADBAB9]/40 cursor-not-allowed"
            }`}
            aria-label="Send follow-up"
          >
            <ArrowUp className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          </button>
        </div>
      </div>
      <p className="text-[12px] text-[#ADBAB9] text-center mt-2 font-sans select-none">
        MorphAPI generates self-healing JSON endpoints from live DOM structure.
      </p>
    </div>
  );
}
