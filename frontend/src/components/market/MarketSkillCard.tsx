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
    <div className="editorial-card p-5 transition-all flex flex-col justify-between space-y-4">
      {/* Top Row: Skill Name, Category, Trend Badge */}
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-sm font-bold text-foreground truncate">
                {skill.skill_name}
              </h4>
              {skill.category && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-sm bg-surface-subtle text-foreground border border-border shrink-0">
                  {skill.category}
                </span>
              )}
            </div>
            <div className="text-[10px] text-muted font-mono">
              Slug: {skill.canonical_slug}
            </div>
          </div>

          {/* Growth Classification Badge */}
          <div className="shrink-0">
            {trend === "RISING" && (
              <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-sm border border-accent/40 bg-accent/5 text-accent">
                <TrendingUp className="h-3 w-3" aria-hidden="true" />
                <span>RISING</span>
              </span>
            )}
            {trend === "STABLE" && (
              <span className="inline-flex items-center gap-1 text-[10px] font-mono font-medium px-2 py-0.5 rounded-sm border border-border bg-surface-subtle text-foreground">
                <Activity className="h-3 w-3" aria-hidden="true" />
                <span>STABLE</span>
              </span>
            )}
            {trend === "DECLINING" && (
              <span className="inline-flex items-center gap-1 text-[10px] font-mono font-medium px-2 py-0.5 rounded-sm border border-border bg-surface-subtle text-muted">
                <TrendingDown className="h-3 w-3" aria-hidden="true" />
                <span>DECLINING</span>
              </span>
            )}
          </div>
        </div>

        {/* Market vs. Candidate Notice Pill */}
        <div className="text-[10px] text-muted bg-surface-subtle px-2.5 py-1 rounded-sm border border-border">
          <span className="text-foreground font-mono font-medium">Market Benchmark:</span> Employer demand in India
        </div>
      </div>

      {/* Metrics Row: Demand Score and YoY Growth */}
      <div className="grid grid-cols-2 divide-x divide-border border-y border-border py-3">
        {/* Demand Score Metric */}
        <div className="pr-3 space-y-1.5">
          <div className="flex items-center justify-between text-[11px] font-mono text-muted">
            <span>Demand</span>
            <span className="font-mono font-bold text-foreground text-xs">
              {skill.demand_score.toFixed(2)}
            </span>
          </div>
          {/* Hairline bar */}
          <div className="w-full bg-border rounded-none h-1 overflow-hidden">
            <div
              className="bg-accent h-1 transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, demandPercent))}%` }}
              aria-label={`Demand score: ${demandPercent}%`}
            />
          </div>
          <div className="text-[10px] font-mono text-muted text-right">
            {demandPercent}% weight
          </div>
        </div>

        {/* YoY Growth Rate Metric */}
        <div className="pl-3 space-y-1.5">
          <div className="flex items-center justify-between text-[11px] font-mono text-muted">
            <span>Trajectory</span>
            <span
              className={`font-mono font-bold text-xs ${
                trend === "RISING"
                  ? "text-accent"
                  : trend === "DECLINING"
                  ? "text-muted"
                  : "text-foreground"
              }`}
            >
              {formattedGrowth}
            </span>
          </div>
          <div className="text-[10px] text-muted flex items-center justify-between font-mono">
            <span>Historical</span>
            <span className="text-foreground">{trend}</span>
          </div>
          {typeof skill.sample_size === "number" && skill.sample_size > 0 && (
            <div className="text-[10px] font-mono text-muted flex items-center gap-1 truncate">
              <Users className="h-3 w-3 shrink-0" />
              <span>{skill.sample_size.toLocaleString()} postings</span>
            </div>
          )}
        </div>
      </div>

      {/* Action Links: Contextual Navigation to Roadmap or Assistant */}
      <div className="flex items-center justify-between gap-2 text-xs pt-1">
        {onExploreInRoadmap && (
          <button
            type="button"
            onClick={onExploreInRoadmap}
            className="inline-flex items-center gap-1 text-xs text-muted hover:text-foreground font-mono transition-colors cursor-pointer"
          >
            <Compass className="h-3.5 w-3.5" />
            <span>Cross-reference Roadmap</span>
          </button>
        )}

        {onAskAssistant && (
          <button
            type="button"
            onClick={() => onAskAssistant(skill.skill_name)}
            className="inline-flex items-center gap-1 text-xs text-muted hover:text-accent font-mono transition-colors cursor-pointer ml-auto"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>Ask AI</span>
          </button>
        )}
      </div>
    </div>
  );
}
