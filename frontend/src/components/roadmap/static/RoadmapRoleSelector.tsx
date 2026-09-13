"use client";

import React from "react";
import { RoadmapListItem } from "@/lib/api";
import { Compass, ShieldCheck } from "lucide-react";

interface RoadmapRoleSelectorProps {
  roadmaps: RoadmapListItem[];
  selectedRoadmapId: string;
  onSelectRoadmap: (roadmapId: string) => void;
  loading?: boolean;
}

export default function RoadmapRoleSelector({
  roadmaps,
  selectedRoadmapId,
  onSelectRoadmap,
  loading = false,
}: RoadmapRoleSelectorProps) {
  if (loading && roadmaps.length === 0) {
    return (
      <div className="space-y-3">
        <div className="h-4 w-48 rounded bg-slate-200 dark:bg-neutral-800 animate-pulse" />
        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="h-10 w-36 rounded-xl bg-slate-100 dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 animate-pulse flex-shrink-0"
            />
          ))}
        </div>
      </div>
    );
  }

  const canonicalRoadmaps = roadmaps.filter((r) => r.has_market_data);
  const curatedRoadmaps = roadmaps.filter((r) => !r.has_market_data);

  return (
    <div className="space-y-3">
      {/* Header with category legends */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
        <span className="font-semibold tracking-wide uppercase text-[11px] text-slate-500 dark:text-neutral-400">
          Career Track ({roadmaps.length} Tracks Available)
        </span>
        <div className="flex items-center gap-3 text-[11px]">
          <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
            <ShieldCheck className="h-3.5 w-3.5" /> Market Intel
          </span>
          <span className="flex items-center gap-1 text-indigo-600 dark:text-indigo-400 font-medium">
            <Compass className="h-3.5 w-3.5" /> Curated
          </span>
        </div>
      </div>

      {/* Horizontal scrollable tracks */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2.5 pt-1 scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-neutral-800 scrollbar-track-transparent">
        {/* Canonical Market Intel Roles */}
        {canonicalRoadmaps.map((r) => {
          const isSelected = r.id === selectedRoadmapId;
          return (
            <button
              key={r.id}
              type="button"
              onClick={() => onSelectRoadmap(r.id)}
              aria-pressed={isSelected}
              className={`flex-shrink-0 px-3.5 py-2 rounded-xl text-xs font-medium transition-all duration-200 flex items-center gap-2 border cursor-pointer ${
                isSelected
                  ? "bg-emerald-50 dark:bg-emerald-500/15 text-emerald-800 dark:text-emerald-300 border-emerald-400 dark:border-emerald-500/40 shadow-sm dark:shadow-emerald-950/40 font-semibold"
                  : "bg-white dark:bg-neutral-900 text-slate-700 dark:text-neutral-300 border-slate-200 dark:border-neutral-800 hover:border-slate-300 dark:hover:border-neutral-700 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full transition-all ${
                  isSelected ? "bg-emerald-500 ring-2 ring-emerald-300 dark:ring-emerald-800" : "bg-emerald-500/60"
                }`}
              />
              <span>{r.title}</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
                Market
              </span>
            </button>
          );
        })}

        {/* Divider between market intel and curated tracks */}
        {canonicalRoadmaps.length > 0 && curatedRoadmaps.length > 0 && (
          <div className="h-6 w-px bg-slate-300 dark:bg-neutral-800 flex-shrink-0 mx-1" />
        )}

        {/* Curated Career Tracks */}
        {curatedRoadmaps.map((r) => {
          const isSelected = r.id === selectedRoadmapId;
          return (
            <button
              key={r.id}
              type="button"
              onClick={() => onSelectRoadmap(r.id)}
              aria-pressed={isSelected}
              className={`flex-shrink-0 px-3.5 py-2 rounded-xl text-xs font-medium transition-all duration-200 flex items-center gap-2 border cursor-pointer ${
                isSelected
                  ? "bg-indigo-50 dark:bg-indigo-500/15 text-indigo-800 dark:text-indigo-300 border-indigo-400 dark:border-indigo-500/40 shadow-sm dark:shadow-indigo-950/40 font-semibold"
                  : "bg-white dark:bg-neutral-900 text-slate-700 dark:text-neutral-300 border-slate-200 dark:border-neutral-800 hover:border-slate-300 dark:hover:border-neutral-700 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full transition-all ${
                  isSelected ? "bg-indigo-500 ring-2 ring-indigo-300 dark:ring-indigo-800" : "bg-indigo-500/60"
                }`}
              />
              <span>{r.title}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
