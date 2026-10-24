"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { ArrowUpRight } from "lucide-react";
import { UserAccountWidget } from "./UserAccountWidget";

export function MechanicalNavbar() {
  return (
    <header className="sticky top-0 z-50 w-full bg-[#10171B]/90 backdrop-blur-md border-b border-[#3A4A50]">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4 font-mono">
        {/* Left: Brand logo */}
        <div className="flex-1 flex items-center justify-start min-w-[140px]">
          <Link href="/" className="flex items-center gap-2.5 group focus:outline-hidden">
            <Image
              src="/logo.png"
              alt="MorphAPI Emblem"
              width={26}
              height={26}
              className="w-6.5 h-6.5 object-contain group-hover:scale-105 transition-transform duration-200 drop-shadow-[0_0_8px_rgba(195,209,184,0.25)] shrink-0"
              priority
            />
            <span className="font-bold text-sm tracking-tight text-[#EDF1EE] group-hover:text-[#C3D1B8] transition-colors">
              MORPHAPI
            </span>
          </Link>
        </div>

        {/* Center: Navigation in the exact middle */}
        <nav className="hidden md:flex items-center justify-center gap-1 text-xs text-[#ADBAB9]">
          <a
            href="#demo"
            className="px-3 py-1.5 rounded-sm hover:text-[#EDF1EE] hover:bg-[#202C32] border border-transparent hover:border-[#3A4A50] transition-colors"
          >
            Interactive Demo
          </a>
          <a
            href="#how-it-works"
            className="px-3 py-1.5 rounded-sm hover:text-[#EDF1EE] hover:bg-[#202C32] border border-transparent hover:border-[#3A4A50] transition-colors"
          >
            How It Works
          </a>
          <a
            href="#protocols"
            className="px-3 py-1.5 rounded-sm hover:text-[#EDF1EE] hover:bg-[#202C32] border border-transparent hover:border-[#3A4A50] transition-colors"
          >
            Protocols
          </a>
          <a
            href="https://github.com/Jayant-1/MorphAPI"
            target="_blank"
            rel="noreferrer"
            className="px-3 py-1.5 rounded-sm hover:text-[#EDF1EE] hover:bg-[#202C32] border border-transparent hover:border-[#3A4A50] transition-colors flex items-center gap-1"
          >
            <span>GitHub</span>
            <ArrowUpRight className="w-3 h-3 text-[#ADBAB9]" />
          </a>
        </nav>

        {/* Right: User Account Icon */}
        <div className="flex-1 flex items-center justify-end min-w-[140px]">
          <UserAccountWidget variant="navbar" />
        </div>
      </div>
    </header>
  );
}
