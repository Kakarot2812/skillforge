"use client";

import React from "react";
import { RoadmapListItem } from "@/lib/api";
import { Sparkles, Compass, ShieldCheck } from "lucide-react";

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
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div
            key={i}
            className="h-10 w-36 rounded-xl bg-neutral-900/80 border border-neutral-800 animate-pulse flex-shrink-0"
          />
        ))}
      </div>
    );
  }

  const canonicalRoadmaps = roadmaps.filter((r) => r.has_market_data);
  const curatedRoadmaps = roadmaps.filter((r) => !r.has_market_data);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-neutral-400">
        <span className="font-medium tracking-wide uppercase text-[11px] text-neutral-500">
          Select Technology Track ({roadmaps.length} Tracks)
        </span>
        <div className="flex items-center gap-3 text-[11px]">
          <span className="flex items-center gap-1 text-emerald-400">
            <ShieldCheck className="h-3 w-3" /> Live Market Intel
          </span>
          <span className="flex items-center gap-1 text-indigo-400">
            <Compass className="h-3 w-3" /> Curated Catalog
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-neutral-800">
        {/* Canonical Roles */}
        {canonicalRoadmaps.map((r) => {
          const isSelected = r.id === selectedRoadmapId;
          return (
            <button
              key={r.id}
              onClick={() => onSelectRoadmap(r.id)}
              className={`flex-shrink-0 px-3.5 py-2 rounded-xl text-xs font-medium transition-all duration-200 flex items-center gap-2 border ${
                isSelected
                  ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40 shadow-lg shadow-emerald-950/40"
                  : "bg-neutral-900/80 text-neutral-300 border-neutral-800 hover:border-neutral-700 hover:text-white"
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  isSelected ? "bg-emerald-400 animate-pulse" : "bg-emerald-500/60"
                }`}
              />
              <span>{r.title}</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Market
              </span>
            </button>
          );
        })}

        <div className="h-5 w-[1px] bg-neutral-800 flex-shrink-0 mx-1" />

        {/* Curated Domains */}
        {curatedRoadmaps.map((r) => {
          const isSelected = r.id === selectedRoadmapId;
          return (
            <button
              key={r.id}
              onClick={() => onSelectRoadmap(r.id)}
              className={`flex-shrink-0 px-3.5 py-2 rounded-xl text-xs font-medium transition-all duration-200 flex items-center gap-2 border ${
                isSelected
                  ? "bg-indigo-500/15 text-indigo-300 border-indigo-500/40 shadow-lg shadow-indigo-950/40"
                  : "bg-neutral-900/80 text-neutral-300 border-neutral-800 hover:border-neutral-700 hover:text-white"
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  isSelected ? "bg-indigo-400 animate-pulse" : "bg-indigo-500/60"
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
