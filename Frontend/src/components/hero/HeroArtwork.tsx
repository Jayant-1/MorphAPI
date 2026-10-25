"use client";

import React, { useRef, useState, useEffect } from "react";
import { Play, Pause } from "lucide-react";

interface HeroArtworkProps {
  dimmed?: boolean;
}

export function HeroArtwork({ dimmed = false }: HeroArtworkProps) {
  const videoRefA = useRef<HTMLVideoElement>(null);
  const videoRefB = useRef<HTMLVideoElement>(null);
  const [activeTrack, setActiveTrack] = useState<"A" | "B">("A");
  const [isPlaying, setIsPlaying] = useState(true);

  // Crossfade duration: 2.2s seamless blend between track endpoints
  const FADE_DURATION = 2.2;

  useEffect(() => {
    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (prefersReducedMotion) {
      videoRefA.current?.pause();
      videoRefB.current?.pause();
      setIsPlaying(false);
      return;
    }

    const vidA = videoRefA.current;
    if (vidA) {
      vidA.playbackRate = 0.85;
      vidA.play().catch(() => {});
    }
  }, []);

  // Time update monitoring on Track A to initiate seamless crossfade into Track B
  const handleTimeUpdateA = () => {
    const vidA = videoRefA.current;
    const vidB = videoRefB.current;
    if (!vidA || !vidB) return;

    if (activeTrack === "A" && vidA.duration && vidA.currentTime >= vidA.duration - FADE_DURATION) {
      vidB.currentTime = 0;
      vidB.playbackRate = 0.85;
      vidB.play().catch(() => {});
      setActiveTrack("B");
    }
  };

  // Time update monitoring on Track B to initiate seamless crossfade into Track A
  const handleTimeUpdateB = () => {
    const vidA = videoRefA.current;
    const vidB = videoRefB.current;
    if (!vidA || !vidB) return;

    if (activeTrack === "B" && vidB.duration && vidB.currentTime >= vidB.duration - FADE_DURATION) {
      vidA.currentTime = 0;
      vidA.playbackRate = 0.85;
      vidA.play().catch(() => {});
      setActiveTrack("A");
    }
  };

  const handleEndedA = () => {
    if (videoRefA.current) {
      videoRefA.current.pause();
      videoRefA.current.currentTime = 0;
    }
  };

  const handleEndedB = () => {
    if (videoRefB.current) {
      videoRefB.current.pause();
      videoRefB.current.currentTime = 0;
    }
  };

  const togglePlayback = (e: React.MouseEvent) => {
    e.stopPropagation();
    const vidA = videoRefA.current;
    const vidB = videoRefB.current;
    if (!vidA || !vidB) return;

    if (isPlaying) {
      vidA.pause();
      vidB.pause();
      setIsPlaying(false);
    } else {
      const current = activeTrack === "A" ? vidA : vidB;
      current.play().then(() => setIsPlaying(true)).catch(() => setIsPlaying(false));
    }
  };

  return (
    <div
      className={`fixed inset-0 select-none overflow-hidden transition-opacity duration-500 pointer-events-none ${
        dimmed ? "opacity-30" : "opacity-100"
      }`}
      aria-hidden="true"
    >
      {/* Seamless Track A */}
      <video
        ref={videoRefA}
        autoPlay
        muted
        playsInline
        preload="auto"
        onTimeUpdate={handleTimeUpdateA}
        onEnded={handleEndedA}
        className={`absolute inset-0 w-full h-full object-cover object-center pointer-events-none transition-opacity duration-[2200ms] ease-in-out ${
          activeTrack === "A" ? "opacity-100 z-10" : "opacity-0 z-0"
        }`}
      >
        <source src="/hero-background.mp4" type="video/mp4" />
      </video>

      {/* Seamless Track B (Crossfades seamlessly with Track A for infinite loop) */}
      <video
        ref={videoRefB}
        muted
        playsInline
        preload="auto"
        onTimeUpdate={handleTimeUpdateB}
        onEnded={handleEndedB}
        className={`absolute inset-0 w-full h-full object-cover object-center pointer-events-none transition-opacity duration-[2200ms] ease-in-out ${
          activeTrack === "B" ? "opacity-100 z-10" : "opacity-0 z-0"
        }`}
      >
        <source src="/hero-background.mp4" type="video/mp4" />
      </video>

      {/* Dark gradient overlay for text contrast */}
      <div className="absolute inset-0 z-20 bg-gradient-to-b from-[#10171B]/55 via-[#10171B]/60 to-[#10171B]/85 pointer-events-none" />

      {/* Discreet Video Pause/Play Control — only shown in hero (not dimmed) */}
      {!dimmed && (
        <div className="absolute bottom-4 right-4 z-30 pointer-events-auto">
          <button
            type="button"
            onClick={togglePlayback}
            className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-[#202C32]/80 hover:bg-[#2A3940] border border-[#3A4A50] text-[#ADBAB9] hover:text-[#EDF1EE] flex items-center justify-center transition-colors focus:outline-hidden focus:ring-1 focus:ring-[#AEC8D0]"
            title={isPlaying ? "Pause background clouds video" : "Play background clouds video"}
            aria-label={isPlaying ? "Pause background clouds video" : "Play background clouds video"}
            aria-pressed={!isPlaying}
          >
            {isPlaying ? (
              <Pause className="w-3 h-3 text-[#ADBAB9]" />
            ) : (
              <Play className="w-3 h-3 text-[#ADBAB9] ml-0.5" />
            )}
          </button>
        </div>
      )}
    </div>
  );
}
