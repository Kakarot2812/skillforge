"use client";

import React from "react";
import { RoadmapSummary } from "@/lib/api";
import { CheckCircle2, Clock, SkipForward, Flame, Sparkles, Layers, ListOrdered } from "lucide-react";

interface RoadmapProgressProps {
  summary: RoadmapSummary;
  ordering: "curated" | "recommended";
  onToggleOrdering: (ordering: "curated" | "recommended") => void;
  hasMarketData: boolean;
}

export default function RoadmapProgress({
  summary,
  ordering,
  onToggleOrdering,
  hasMarketData,
}: RoadmapProgressProps) {
  return (
    <div className="rounded-2xl bg-neutral-900/50 border border-neutral-800 p-5 space-y-4">
      {/* Top row: Progress bar + Stats + Ordering switch */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-neutral-200">
              Personalized Learning Progress
            </h3>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
              {summary.progress_percentage}% Ready
            </span>
          </div>
          <p className="text-xs text-neutral-400 mt-0.5">
            {summary.completed_skills} of {summary.total_skills} skills completed •{" "}
            {summary.learning_skills} in progress • {summary.skipped_skills} skipped
          </p>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center p-1 rounded-xl bg-neutral-950 border border-neutral-800 text-xs self-start sm:self-auto">
          <button
            onClick={() => onToggleOrdering("recommended")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
              ordering === "recommended"
                ? "bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-md shadow-emerald-950/50"
                : "text-neutral-400 hover:text-neutral-200"
            }`}
            title="Prerequisite-safe ordering prioritizing HIGH & MEDIUM skill gaps"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>Recommended Order</span>
          </button>
          <button
            onClick={() => onToggleOrdering("curated")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
              ordering === "curated"
                ? "bg-neutral-800 text-white shadow-sm"
                : "text-neutral-400 hover:text-neutral-200"
            }`}
            title="Standard stage-by-stage progression from Foundations to Advanced"
          >
            <Layers className="h-3.5 w-3.5" />
            <span>Full Roadmap</span>
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-neutral-950 rounded-full h-2.5 overflow-hidden border border-neutral-800/80">
        <div
          className="bg-gradient-to-r from-emerald-500 via-teal-400 to-indigo-500 h-2.5 rounded-full transition-all duration-500 ease-out shadow-sm"
          style={{ width: `${Math.max(2, summary.progress_percentage)}%` }}
        />
      </div>

      {/* Bottom status badges */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs pt-1 border-t border-neutral-800/60">
        <div className="flex items-center gap-4 text-neutral-400">
          <span className="flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            <strong className="text-neutral-200">{summary.completed_skills}</strong> Done
          </span>
          <span className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-sky-400" />
            <strong className="text-neutral-200">{summary.learning_skills}</strong> Learning
          </span>
          <span className="flex items-center gap-1.5">
            <SkipForward className="h-3.5 w-3.5 text-neutral-500" />
            <strong className="text-neutral-200">{summary.skipped_skills}</strong> Skipped
          </span>
          <span className="flex items-center gap-1.5 text-neutral-500">
            <span>{summary.not_started_skills} Not Started</span>
          </span>
        </div>

        {hasMarketData && summary.high_priority_gap_count > 0 && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px] font-medium">
            <Flame className="h-3.5 w-3.5 text-amber-400 animate-pulse" />
            <span>
              {summary.high_priority_gap_count} High-Priority Gap
              {summary.high_priority_gap_count > 1 ? "s" : ""} to close
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
