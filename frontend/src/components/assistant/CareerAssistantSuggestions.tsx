"use client";

import React from "react";
import { HelpCircle, Target, Award, TrendingUp, Compass } from "lucide-react";

export interface CareerAssistantSuggestionsProps {
  onSelectSuggestion: (question: string) => void;
  disabled?: boolean;
}

const SUGGESTIONS = [
  {
    icon: HelpCircle,
    label: "Why is this skill gap important?",
    query: "Why is this skill gap important for my target role?",
  },
  {
    icon: Target,
    label: "What should I focus on next?",
    query: "What should I focus on next based on my prioritized gaps?",
  },
  {
    icon: Award,
    label: "Explain my strongest skills",
    query: "Explain my strongest demonstrated skills and verified evidence.",
  },
  {
    icon: TrendingUp,
    label: "Market demand vs priorities",
    query: "How does market demand affect my learning priorities?",
  },
  {
    icon: Compass,
    label: "Explain my roadmap",
    query: "Explain my current roadmap sequence and milestone prerequisites.",
  },
];

export default function CareerAssistantSuggestions({
  onSelectSuggestion,
  disabled = false,
}: CareerAssistantSuggestionsProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 dark:text-neutral-400 uppercase tracking-wider">
        <span>Suggested Explorations</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((item, idx) => {
          const IconComponent = item.icon;
          return (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectSuggestion(item.query)}
              disabled={disabled}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100/90 dark:bg-neutral-900/80 hover:bg-slate-200 dark:hover:bg-neutral-800 active:bg-slate-300 dark:active:bg-neutral-700/80 border border-slate-200 dark:border-neutral-800 hover:border-slate-300 dark:hover:border-neutral-700 text-slate-700 dark:text-neutral-300 hover:text-slate-900 dark:hover:text-white text-xs font-medium transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed text-left focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
            >
              <IconComponent className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
