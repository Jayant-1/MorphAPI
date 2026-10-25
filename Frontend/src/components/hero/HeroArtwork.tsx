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

  const activeTrackRef = useRef<"A" | "B">("A");
  const isFadingRef = useRef(false);

  // Crossfade duration: 2.2s seamless blend
  const FADE_DURATION = 2.2;
  const PLAYBACK_RATE = 0.85;

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
      vidA.playbackRate = PLAYBACK_RATE;
      vidA.play().catch(() => {});
    }

    // High-precision monitor to execute seamless crossfade before either track ends
    const interval = setInterval(() => {
      const currentTrack = activeTrackRef.current;
      const activeVideo = currentTrack === "A" ? videoRefA.current : videoRefB.current;
      const nextVideo = currentTrack === "A" ? videoRefB.current : videoRefA.current;

      if (!activeVideo || !nextVideo) return;

      const duration = activeVideo.duration;
      const currentTime = activeVideo.currentTime;

      if (duration && currentTime >= duration - FADE_DURATION && !isFadingRef.current) {
        isFadingRef.current = true;
        const nextTrack = currentTrack === "A" ? "B" : "A";

        // Prime and play the incoming video from 0s
        nextVideo.currentTime = 0;
        nextVideo.playbackRate = PLAYBACK_RATE;
        nextVideo.play().catch(() => {});

        // Swap active track to trigger CSS crossfade
        activeTrackRef.current = nextTrack;
        setActiveTrack(nextTrack);

        // After crossfade finishes, pause the outgoing track so it rests silently at 0s
        setTimeout(() => {
          activeVideo.pause();
          activeVideo.currentTime = 0;
          isFadingRef.current = false;
        }, (FADE_DURATION + 0.3) * 1000);
      }
    }, 100);

    return () => clearInterval(interval);
  }, []);

  const togglePlayback = (e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    const vidA = videoRefA.current;
    const vidB = videoRefB.current;
    if (!vidA || !vidB) return;

    // Direct check of actual video hardware status
    const isCurrentlyPlaying = (!vidA.paused && !vidA.ended) || (!vidB.paused && !vidB.ended);

    if (isCurrentlyPlaying) {
      vidA.pause();
      vidB.pause();
      setIsPlaying(false);
    } else {
      const currentTrack = activeTrackRef.current;
      const targetVideo = currentTrack === "A" ? vidA : vidB;
      if (targetVideo.ended) {
        targetVideo.currentTime = 0;
      }
      targetVideo
        .play()
        .then(() => setIsPlaying(true))
        .catch(() => {
          if (vidA) {
            vidA.currentTime = 0;
            vidA.play().then(() => {
              activeTrackRef.current = "A";
              setActiveTrack("A");
              setIsPlaying(true);
            }).catch(() => {});
          }
        });
    }
  };

  return (
    <div
      className={`fixed inset-0 select-none overflow-hidden transition-opacity duration-500 pointer-events-none ${
        dimmed ? "opacity-30" : "opacity-100"
      }`}
    >
      {/* Seamless Track A */}
      <video
        ref={videoRefA}
        autoPlay
        muted
        playsInline
        preload="auto"
        onPlay={() => setIsPlaying(true)}
        onPause={() => {
          if ((videoRefA.current?.paused ?? true) && (videoRefB.current?.paused ?? true)) {
            setIsPlaying(false);
          }
        }}
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
        onPlay={() => setIsPlaying(true)}
        onPause={() => {
          if ((videoRefA.current?.paused ?? true) && (videoRefB.current?.paused ?? true)) {
            setIsPlaying(false);
          }
        }}
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
        <div
          onClick={togglePlayback}
          className="absolute bottom-4 right-4 z-30 pointer-events-auto cursor-pointer"
        >
          <button
            type="button"
            onClick={togglePlayback}
            className="w-8 h-8 rounded-lg bg-[#202C32]/90 hover:bg-[#2A3940] border border-[#3A4A50] text-[#ADBAB9] hover:text-[#EDF1EE] flex items-center justify-center transition-colors shadow-lg cursor-pointer focus:outline-hidden focus:ring-1 focus:ring-[#AEC8D0]"
            title={isPlaying ? "Pause background clouds video" : "Play background clouds video"}
            aria-label={isPlaying ? "Pause background clouds video" : "Play background clouds video"}
            aria-pressed={!isPlaying}
          >
            {isPlaying ? (
              <Pause className="w-3.5 h-3.5 text-[#ADBAB9]" />
            ) : (
              <Play className="w-3.5 h-3.5 text-[#ADBAB9] ml-0.5" />
            )}
          </button>
        </div>
      )}
    </div>
  );
}
