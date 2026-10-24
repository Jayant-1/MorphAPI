"use client";

import React, { useState, useRef, useEffect } from "react";
import { Globe, ExternalLink, Bot } from "lucide-react";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { HeroArtwork } from "@/components/hero/HeroArtwork";
import { InlineAgentActivity } from "@/components/chat/InlineAgentActivity";
import { InlineEndpoints } from "@/components/chat/InlineEndpoints";
import { startRun, startFollowUpRun, ActiveRunHandle } from "@/lib/api-adapter";
import { RunSession, ChatMessage } from "@/lib/types";

export default function HomePage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeSession, setActiveSession] = useState<RunSession | null>(null);

  const activeRunHandle = useRef<ActiveRunHandle | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom as messages/activities arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming, activeSession?.steps]);

  // Clean up running session on unmount
  useEffect(() => {
    return () => {
      activeRunHandle.current?.stop();
    };
  }, []);

  const handleNewChat = () => {
    activeRunHandle.current?.stop();
    activeRunHandle.current = null;
    setActiveSession(null);
    setMessages([]);
    setIsStreaming(false);
  };

  const handleStartInitialRun = (
    url: string,
    prompt: string,
    fixtureId?: string,
    forceDemo?: boolean
  ) => {
    if (activeRunHandle.current) {
      activeRunHandle.current.stop();
    }

    const userMessageId = "msg_user_" + Date.now();
    const assistantMessageId = "msg_asst_" + (Date.now() + 1);

    const newUserMessage: ChatMessage = {
      id: userMessageId,
      role: "user",
      content: prompt,
      targetUrl: url,
      createdAt: new Date().toISOString(),
    };

    const initialAssistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "I'll inspect the website DOM and synthesize a verified, self-healing API endpoint.",
      createdAt: new Date().toISOString(),
      status: "streaming",
    };

    setMessages([newUserMessage, initialAssistantMessage]);
    setIsStreaming(true);

    const handle = startRun(url, prompt, {
      fixtureId,
      forceDemo,
      onUpdate: (updatedSession) => {
        setActiveSession(updatedSession);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  runSession: updatedSession,
                  status:
                    updatedSession.status === "completed"
                      ? "completed"
                      : updatedSession.status === "failed"
                      ? "error"
                      : updatedSession.status === "awaiting_approval"
                      ? "awaiting_approval"
                      : "streaming",
                  endpoints: updatedSession.endpoints,
                  v2Response: updatedSession.v2Response,
                }
              : msg
          )
        );
      },
      onComplete: (completedSession) => {
        setActiveSession(completedSession);
        setIsStreaming(false);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  content:
                    completedSession.endpoints.length > 0
                      ? "I've synthesized and activated your API endpoint with full contract validation and dynamic OpenAPI 3.1 schema."
                      : "Analysis complete. No structured repeatable records could be verified.",
                  runSession: completedSession,
                  status: "completed",
                  endpoints: completedSession.endpoints,
                  v2Response: completedSession.v2Response,
                }
              : msg
          )
        );
      },
      onError: (errMsg) => {
        setIsStreaming(false);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  content: `Execution interrupted: ${errMsg}`,
                  status: "error",
                }
              : msg
          )
        );
      },
    });

    activeRunHandle.current = handle;
  };

  const handleFollowUp = (followUpPrompt: string) => {
    if (!activeSession || isStreaming) return;

    const userMsgId = "msg_fu_user_" + Date.now();
    const asstMsgId = "msg_fu_asst_" + (Date.now() + 1);

    const newUserMsg: ChatMessage = {
      id: userMsgId,
      role: "user",
      content: followUpPrompt,
      createdAt: new Date().toISOString(),
    };

    const newAsstMsg: ChatMessage = {
      id: asstMsgId,
      role: "assistant",
      content: `Refining API endpoints based on your request: "${followUpPrompt}"`,
      createdAt: new Date().toISOString(),
      status: "streaming",
    };

    setMessages((prev) => [...prev, newUserMsg, newAsstMsg]);
    setIsStreaming(true);

    const handle = startFollowUpRun(activeSession, followUpPrompt, {
      onUpdate: (updatedSession) => {
        setActiveSession(updatedSession);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === asstMsgId
              ? {
                  ...msg,
                  runSession: updatedSession,
                  status: updatedSession.status === "completed" ? "completed" : "streaming",
                  endpoints: updatedSession.endpoints,
                  v2Response: updatedSession.v2Response,
                }
              : msg
          )
        );
      },
      onComplete: (completedSession) => {
        setActiveSession(completedSession);
        setIsStreaming(false);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === asstMsgId
              ? {
                  ...msg,
                  content: "Updated endpoint contract synthesized and live on gateway.",
                  runSession: completedSession,
                  status: "completed",
                  endpoints: completedSession.endpoints,
                  v2Response: completedSession.v2Response,
                }
              : msg
          )
        );
      },
      onError: (errMsg) => {
        setIsStreaming(false);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === asstMsgId
              ? {
                  ...msg,
                  content: `Refinement error: ${errMsg}`,
                  status: "error",
                }
              : msg
          )
        );
      },
    });

    activeRunHandle.current = handle;
  };

  const handleApprove = () => {
    if (!activeSession) return;
    setActiveSession((prev) => {
      if (!prev) return prev;
      const approved: RunSession = {
        ...prev,
        status: "completed",
        approvalMessage: undefined,
        endpoints: prev.endpoints.map((ep) => ({ ...ep, status: "ready" })),
      };
      setMessages((m) =>
        m.map((msg) =>
          msg.runSession?.id === prev.id
            ? { ...msg, status: "completed", runSession: approved, endpoints: approved.endpoints }
            : msg
        )
      );
      return approved;
    });
  };

  const handleReject = () => {
    if (!activeSession) return;
    setActiveSession((prev) => {
      if (!prev) return prev;
      const rejected: RunSession = {
        ...prev,
        status: "failed",
        approvalMessage: undefined,
        errorMessage: "Operator rejected proposed schema. Please refine your request.",
      };
      setMessages((m) =>
        m.map((msg) =>
          msg.runSession?.id === prev.id
            ? { ...msg, status: "error", runSession: rejected }
            : msg
        )
      );
      return rejected;
    });
  };

  const handleRetry = () => {
    if (!activeSession) return;
    handleStartInitialRun(activeSession.targetUrl, activeSession.prompt);
  };

  const inChat = messages.length > 0;
  const isDemo = activeSession?.isDemo;

  // ─────────────────────────────────────────────────────────────────
  // CHAT VIEW — appears after submit. Pure single-column ChatGPT style.
  // Storm-cloud background video with dark gradient overlay, scrollable messages, pinned composer.
  // ─────────────────────────────────────────────────────────────────
  if (inChat) {
    return (
      <div className="relative h-screen overflow-hidden bg-[#10171B] text-[#EDF1EE] flex flex-col font-sans selection:bg-[#C3D1B8] selection:text-[#17201C]">
        {/* Background Storm Clouds Video with Dark Overlay */}
        <HeroArtwork dimmed={true} />

        {/* Header */}
        <ChatHeader onNewChat={handleNewChat} isDemo={isDemo} />

        {/* Scrollable messages area fills remaining height */}
        <div className="relative z-10 flex-1 overflow-y-auto">
          <div className="w-full max-w-[760px] mx-auto px-4 sm:px-6 py-8 space-y-8">
            {messages.map((msg) => (
              <div key={msg.id} className="w-full flex flex-col">
                {msg.role === "user" ? (
                  // User bubble
                  <div className="self-end max-w-[85%] sm:max-w-[75%] rounded-2xl bg-[#202C32]/95 backdrop-blur-sm border border-[#3A4A50] px-5 py-4 space-y-2 shadow-sm">
                    {msg.targetUrl && (
                      <div className="flex items-center gap-1.5 pb-2 mb-1 border-b border-[#3A4A50]/60 text-[13px] font-mono text-[#ADBAB9]">
                        <Globe className="w-3.5 h-3.5 text-[#AEC8D0] shrink-0" />
                        <a
                          href={msg.targetUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[#AEC8D0] hover:underline truncate max-w-[260px] sm:max-w-[360px]"
                        >
                          {msg.targetUrl}
                        </a>
                        <ExternalLink className="w-3 h-3 text-[#ADBAB9] shrink-0" />
                      </div>
                    )}
                    <p className="whitespace-pre-wrap text-[16px] leading-[1.65] text-[#EDF1EE]">
                      {msg.content}
                    </p>
                  </div>
                ) : (
                  // Assistant message
                  <div className="self-start w-full space-y-3">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-[#202C32] border border-[#3A4A50] flex items-center justify-center shrink-0">
                        <Bot className="w-3.5 h-3.5 text-[#C3D1B8]" />
                      </div>
                      <span className="font-syne font-bold text-[14px] tracking-[-0.01em] text-[#EDF1EE]">
                        MorphAPI
                      </span>
                    </div>

                    {msg.status === "streaming" && (
                      <p className="text-[15px] text-[#ADBAB9]">
                        Inspecting DOM cluster and synthesizing verified endpoint…
                      </p>
                    )}

                    <p className="text-[16px] leading-[1.7] text-[#EDF1EE]">
                      {msg.content}
                    </p>

                    {msg.runSession && (
                      <InlineAgentActivity
                        session={msg.runSession}
                        onApprove={handleApprove}
                        onReject={handleReject}
                        onRetry={handleRetry}
                      />
                    )}

                    {msg.endpoints && msg.endpoints.length > 0 && msg.status === "completed" && (
                      <InlineEndpoints endpoints={msg.endpoints} />
                    )}
                  </div>
                )}
              </div>
            ))}

            <div ref={messagesEndRef} className="h-40" />
          </div>
        </div>

        {/* Pinned follow-up composer */}
        <div className="relative z-10 shrink-0 bg-gradient-to-t from-[#10171B] via-[#10171B]/95 to-transparent pb-5 pt-3">
          <ChatComposer
            mode="followup"
            isSubmitting={isStreaming}
            onSubmitFollowUp={handleFollowUp}
          />
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────
  // HERO / LANDING VIEW — full-screen cloud video, centered composer.
  // ─────────────────────────────────────────────────────────────────
  return (
    <div className="relative min-h-screen bg-[#10171B] text-[#EDF1EE] font-sans selection:bg-[#C3D1B8] selection:text-[#17201C] flex flex-col">
      {/* Full-screen background video */}
      <HeroArtwork dimmed={false} />

      {/* Header with V2 status */}
      <ChatHeader onNewChat={handleNewChat} />

      {/* Centered composer in viewport */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center px-4 sm:px-6 py-12">
        <ChatComposer
          mode="initial"
          isSubmitting={isStreaming}
          onSubmitInitial={handleStartInitialRun}
          onSelectSample={(url, prompt) => handleStartInitialRun(url, prompt)}
        />
      </main>
    </div>
  );
}
