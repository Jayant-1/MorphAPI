"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { ArrowUpRight, Github } from "lucide-react";

export function MechanicalFooter() {
  return (
    <footer className="w-full bg-[#060608] border-t border-[#1C1C24] font-sans text-xs text-[#71717A]">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-10 flex flex-col md:flex-row items-center justify-between gap-6">
        {/* Brand */}
        <div className="flex items-center gap-2.5">
          <Image
            src="/logo.png"
            alt="MorphAPI"
            width={24}
            height={24}
            className="w-6 h-6 object-contain shrink-0 drop-shadow-[0_0_8px_rgba(16,185,129,0.3)]"
          />
          <div>
            <span className="font-bold text-white text-sm">MorphAPI</span>
          </div>
        </div>

        {/* Links */}
        <div className="flex flex-wrap items-center gap-6 text-xs text-[#A1A1AA]">
          <a href="#demo" className="hover:text-white transition-colors">
            Demo
          </a>
          <a href="#how-it-works" className="hover:text-white transition-colors">
            How It Works
          </a>
          <a href="#protocols" className="hover:text-white transition-colors">
            Protocols
          </a>
          <a
            href="https://github.com/Jayant-1/MorphAPI"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 hover:text-white transition-colors text-white font-medium"
          >
            <Github className="w-3.5 h-3.5" />
            <span>GitHub</span>
            <ArrowUpRight className="w-3 h-3 text-[#71717A]" />
          </a>
        </div>

        {/* Copyright */}
        <div className="text-[11px] text-[#52525B] font-mono">
          MIT License • Open Source
        </div>
      </div>
    </footer>
  );
}
