"use client";

import React from "react";
import { RoadmapSummary, RoadmapOrdering } from "@/lib/api";
import { CheckCircle2, Clock, SkipForward, Sparkles, Layers, CircleDot } from "lucide-react";

interface RoadmapProgressProps {
  summary: RoadmapSummary;
  ordering: RoadmapOrdering;
  onToggleOrdering: (ordering: RoadmapOrdering) => void;
  hasMarketData: boolean;
  practiceCompleted?: number;
  practiceTotal?: number;
}

export default function RoadmapProgress({
  summary,
  ordering,
  onToggleOrdering,
  hasMarketData,
  practiceCompleted,
  practiceTotal,
}: RoadmapProgressProps) {
  const percentage = Math.min(100, Math.max(0, summary.progress_percentage || 0));

  return (
    <div className="rounded-2xl bg-white dark:bg-neutral-900/60 border border-slate-200 dark:border-neutral-800 p-5 space-y-4 shadow-sm">
      {/* Top row: Progress headline + ordering toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-slate-900 dark:text-neutral-100 tracking-tight">
              Roadmap Progress
            </h3>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20 font-semibold">
              {percentage}% Complete
            </span>
            {hasMarketData && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-500/20 font-medium">
                Market Intel
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 dark:text-neutral-400">
            {summary.completed_skills} of {summary.total_skills} skills mastered
            {summary.learning_skills > 0 && ` • ${summary.learning_skills} in progress`}
            {summary.skipped_skills > 0 && ` • ${summary.skipped_skills} skipped`}
          </p>
        </div>

        {/* View Mode Switcher: Curated vs Recommended */}
        <div className="flex items-center p-1 rounded-xl bg-slate-100 dark:bg-neutral-950 border border-slate-200 dark:border-neutral-800 text-xs self-start sm:self-auto">
          <button
            type="button"
            onClick={() => onToggleOrdering("curated")}
            aria-pressed={ordering === "curated"}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all cursor-pointer ${
              ordering === "curated"
                ? "bg-white dark:bg-neutral-800 text-slate-900 dark:text-white shadow-sm font-semibold"
                : "text-slate-600 dark:text-neutral-400 hover:text-slate-900 dark:hover:text-neutral-200"
            }`}
            title="Follow the curated stage curriculum from Foundations to Advanced"
          >
            <Layers className="h-3.5 w-3.5" />
            <span>Curated Curriculum</span>
          </button>
          <button
            type="button"
            onClick={() => onToggleOrdering("recommended")}
            aria-pressed={ordering === "recommended"}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all cursor-pointer ${
              ordering === "recommended"
                ? "bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-sm dark:shadow-emerald-950/50 font-semibold"
                : "text-slate-600 dark:text-neutral-400 hover:text-slate-900 dark:hover:text-neutral-200"
            }`}
            title="Prerequisite-safe topological DAG sequence"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>Recommended (DAG)</span>
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-100 dark:bg-neutral-950 rounded-full h-2.5 overflow-hidden border border-slate-200 dark:border-neutral-800/80">
        <div
          className="bg-gradient-to-r from-emerald-500 via-teal-500 to-indigo-500 h-2.5 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${Math.max(percentage > 0 ? 2 : 0, percentage)}%` }}
        />
      </div>

      {/* Bottom status counters */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs pt-1 border-t border-slate-100 dark:border-neutral-800/60">
        <div className="flex flex-wrap items-center gap-4 text-slate-600 dark:text-neutral-400">
          <span className="flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
            <strong className="text-slate-800 dark:text-neutral-200">{summary.completed_skills}</strong> Done
          </span>
          <span className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-sky-600 dark:text-sky-400" />
            <strong className="text-slate-800 dark:text-neutral-200">{summary.learning_skills}</strong> Learning
          </span>
          <span className="flex items-center gap-1.5">
            <SkipForward className="h-3.5 w-3.5 text-slate-400 dark:text-neutral-500" />
            <strong className="text-slate-800 dark:text-neutral-200">{summary.skipped_skills}</strong> Skipped
          </span>
          <span className="flex items-center gap-1.5 text-slate-500 dark:text-neutral-500">
            <CircleDot className="h-3.5 w-3.5 text-slate-400 dark:text-neutral-600" />
            <span>{summary.not_started_skills} Not Started</span>
          </span>
        </div>

        {practiceTotal !== undefined && practiceTotal > 0 && (
          <div className="text-[11px] font-mono text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-200 dark:border-indigo-500/20">
            Practice: {practiceCompleted || 0} / {practiceTotal} Solved
          </div>
        )}
      </div>
    </div>
  );
}
