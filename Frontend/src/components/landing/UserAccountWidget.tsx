"use client";

import React, { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import {
  User,
  Settings,
  LogOut,
  Key,
  Check,
  Copy,
  Lock,
  X,
  Eye,
  EyeOff,
} from "lucide-react";

interface UserAccountProps {
  variant?: "hero" | "navbar";
}

export function UserAccountWidget({ variant = "navbar" }: UserAccountProps) {
  // Hardcoded developer credentials
  const USER_CREDENTIALS = {
    username: "jayant.dev",
    password: "1qaz2wsx",
    email: "jayant@morphapi.io",
    role: "Lead Systems Architect",
    tier: "Enterprise Gateway Pro",
    cluster: "us-east-metal-01",
    apiKey: "morph_live_sec_9941a8f_healer",
    authType: "Preset Developer Session",
    engine: "Playwright AST + Gemma 4 Vision",
  };

  // State: initially logged in
  const [mounted, setMounted] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(true);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [activeModal, setActiveModal] = useState<"none" | "profile" | "settings" | "login">("none");
  const [copiedKey, setCopiedKey] = useState(false);

  // Settings toggles
  const [autoHealEnabled, setAutoHealEnabled] = useState(true);
  const [showPassword, setShowPassword] = useState(false);

  // Login form state
  const [loginUsername, setLoginUsername] = useState("jayant.dev");
  const [loginPassword, setLoginPassword] = useState("1qaz2wsx");
  const [loginError, setLoginError] = useState("");

  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Click outside to close dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleCopyKey = () => {
    navigator.clipboard.writeText(USER_CREDENTIALS.apiKey);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setDropdownOpen(false);
  };

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (loginUsername === USER_CREDENTIALS.username && loginPassword === USER_CREDENTIALS.password) {
      setIsLoggedIn(true);
      setActiveModal("none");
      setLoginError("");
    } else {
      setLoginError("Invalid credentials. Use hardcoded: jayant.dev / 1qaz2wsx");
    }
  };

  const prefillCredentials = () => {
    setLoginUsername(USER_CREDENTIALS.username);
    setLoginPassword(USER_CREDENTIALS.password);
    setLoginError("");
  };

  return (
    <>
      <div className="relative inline-block text-left" ref={dropdownRef}>
        {isLoggedIn ? (
          /* Single clean account icon button (no text / no badges / no chevron in navbar) */
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            aria-label="User Account Menu"
            title={`${USER_CREDENTIALS.username} (${USER_CREDENTIALS.role})`}
            className="group relative w-8 h-8 rounded-full bg-[#111217] border border-[#22242F] hover:border-[#10B981]/50 flex items-center justify-center transition-all duration-150 focus:outline-hidden cursor-pointer"
          >
            <User className="w-3.5 h-3.5 text-[#A1A1AA] group-hover:text-white transition-colors" />
          </button>
        ) : (
          /* Minimal Sign In Button when logged out */
          <button
            onClick={() => setActiveModal("login")}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-[#272730] bg-[#111217] hover:bg-[#181922] text-[#A1A1AA] hover:text-white text-xs font-mono transition-colors cursor-pointer"
          >
            <User className="w-3 h-3" />
            <span>Sign In</span>
          </button>
        )}

        {/* Clean, Refined Developer Dropdown (Zero AI Slop) */}
        {dropdownOpen && isLoggedIn && (
          <div className="absolute right-0 mt-2 w-64 origin-top-right rounded-lg border border-[#22242F] bg-[#0C0D12] shadow-2xl text-xs font-mono text-[#D4D4D8] z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-100">
            {/* Header: User Handle */}
            <div className="px-3.5 py-3 border-b border-[#1E2028]">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-full bg-[#181A24] border border-[#2A2D3C] text-white flex items-center justify-center font-bold text-xs shrink-0">
                  JD
                </div>
                <div className="min-w-0">
                  <div className="font-bold text-white text-xs truncate">
                    {USER_CREDENTIALS.username}
                  </div>
                  <div className="text-[10px] text-[#71717A] truncate">
                    {USER_CREDENTIALS.email}
                  </div>
                </div>
              </div>
            </div>

            {/* Menu Navigation Options */}
            <div className="p-1.5 space-y-0.5">
              <button
                onClick={() => {
                  setDropdownOpen(false);
                  setActiveModal("profile");
                }}
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md hover:bg-[#161822] hover:text-white transition-colors text-left cursor-pointer"
              >
                <User className="w-3.5 h-3.5 text-emerald-400" />
                <span>Developer Profile</span>
              </button>

              <button
                onClick={() => {
                  setDropdownOpen(false);
                  setActiveModal("settings");
                }}
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md hover:bg-[#161822] hover:text-white transition-colors text-left cursor-pointer"
              >
                <Settings className="w-3.5 h-3.5 text-cyan-400" />
                <span>Gateway Settings</span>
              </button>
            </div>

            {/* Logout Footer */}
            <div className="border-t border-[#1E2028] p-1.5">
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md hover:bg-red-500/10 text-[#EF4444] hover:text-red-300 transition-colors text-left cursor-pointer"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Log Out</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Portal Modals: Mounted directly to document.body to prevent containing block trap */}
      {mounted && activeModal !== "none" && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 font-mono">
          {/* Developer Profile Modal */}
          {activeModal === "profile" && (
            <div className="w-full max-w-md rounded-lg border border-[#22242F] bg-[#0C0D12] p-5 shadow-2xl text-xs space-y-4 animate-in fade-in zoom-in-95">
              {/* Modal Header */}
              <div className="flex items-center justify-between border-b border-[#1E2028] pb-3">
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4 text-emerald-400" />
                  <h3 className="font-bold text-white text-sm">Developer Profile</h3>
                </div>
                <button
                  onClick={() => setActiveModal("none")}
                  className="text-[#71717A] hover:text-white p-1 transition-colors cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* User Identity Header */}
              <div className="flex items-center gap-3 pb-3 border-b border-[#1E2028]">
                <div className="w-9 h-9 rounded-full bg-[#181A24] border border-[#2A2D3C] text-white flex items-center justify-center font-bold text-xs shrink-0">
                  JD
                </div>
                <div className="min-w-0">
                  <div className="font-bold text-white text-sm">{USER_CREDENTIALS.username}</div>
                  <div className="text-[11px] text-[#71717A]">{USER_CREDENTIALS.email}</div>
                </div>
              </div>

              {/* Clean Spec Property Table (No fake stats / No cards inside cards) */}
              <div className="space-y-2.5 text-[11px]">
                <div className="flex items-center justify-between py-1 border-b border-[#1A1C24]">
                  <span className="text-[#71717A]">Access Role</span>
                  <span className="text-white font-medium">{USER_CREDENTIALS.role}</span>
                </div>
                <div className="flex items-center justify-between py-1 border-b border-[#1A1C24]">
                  <span className="text-[#71717A]">License Tier</span>
                  <span className="text-white font-medium">{USER_CREDENTIALS.tier}</span>
                </div>
                <div className="flex items-center justify-between py-1 border-b border-[#1A1C24]">
                  <span className="text-[#71717A]">Active Cluster</span>
                  <span className="text-white font-mono">{USER_CREDENTIALS.cluster}</span>
                </div>
                <div className="flex items-center justify-between py-1 border-b border-[#1A1C24]">
                  <span className="text-[#71717A]">Auth Protocol</span>
                  <span className="text-emerald-400 font-mono">{USER_CREDENTIALS.authType}</span>
                </div>
                <div className="flex items-center justify-between py-1 border-b border-[#1A1C24]">
                  <span className="text-[#71717A]">Healing Engine</span>
                  <span className="text-cyan-400 font-mono">{USER_CREDENTIALS.engine}</span>
                </div>
                <div className="flex items-center justify-between py-1 border-b border-[#1A1C24]">
                  <span className="text-[#71717A]">API Key</span>
                  <div className="flex items-center gap-2">
                    <code className="text-emerald-400 font-mono text-[10px]">
                      {USER_CREDENTIALS.apiKey.slice(0, 16)}...
                    </code>
                    <button
                      onClick={handleCopyKey}
                      className="text-[#71717A] hover:text-white p-0.5 transition-colors cursor-pointer"
                      title="Copy Key"
                    >
                      {copiedKey ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="pt-2 flex justify-end">
                <button
                  onClick={() => setActiveModal("none")}
                  className="px-4 py-1.5 bg-[#181A24] hover:bg-[#222432] border border-[#2A2D3C] text-white rounded text-xs font-medium transition-colors cursor-pointer"
                >
                  Close
                </button>
              </div>
            </div>
          )}

          {/* Gateway Settings Modal */}
          {activeModal === "settings" && (
            <div className="w-full max-w-md rounded-lg border border-[#22242F] bg-[#0C0D12] p-5 shadow-2xl text-xs space-y-4 animate-in fade-in zoom-in-95">
              {/* Modal Header */}
              <div className="flex items-center justify-between border-b border-[#1E2028] pb-3">
                <div className="flex items-center gap-2">
                  <Settings className="w-4 h-4 text-cyan-400" />
                  <h3 className="font-bold text-white text-sm">Gateway Settings</h3>
                </div>
                <button
                  onClick={() => setActiveModal("none")}
                  className="text-[#71717A] hover:text-white p-1 transition-colors cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-3.5">
                {/* Account Handle */}
                <div className="space-y-1">
                  <label className="text-[11px] text-[#71717A]">Account Identifier</label>
                  <input
                    type="text"
                    readOnly
                    value={USER_CREDENTIALS.username}
                    className="w-full px-3 py-1.5 bg-[#12141C] border border-[#22242F] rounded text-white font-mono text-xs select-all focus:outline-hidden"
                  />
                </div>

                {/* Password with Reveal */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="text-[11px] text-[#71717A]">Recovery Password (Hardcoded)</label>
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="text-[10px] text-[#71717A] hover:text-white flex items-center gap-1 transition-colors cursor-pointer"
                    >
                      {showPassword ? (
                        <>
                          <EyeOff className="w-3 h-3" />
                          <span>Hide</span>
                        </>
                      ) : (
                        <>
                          <Eye className="w-3 h-3" />
                          <span>Reveal</span>
                        </>
                      )}
                    </button>
                  </div>
                  <input
                    type={showPassword ? "text" : "password"}
                    readOnly
                    value={USER_CREDENTIALS.password}
                    className="w-full px-3 py-1.5 bg-[#12141C] border border-[#22242F] rounded text-white font-mono text-xs select-all focus:outline-hidden"
                  />
                </div>

                {/* Functional Gateway Preferences */}
                <div className="pt-2 border-t border-[#1E2028] space-y-2.5">
                  <div className="text-[11px] font-semibold text-white">Runtime Preferences</div>

                  <div className="flex items-center justify-between py-1 border-b border-[#1A1C24]">
                    <div>
                      <div className="text-[11px] text-white">Autonomous Selector Healing</div>
                      <div className="text-[10px] text-[#71717A]">Synthesizes AST fixes on TimeoutError</div>
                    </div>
                    <button
                      onClick={() => setAutoHealEnabled(!autoHealEnabled)}
                      className={`px-2.5 py-0.5 rounded text-[10px] font-bold border transition-colors cursor-pointer ${
                        autoHealEnabled
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                          : "bg-neutral-800 text-neutral-400 border-neutral-700"
                      }`}
                    >
                      {autoHealEnabled ? "ENABLED" : "PAUSED"}
                    </button>
                  </div>

                  <div className="flex items-center justify-between py-1 border-b border-[#1A1C24]">
                    <div>
                      <div className="text-[11px] text-white">Headless Playwright Enclave</div>
                      <div className="text-[10px] text-[#71717A]">SSRF sandboxed container</div>
                    </div>
                    <span className="text-[10px] font-mono text-white">Isolated</span>
                  </div>

                  <div className="flex items-center justify-between py-1">
                    <div>
                      <div className="text-[11px] text-white">Circuit Breaker Threshold</div>
                      <div className="text-[10px] text-[#71717A]">Maximum healing attempts</div>
                    </div>
                    <span className="text-[10px] font-mono text-white">2 retries</span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="pt-2 flex justify-end">
                <button
                  onClick={() => setActiveModal("none")}
                  className="px-4 py-1.5 bg-emerald-500 hover:bg-emerald-400 text-black font-semibold rounded text-xs transition-colors cursor-pointer"
                >
                  Done
                </button>
              </div>
            </div>
          )}

          {/* Sign In Modal */}
          {activeModal === "login" && (
            <div className="w-full max-w-sm rounded-lg border border-[#22242F] bg-[#0C0D12] p-5 shadow-2xl text-xs space-y-4 animate-in fade-in zoom-in-95">
              <div className="flex items-center justify-between border-b border-[#1E2028] pb-3">
                <div className="flex items-center gap-2">
                  <Lock className="w-4 h-4 text-emerald-400" />
                  <h3 className="font-bold text-white text-sm">Sign In to Gateway</h3>
                </div>
                <button
                  onClick={() => setActiveModal("none")}
                  className="text-[#71717A] hover:text-white p-1 transition-colors cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="p-2.5 rounded bg-[#12141C] border border-[#22242F] text-[11px] text-[#A1A1AA] space-y-1">
                <div className="text-white font-medium">Hardcoded Account:</div>
                <div>Username: <code className="text-emerald-400">jayant.dev</code></div>
                <div>Password: <code className="text-emerald-400">1qaz2wsx</code></div>
                <button
                  type="button"
                  onClick={prefillCredentials}
                  className="mt-1 text-[10px] text-emerald-400 hover:underline cursor-pointer"
                >
                  Fill Preset Credentials
                </button>
              </div>

              {loginError && (
                <div className="p-2 rounded bg-red-500/10 border border-red-500/25 text-[11px] text-[#EF4444]">
                  {loginError}
                </div>
              )}

              <form onSubmit={handleLogin} className="space-y-3">
                <div className="space-y-1">
                  <label className="text-[11px] text-[#71717A]">Username</label>
                  <input
                    type="text"
                    value={loginUsername}
                    onChange={(e) => setLoginUsername(e.target.value)}
                    className="w-full px-3 py-1.5 bg-[#12141C] border border-[#22242F] rounded text-white font-mono text-xs focus:outline-hidden focus:border-[#10B981]"
                    placeholder="jayant.dev"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] text-[#71717A]">Password</label>
                  <input
                    type="password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    className="w-full px-3 py-1.5 bg-[#12141C] border border-[#22242F] rounded text-white font-mono text-xs focus:outline-hidden focus:border-[#10B981]"
                    placeholder="1qaz2wsx"
                  />
                </div>

                <div className="pt-2 flex gap-2">
                  <button
                    type="submit"
                    className="w-full py-2 bg-emerald-500 hover:bg-emerald-400 text-black font-bold rounded text-xs transition-colors cursor-pointer"
                  >
                    Log In
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>,
        document.body
      )}
    </>
  );
}
