"use client";

import React from "react";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Users,
  Compass,
  Sparkles,
} from "lucide-react";

export interface MarketSkillItemData {
  skill_id: string;
  skill_name: string;
  canonical_slug: string;
  category?: string;
  demand_score: number;
  growth_rate: number;
  trend?: "RISING" | "STABLE" | "DECLINING";
  sample_size?: number;
  data_updated_at?: string;
}

export interface MarketSkillCardProps {
  skill: MarketSkillItemData;
  onExploreInRoadmap?: () => void;
  onAskAssistant?: (skillName: string) => void;
}

export default function MarketSkillCard({
  skill,
  onExploreInRoadmap,
  onAskAssistant,
}: MarketSkillCardProps) {
  // Format percentage presentation: e.g. 0.78 -> 78%, 0.15 -> +15%
  const demandPercent = Math.round(skill.demand_score * 100);
  const growthPercent = Math.round(skill.growth_rate * 100);
  const formattedGrowth =
    growthPercent > 0 ? `+${growthPercent}%` : `${growthPercent}%`;

  // Trend classification styling strictly based on backend string
  const trend = skill.trend || "STABLE";

  return (
    <div className="bg-white dark:bg-neutral-900/80 border border-neutral-200 dark:border-neutral-800 hover:border-neutral-300 dark:hover:border-neutral-700/80 rounded-2xl p-4 sm:p-5 transition-all shadow-xs hover:shadow-md flex flex-col justify-between space-y-4">
      {/* Top Row: Skill Name, Category, Trend Badge */}
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-sm sm:text-base font-bold text-neutral-900 dark:text-white truncate">
                {skill.skill_name}
              </h4>
              {skill.category && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-400 border border-neutral-200 dark:border-neutral-700/60 shrink-0">
                  {skill.category}
                </span>
              )}
            </div>
            <div className="text-[10px] text-neutral-500 font-mono">
              Slug: {skill.canonical_slug}
            </div>
          </div>

          {/* Growth Classification Badge (Strictly displaying backend trend) */}
          <div className="shrink-0">
            {trend === "RISING" && (
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
                <TrendingUp className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Rising Demand</span>
              </span>
            )}
            {trend === "STABLE" && (
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-500/20">
                <Activity className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Stable Demand</span>
              </span>
            )}
            {trend === "DECLINING" && (
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20">
                <TrendingDown className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Declining Demand</span>
              </span>
            )}
          </div>
        </div>

        {/* Market vs. Candidate Notice Pill */}
        <div className="text-[10px] text-neutral-500 dark:text-neutral-500 bg-neutral-50 dark:bg-neutral-950/60 px-2.5 py-1 rounded-lg border border-neutral-200 dark:border-neutral-800/80">
          <span className="text-neutral-700 dark:text-neutral-400 font-medium">Market Fact:</span> Employer hiring demand in India (not your personal skill status)
        </div>
      </div>

      {/* Metrics Row: Demand Score and YoY Growth */}
      <div className="grid grid-cols-2 gap-3 pt-1">
        {/* Demand Score Metric */}
        <div className="p-3 rounded-xl bg-neutral-50 dark:bg-neutral-950/70 border border-neutral-200 dark:border-neutral-800 space-y-1.5">
          <div className="flex items-center justify-between text-[11px] text-neutral-600 dark:text-neutral-400">
            <span>Demand Score</span>
            <span className="font-mono font-bold text-neutral-900 dark:text-white text-xs">
              {skill.demand_score.toFixed(2)}
            </span>
          </div>
          {/* Progress bar visual equivalent */}
          <div className="w-full bg-neutral-200 dark:bg-neutral-800 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-indigo-500 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(0, demandPercent))}%` }}
              aria-label={`Demand score: ${demandPercent}%`}
            />
          </div>
          <div className="text-[10px] font-mono text-indigo-600 dark:text-indigo-300 text-right font-medium">
            {demandPercent}% Market Weight
          </div>
        </div>

        {/* YoY Growth Rate Metric */}
        <div className="p-3 rounded-xl bg-neutral-50 dark:bg-neutral-950/70 border border-neutral-200 dark:border-neutral-800 space-y-1.5">
          <div className="flex items-center justify-between text-[11px] text-neutral-600 dark:text-neutral-400">
            <span>YoY Trajectory</span>
            <span
              className={`font-mono font-bold text-xs ${
                trend === "RISING"
                  ? "text-emerald-600 dark:text-emerald-400"
                  : trend === "DECLINING"
                  ? "text-amber-600 dark:text-amber-400"
                  : "text-blue-600 dark:text-blue-300"
              }`}
            >
              {formattedGrowth}
            </span>
          </div>
          <div className="text-[10px] text-neutral-500 flex items-center justify-between">
            <span>Historical</span>
            <span className="font-mono text-neutral-700 dark:text-neutral-300">{trend}</span>
          </div>
          {typeof skill.sample_size === "number" && skill.sample_size > 0 && (
            <div className="text-[10px] font-mono text-neutral-500 flex items-center gap-1 truncate">
              <Users className="h-3 w-3 shrink-0" />
              <span>{skill.sample_size.toLocaleString()} postings</span>
            </div>
          )}
        </div>
      </div>

      {/* Action Links: Contextual Navigation to Roadmap or Assistant */}
      <div className="pt-2 border-t border-neutral-200 dark:border-neutral-800/80 flex items-center justify-between gap-2 text-xs">
        {onExploreInRoadmap && (
          <button
            type="button"
            onClick={onExploreInRoadmap}
            className="inline-flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 font-medium transition-colors cursor-pointer text-xs"
          >
            <Compass className="h-3.5 w-3.5" />
            <span>Cross-reference Roadmap</span>
          </button>
        )}

        {onAskAssistant && (
          <button
            type="button"
            onClick={() => onAskAssistant(skill.skill_name)}
            className="inline-flex items-center gap-1.5 text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 font-medium transition-colors cursor-pointer text-xs ml-auto"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>Ask Assistant</span>
          </button>
        )}
      </div>
    </div>
  );
}
