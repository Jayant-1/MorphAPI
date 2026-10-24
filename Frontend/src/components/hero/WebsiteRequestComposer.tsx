"use client";

import React, { useState, useRef, useEffect } from "react";
import { Globe, ArrowUp, Loader2, AlertCircle, Mic } from "lucide-react";

interface WebsiteRequestComposerProps {
  initialUrl?: string;
  initialPrompt?: string;
  isSubmitting?: boolean;
  onSubmit: (url: string, prompt: string) => void;
  className?: string;
}

export function WebsiteRequestComposer({
  initialUrl = "",
  initialPrompt = "",
  isSubmitting = false,
  onSubmit,
  className = "",
}: WebsiteRequestComposerProps) {
  const [url, setUrl] = useState(initialUrl);
  const [prompt, setPrompt] = useState(initialPrompt);
  const [urlError, setUrlError] = useState<string | null>(null);
  const [promptError, setPromptError] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [isRequestingMic, setIsRequestingMic] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);

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
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
      }
      if (mediaStreamRef.current) {
        try {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
        } catch {
          // ignore
        }
      }
    };
  }, []);

  useEffect(() => {
    if (initialUrl !== undefined) setUrl(initialUrl);
  }, [initialUrl]);

  useEffect(() => {
    if (initialPrompt !== undefined) setPrompt(initialPrompt);
  }, [initialPrompt]);

  const toggleListening = async () => {
    if (isListening || isRequestingMic) {
      cleanupAudio();
      return;
    }

    setMicError(null);

    if (typeof window === "undefined") return;

    // Verify browser supports media devices
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setMicError("Microphone access is not supported by your browser environment.");
      setTimeout(() => setMicError(null), 4000);
      return;
    }

    setIsRequestingMic(true);

    try {
      // 1. Explicitly invoke getUserMedia to guarantee the browser prompts the user for microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const SpeechRecognition =
        (window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition;

      if (!SpeechRecognition) {
        // Microphone access granted, but browser lacks SpeechRecognition (e.g. Firefox)
        setIsListening(true);
        setIsRequestingMic(false);
        setMicError("Microphone connected. (Live transcription requires Chrome/Edge/Safari)");
        setTimeout(() => setMicError(null), 5000);
        return;
      }

      // In Chrome/Chromium, release the initial probe stream tracks so hardware mic is unlocked for SpeechRecognition
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
          setMicError("Microphone permission denied. Please allow microphone permissions.");
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
    } catch (err: any) {
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setMicError("Microphone permission denied. Please allow access in browser settings.");
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        setMicError("No microphone found. Please connect an audio input device.");
      } else {
        setMicError("Could not access microphone.");
      }
      cleanupAudio();
      setTimeout(() => setMicError(null), 4000);
    }
  };

  const validateUrl = (val: string): boolean => {
    const trimmed = val.trim();
    if (!trimmed) {
      setUrlError("Please enter a website URL.");
      return false;
    }
    try {
      const parsed = new URL(trimmed.startsWith("http") ? trimmed : `https://${trimmed}`);
      if (!parsed.hostname || !parsed.hostname.includes(".")) {
        setUrlError("Enter a valid web domain (e.g. example.com).");
        return false;
      }
      setUrlError(null);
      return true;
    } catch {
      setUrlError("Invalid URL format. Example: https://example.com");
      return false;
    }
  };

  const validatePrompt = (val: string): boolean => {
    const trimmed = val.trim();
    if (!trimmed) {
      setPromptError("Please describe what data this API should extract.");
      return false;
    }
    if (trimmed.length < 5) {
      setPromptError("Please provide a more descriptive extraction request.");
      return false;
    }
    setPromptError(null);
    return true;
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (isSubmitting) return;

    const isUrlValid = validateUrl(url);
    const isPromptValid = validatePrompt(prompt);

    if (!isUrlValid) {
      urlInputRef.current?.focus();
      return;
    }
    if (!isPromptValid) {
      textareaRef.current?.focus();
      return;
    }

    const formattedUrl = url.trim().startsWith("http") ? url.trim() : `https://${url.trim()}`;
    onSubmit(formattedUrl, prompt.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className={`w-full flex flex-col items-center select-none font-sans ${className}`}
      noValidate
    >
      {/* 
        Top URL Input: Visibly narrower than the request composer (~440-480px on desktop)
        Placed centered above the main composer with ~10px visual offset 
      */}
      {/* 
        Top URL Input: Visibly narrower than the request composer (~440-480px on desktop)
        Placed centered directly above the main composer
      */}
      <div className="w-full max-w-[460px] flex flex-col items-start relative z-20">
        <label htmlFor="morph-url-input" className="sr-only">
          Website URL
        </label>

        <div className="w-full relative flex items-center group">
          <div className="absolute left-3.5 text-[#ADBAB9] group-focus-within:text-[#AEC8D0] transition-colors pointer-events-none">
            <Globe className="w-4 h-4" />
          </div>

          <input
            ref={urlInputRef}
            id="morph-url-input"
            type="url"
            name="targetUrl"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              if (urlError) validateUrl(e.target.value);
            }}
            placeholder="Website link (e.g. https://example.com)"
            disabled={isSubmitting}
            autoComplete="url"
            className={`w-full h-[46px] sm:h-[48px] pl-10 ${urlError ? "pr-32" : "pr-4"} rounded-xl bg-[#202C32]/98 text-[#EDF1EE] font-mono text-sm placeholder:text-[#ADBAB9] border ${urlError ? "border-[#E3A29E] focus:border-[#E3A29E] focus:ring-[#E3A29E]" : "border-[#3A4A50] hover:border-[#4B5E66] focus:border-[#AEC8D0] focus:ring-[#AEC8D0]"} focus:ring-1 focus:outline-hidden transition-all shadow-[0_4px_20px_rgba(16,23,27,0.6)] backdrop-blur-md disabled:opacity-60`}
            aria-invalid={!!urlError}
          />

          {urlError && (
            <span className="absolute right-3 text-[#E3A29E] flex items-center gap-1 font-sans text-xs bg-[#202C32] px-2 py-0.5 rounded-md pointer-events-none border border-[#E3A29E]/30">
              <AlertCircle className="w-3 h-3" />
              {urlError}
            </span>
          )}
        </div>
      </div>

      {/* 
        Bottom Request Composer: Wider (~720-760px on desktop, full width on mobile)
        Positioned directly adjacent to the URL box with a minimal 4px gap
      */}
      <div className="w-full max-w-[740px] flex flex-col items-start relative z-10 mt-1 sm:mt-1.5">
        <label htmlFor="morph-prompt-input" className="sr-only">
          What should this API return?
        </label>

        <div className="w-full relative rounded-2xl bg-[#202C32]/98 border border-[#3A4A50] hover:border-[#4B5E66] focus-within:border-[#AEC8D0] focus-within:ring-1 focus-within:ring-[#AEC8D0] transition-all shadow-[0_8px_32px_rgba(16,23,27,0.7)] backdrop-blur-md overflow-hidden">
          <textarea
            ref={textareaRef}
            id="morph-prompt-input"
            name="prompt"
            value={prompt}
            onChange={(e) => {
              setPrompt(e.target.value);
              if (promptError) validatePrompt(e.target.value);
            }}
            onKeyDown={handleKeyDown}
            placeholder="User requirements from website (e.g. extract product names, prices, availability)..."
            disabled={isSubmitting}
            rows={4}
            className="w-full min-h-[140px] sm:min-h-[155px] p-4 sm:p-5 pb-14 bg-transparent text-[#EDF1EE] font-sans text-sm sm:text-base placeholder:text-[#ADBAB9] resize-none focus:outline-hidden leading-relaxed disabled:opacity-60"
            aria-invalid={!!promptError}
          />

          {/* Bottom Action Footer inside composer */}
          <div className="absolute bottom-3 left-4 right-3.5 flex items-center justify-between pointer-events-none">
            {/* Keyboard shortcut hint and inline error feedback */}
            <div className="flex items-center gap-3">
              <span className="hidden sm:inline-flex items-center gap-1.5 text-[11px] font-mono text-[#ADBAB9] tracking-tight">
                <kbd className="px-1.5 py-0.5 rounded-sm bg-[#151E23] border border-[#3A4A50] text-[#ADBAB9]">
                  Ctrl
                </kbd>
                <span>+</span>
                <kbd className="px-1.5 py-0.5 rounded-sm bg-[#151E23] border border-[#3A4A50] text-[#ADBAB9]">
                  Enter
                </kbd>
                <span className="text-[#ADBAB9]/70">to submit</span>
              </span>

              {promptError && (
                <span className="text-[#E3A29E] flex items-center gap-1 font-sans text-xs bg-[#202C32] px-2 py-0.5 rounded-md border border-[#E3A29E]/30">
                  <AlertCircle className="w-3.5 h-3.5" />
                  {promptError}
                </span>
              )}
              {micError && !promptError && (
                <span className="text-[#DDC38A] flex items-center gap-1 font-sans text-xs bg-[#202C32] px-2 py-0.5 rounded-md border border-[#DDC38A]/30">
                  <AlertCircle className="w-3.5 h-3.5" />
                  {micError}
                </span>
              )}
            </div>

            {/* Action controls: Voice Mic + Build API */}
            <div className="flex items-center gap-2 pointer-events-auto ml-auto">
              {/* Requesting mic badge */}
              {isRequestingMic && (
                <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#DDC38A]/15 border border-[#DDC38A]/30 text-[#DDC38A] text-xs font-mono animate-pulse">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#DDC38A] animate-ping" />
                  <span>Requesting mic...</span>
                </span>
              )}

              {/* Listening pulse badge */}
              {isListening && (
                <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#A7C4A2]/15 border border-[#A7C4A2]/30 text-[#A7C4A2] text-xs font-mono animate-pulse">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#A7C4A2] animate-ping" />
                  <span>Listening...</span>
                </span>
              )}

              {/* Clean Mic Button for Voice Input */}
              <button
                type="button"
                onClick={toggleListening}
                disabled={isSubmitting}
                className={`relative w-9 h-9 sm:w-10 sm:h-10 rounded-xl border transition-all flex items-center justify-center focus:outline-hidden focus:ring-1 focus:ring-[#AEC8D0] disabled:opacity-50 ${
                  isListening
                    ? "bg-[#A7C4A2]/20 text-[#A7C4A2] border-[#A7C4A2]/60 shadow-xs"
                    : isRequestingMic
                    ? "bg-[#DDC38A]/20 text-[#DDC38A] border-[#DDC38A]/60 shadow-xs animate-pulse"
                    : "bg-[#151E23] hover:bg-[#2A3940] text-[#ADBAB9] hover:text-[#EDF1EE] border-[#3A4A50] hover:border-[#4B5E66] shadow-xs"
                }`}
                title={
                  isListening
                    ? "Listening... Click to stop speaking"
                    : isRequestingMic
                    ? "Requesting microphone permission in browser..."
                    : "Talk to enter requirements"
                }
                aria-label={
                  isListening
                    ? "Stop voice input"
                    : isRequestingMic
                    ? "Requesting microphone permission"
                    : "Speak requirements"
                }
                aria-pressed={isListening}
              >
                {isRequestingMic ? (
                  <Loader2 className="w-4 h-4 animate-spin text-[#DDC38A]" />
                ) : (
                  <Mic className={`w-4 h-4 transition-transform ${isListening ? "text-[#A7C4A2] scale-110" : ""}`} />
                )}
              </button>

              {/* Primary Submit Button: Build API (Pale Sage with dark text) */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#C3D1B8] hover:bg-[#D5DFCD] active:translate-y-0.5 text-[#17201C] font-semibold text-xs sm:text-sm shadow-sm transition-all focus:outline-hidden focus:ring-2 focus:ring-[#AEC8D0] disabled:opacity-50 disabled:pointer-events-none group"
                aria-label="Build API from target URL"
              >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-[#17201C]" />
                  <span>Synthesizing...</span>
                </>
              ) : (
                <>
                  <span>Build API</span>
                  <div className="w-5 h-5 rounded-lg bg-[#17201C]/15 flex items-center justify-center group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform">
                    <ArrowUp className="w-3.5 h-3.5 text-[#17201C]" />
                  </div>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  </form>
);
}
