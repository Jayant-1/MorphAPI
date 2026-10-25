"use client";

import React, { useRef, useState, useEffect } from "react";
import { Play, Pause } from "lucide-react";

interface HeroArtworkProps {
  dimmed?: boolean;
}

export function HeroArtwork({ dimmed = false }: HeroArtworkProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(true);

  useEffect(() => {
    // Respect reduced-motion preferences
    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (prefersReducedMotion && videoRef.current) {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  }, []);

  const togglePlayback = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!videoRef.current) return;

    if (videoRef.current.paused) {
      videoRef.current.play().then(() => setIsPlaying(true)).catch(() => setIsPlaying(false));
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  return (
    <div
      className={`fixed inset-0 select-none overflow-hidden transition-opacity duration-500 pointer-events-none ${
        dimmed ? "opacity-30" : "opacity-100"
      }`}
      aria-hidden="true"
    >
      {/* Cinematic Storm Cloudscape Video Background with Fallback Poster */}
      <video
        ref={videoRef}
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        poster="/hero-artwork.jpg"
        onPlaying={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        className="w-full h-full object-cover object-center pointer-events-none"
      >
        <source src="/hero-background.mp4" type="video/mp4" />
      </video>

      {/* Dark gradient overlay for text contrast */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#10171B]/55 via-[#10171B]/60 to-[#10171B]/85 pointer-events-none" />

      {/* Discreet Video Pause/Play Control — only shown in hero (not dimmed) */}
      {!dimmed && (
        <div className="absolute bottom-4 right-4 z-20 pointer-events-auto">
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
