"use client";

import React, { useState } from "react";
import { HeroArtwork } from "./HeroArtwork";
import { WebsiteRequestComposer } from "./WebsiteRequestComposer";

interface MorphHeroProps {
  initialUrl?: string;
  initialPrompt?: string;
  initialFixtureId?: string;
  onStartRun: (url: string, prompt: string, fixtureId?: string) => void;
  onDraftChange?: (url: string, prompt: string) => void;
  isSubmitting?: boolean;
  isTransitioning?: boolean;
}

export function MorphHero({
  initialUrl,
  initialPrompt,
  initialFixtureId = "multi_endpoint_catalog",
  onStartRun,
  onDraftChange,
  isSubmitting = false,
  isTransitioning = false,
}: MorphHeroProps) {
  const [composerUrl, setComposerUrl] = useState(initialUrl || "");
  const [composerPrompt, setComposerPrompt] = useState(initialPrompt || "");

  React.useEffect(() => {
    if (initialUrl !== undefined) {
      setComposerUrl(initialUrl);
    }
  }, [initialUrl]);

  React.useEffect(() => {
    if (initialPrompt !== undefined) {
      setComposerPrompt(initialPrompt);
    }
  }, [initialPrompt]);

  const handleFormSubmit = (url: string, prompt: string) => {
    onDraftChange?.(url, prompt);
    onStartRun(url, prompt, initialFixtureId);
  };

  return (
    <section className="relative w-full min-h-[calc(100vh-3.5rem)] min-h-[calc(100dvh-3.5rem)] flex flex-col items-center justify-center py-12 px-4 sm:px-6 overflow-hidden">
      {/* Visual Background Artwork: smoothly dims during transition */}
      <HeroArtwork dimmed={isTransitioning} />

      {/* Hero Content Container: ~1280px max-width, desktop centered */}
      <div className="relative z-10 w-full max-w-[1280px] mx-auto flex flex-col items-center text-center">
        {/* Eyebrow, Headline, and Supporting Copy: fade out over ~200ms on submit */}
        <div
          className={`flex flex-col items-center transition-all duration-300 ease-in-out ${
            isTransitioning
              ? "opacity-0 -translate-y-6 pointer-events-none"
              : "opacity-100 translate-y-0"
          }`}
        >
          {/* Headline on Two Lines */}
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-[68px] font-bold text-[#EDF1EE] tracking-tight leading-[1.06] max-w-[780px] mb-4">
            <span>Any website.</span>
            <br />
            <span>
              Your next <span className="text-[#C3D1B8]">API.</span>
            </span>
          </h1>

          {/* Supporting Subtext */}
          <p className="text-sm sm:text-base md:text-lg text-[#ADBAB9] max-w-[550px] font-normal leading-relaxed mb-8">
            Paste a link. Describe the data you need. Build and test your API in one place.
          </p>
        </div>

        {/* Two-part Central Composer from Drawing: translates upward on transition */}
        <div
          className={`w-full flex justify-center transition-all duration-500 ease-out ${
            isTransitioning ? "-translate-y-16 scale-[0.98]" : "translate-y-0 scale-100"
          }`}
        >
          <WebsiteRequestComposer
            initialUrl={composerUrl}
            initialPrompt={composerPrompt}
            isSubmitting={isSubmitting || isTransitioning}
            onSubmit={handleFormSubmit}
            className="mb-0"
          />
        </div>
      </div>
    </section>
  );
}
