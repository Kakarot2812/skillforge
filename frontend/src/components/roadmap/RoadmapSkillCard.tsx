"use client";

import React from "react";
import { RoadmapSkillItem } from "@/lib/api";
import { CheckCircle2, Clock, SkipForward, Circle, Flame, Sparkles, BookOpen, ChevronRight } from "lucide-react";

interface RoadmapSkillCardProps {
  skill: RoadmapSkillItem;
  isSelected?: boolean;
  onSelectSkill: (skill: RoadmapSkillItem) => void;
  hasMarketData: boolean;
}

export default function RoadmapSkillCard({
  skill,
  isSelected = false,
  onSelectSkill,
  hasMarketData,
}: RoadmapSkillCardProps) {
  // Difficulty styling
  const difficultyBadge = {
    BEGINNER: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    INTERMEDIATE: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    ADVANCED: "text-rose-400 bg-rose-500/10 border-rose-500/20",
  }[skill.difficulty] || "text-neutral-400 bg-neutral-800 border-neutral-700";

  // User status visual
  const statusConfig = {
    DONE: {
      icon: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
      label: "Done",
      bg: "border-emerald-500/30 bg-emerald-950/10 hover:border-emerald-500/50",
    },
    LEARNING: {
      icon: <Clock className="h-4 w-4 text-sky-400 animate-pulse" />,
      label: "Learning",
      bg: "border-sky-500/30 bg-sky-950/10 hover:border-sky-500/50",
    },
    SKIPPED: {
      icon: <SkipForward className="h-4 w-4 text-neutral-500" />,
      label: "Skipped",
      bg: "border-neutral-800/80 bg-neutral-900/30 opacity-70 hover:opacity-100",
    },
    NOT_STARTED: {
      icon: <Circle className="h-4 w-4 text-neutral-600" />,
      label: "Not Started",
      bg: "border-neutral-800 bg-neutral-900/60 hover:border-neutral-700",
    },
  }[skill.user_status];

  // Gap & Priority Badges
  const isHighPriority = skill.priority_level === "HIGH";
  const isMediumPriority = skill.priority_level === "MEDIUM";

  return (
    <button
      onClick={() => onSelectSkill(skill)}
      className={`group relative text-left w-full p-4 rounded-xl border transition-all duration-200 flex flex-col justify-between gap-3 ${
        statusConfig.bg
      } ${
        isSelected
          ? "ring-2 ring-emerald-500/80 border-transparent shadow-lg shadow-emerald-950/50"
          : ""
      }`}
    >
      {/* Top row: Skill name + User status icon */}
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-neutral-100 group-hover:text-white truncate">
              {skill.name}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
            {/* Difficulty pill */}
            <span className={`px-2 py-0.5 rounded-md font-mono border font-medium uppercase ${difficultyBadge}`}>
              {skill.difficulty}
            </span>

            {/* Gap status badge (only if canonical role and gap known) */}
            {hasMarketData && skill.gap_status && (
              <>
                {skill.gap_status === "STRONG" && (
                  <span className="px-2 py-0.5 rounded-md font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    ✓ Strong
                  </span>
                )}
                {skill.gap_status === "PARTIAL" && (
                  <span className="px-2 py-0.5 rounded-md font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    → Partial
                  </span>
                )}
                {skill.gap_status === "MISSING" && (
                  <span className="px-2 py-0.5 rounded-md font-medium bg-neutral-800 text-neutral-400 border border-neutral-700">
                    ✕ Missing
                  </span>
                )}
              </>
            )}

            {/* Priority flame badge */}
            {hasMarketData && isHighPriority && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-md font-medium bg-gradient-to-r from-amber-500/20 to-rose-500/20 text-amber-300 border border-amber-500/40">
                <Flame className="h-3 w-3 text-amber-400 animate-pulse" />
                High Priority
              </span>
            )}
            {hasMarketData && isMediumPriority && (
              <span className="px-2 py-0.5 rounded-md font-medium bg-sky-500/10 text-sky-300 border border-sky-500/20">
                ⚡ Medium Priority
              </span>
            )}
          </div>
        </div>

        {/* User state indicator */}
        <div className="flex-shrink-0 flex items-center gap-1.5 pt-0.5">
          {statusConfig.icon}
        </div>
      </div>

      {/* Brief description snippet */}
      <p className="text-xs text-neutral-400 line-clamp-2 leading-relaxed">
        {skill.description}
      </p>

      {/* Bottom meta row: Resources count + Prerequisites note */}
      <div className="flex items-center justify-between text-[11px] text-neutral-500 pt-2 border-t border-neutral-800/40">
        <span className="flex items-center gap-1 text-neutral-400">
          <BookOpen className="h-3 w-3" />
          <span>{skill.resources.length} resources</span>
        </span>

        {skill.prerequisites.length > 0 ? (
          <span className="text-[10px] text-neutral-400 font-mono">
            {skill.prerequisites.length} prereq{skill.prerequisites.length > 1 ? "s" : ""}
          </span>
        ) : (
          <span className="text-[10px] text-emerald-500/80 font-mono">Foundation</span>
        )}

        <ChevronRight className="h-3 w-3 text-neutral-600 group-hover:text-neutral-300 transition-transform group-hover:translate-x-0.5" />
      </div>
    </button>
  );
}
