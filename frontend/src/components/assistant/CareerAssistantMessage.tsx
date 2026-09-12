"use client";

import React from "react";
import { Bot, User, ShieldCheck, AlertTriangle, Tag, Sparkles } from "lucide-react";
import { ChatResponseStatus } from "@/lib/types/chat";

export interface ChatMessageItem {
  id: string;
  sender: "user" | "assistant";
  content: string;
  status?: ChatResponseStatus;
  referencedSkillIds?: string[];
  timestamp: string;
  model?: string;
}

export interface CareerAssistantMessageProps {
  message: ChatMessageItem;
  skillNameMap?: Map<string, string>;
}

export default function CareerAssistantMessage({
  message,
  skillNameMap,
}: CareerAssistantMessageProps) {
  const isUser = message.sender === "user";

  return (
    <div
      className={`flex gap-3 sm:gap-4 p-4 rounded-2xl transition-colors ${
        isUser
          ? "bg-slate-100/80 dark:bg-neutral-900/40 border border-slate-200 dark:border-neutral-800/80 ml-4 sm:ml-12"
          : "bg-white dark:bg-neutral-900/80 border border-slate-200 dark:border-neutral-800 mr-4 sm:mr-12 shadow-sm dark:shadow-md"
      }`}
    >
      {/* Avatar Icon */}
      <div className="shrink-0 mt-0.5">
        {isUser ? (
          <div className="h-8 w-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shadow-inner">
            <User className="h-4 w-4" />
          </div>
        ) : (
          <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shadow-inner">
            <Bot className="h-4 w-4" />
          </div>
        )}
      </div>

      {/* Message Content Container */}
      <div className="flex-1 space-y-2 min-w-0">
        {/* Header: Sender Name, Badges, Timestamp */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-900 dark:text-white">
              {isUser ? "You (Candidate)" : "SkillForge AI"}
            </span>

            {!isUser && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-700 dark:text-purple-300 border border-purple-500/20 font-semibold">
                {message.model || "qwen3:8b"}
              </span>
            )}

            {!isUser && message.status === "EXPLANATORY" && (
              <span className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
                <ShieldCheck className="h-3 w-3" />
                Grounded Explanation
              </span>
            )}

            {!isUser && message.status === "INSUFFICIENT_EVIDENCE" && (
              <span className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20">
                <AlertTriangle className="h-3 w-3" />
                Insufficient Evidence
              </span>
            )}
          </div>

          <span className="text-[10px] text-slate-400 dark:text-neutral-500 font-mono">
            {message.timestamp}
          </span>
        </div>

        {/* Text Body: Safe string rendering avoiding arbitrary HTML */}
        <div className="text-xs sm:text-sm text-slate-700 dark:text-neutral-200 leading-relaxed space-y-2 break-words">
          {message.content.split("\n\n").map((paragraph, pIdx) => (
            <p key={pIdx} className="whitespace-pre-line">
              {paragraph}
            </p>
          ))}
        </div>

        {/* Referenced Skills Chips if returned by backend */}
        {!isUser && message.referencedSkillIds && message.referencedSkillIds.length > 0 && (
          <div className="pt-2 border-t border-slate-200 dark:border-neutral-800/60 flex flex-wrap items-center gap-1.5">
            <span className="text-[10px] font-mono text-slate-500 dark:text-neutral-500 flex items-center gap-1 uppercase">
              <Tag className="h-3 w-3" /> Referenced Context:
            </span>
            {message.referencedSkillIds.map((skillId) => {
              const label = skillNameMap?.get(skillId) || skillId.slice(0, 8);
              return (
                <span
                  key={skillId}
                  className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-slate-100 dark:bg-neutral-800/80 text-slate-700 dark:text-neutral-300 border border-slate-200 dark:border-neutral-700/60"
                  title={`Skill ID: ${skillId}`}
                >
                  {label}
                </span>
              );
            })}
          </div>
        )}

        {/* Grounding Disclaimer on Assistant Responses */}
        {!isUser && (
          <div className="pt-1 flex items-center gap-1.5 text-[10px] text-slate-400 dark:text-neutral-500">
            <Sparkles className="h-3 w-3 text-slate-400 dark:text-neutral-500" />
            <span>Explanatory guidance over verified evidence. Does not alter canonical records.</span>
          </div>
        )}
      </div>
    </div>
  );
}
