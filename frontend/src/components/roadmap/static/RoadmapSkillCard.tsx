"use client";

import React from "react";
import { RoadmapSkillItem } from "@/lib/api";
import {
  CheckCircle2,
  Clock,
  SkipForward,
  Circle,
  BookOpen,
  ChevronRight,
  Code2,
  ShieldCheck,
  Lock,
} from "lucide-react";

interface RoadmapSkillCardProps {
  skill: RoadmapSkillItem;
  isSelected?: boolean;
  onSelectSkill: (skill: RoadmapSkillItem) => void;
  allSkillStatuses?: Record<string, string>;
}

export default function RoadmapSkillCard({
  skill,
  isSelected = false,
  onSelectSkill,
  allSkillStatuses = {},
}: RoadmapSkillCardProps) {
  // Difficulty styling
  const difficultyBadge = {
    BEGINNER: "text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20",
    INTERMEDIATE: "text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/20",
    ADVANCED: "text-rose-700 dark:text-rose-400 bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/20",
  }[skill.difficulty] || "text-slate-600 dark:text-neutral-400 bg-slate-100 dark:bg-neutral-800 border-slate-200 dark:border-neutral-700";

  // User learning status visual config
  const status = skill.user_status || "NOT_STARTED";
  const statusConfig = {
    DONE: {
      icon: <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />,
      label: "Done",
      cardStyle: "border-emerald-300 dark:border-emerald-500/30 bg-emerald-50/40 dark:bg-emerald-950/10 hover:border-emerald-400 dark:hover:border-emerald-500/50",
    },
    LEARNING: {
      icon: <Clock className="h-4 w-4 text-sky-600 dark:text-sky-400 animate-pulse" />,
      label: "Learning",
      cardStyle: "border-sky-300 dark:border-sky-500/30 bg-sky-50/40 dark:bg-sky-950/10 hover:border-sky-400 dark:hover:border-sky-500/50",
    },
    SKIPPED: {
      icon: <SkipForward className="h-4 w-4 text-slate-400 dark:text-neutral-500" />,
      label: "Skipped",
      cardStyle: "border-slate-200 dark:border-neutral-800 bg-slate-50/50 dark:bg-neutral-900/30 opacity-75 hover:opacity-100",
    },
    NOT_STARTED: {
      icon: <Circle className="h-4 w-4 text-slate-300 dark:text-neutral-600" />,
      label: "Not Started",
      cardStyle: "border-slate-200 dark:border-neutral-800 bg-white dark:bg-neutral-900/60 hover:border-slate-300 dark:hover:border-neutral-700",
    },
  }[status] || {
    icon: <Circle className="h-4 w-4 text-slate-300 dark:text-neutral-600" />,
    label: "Not Started",
    cardStyle: "border-slate-200 dark:border-neutral-800 bg-white dark:bg-neutral-900/60 hover:border-slate-300 dark:hover:border-neutral-700",
  };

  // Check prerequisite satisfaction status
  const totalPrereqs = skill.prerequisites?.length || 0;
  let unsatisfiedPrereqs = 0;
  if (totalPrereqs > 0 && Object.keys(allSkillStatuses).length > 0) {
    unsatisfiedPrereqs = skill.prerequisites.filter((p) => {
      const pStatus = allSkillStatuses[p.skill_id] || allSkillStatuses[p.skill_slug];
      return pStatus !== "DONE";
    }).length;
  }

  const isPrereqPending = totalPrereqs > 0 && unsatisfiedPrereqs > 0;

  return (
    <button
      type="button"
      onClick={() => onSelectSkill(skill)}
      aria-label={`Select skill: ${skill.name}. Status: ${statusConfig.label}`}
      className={`group relative text-left w-full p-4 rounded-xl border transition-all duration-200 flex flex-col justify-between gap-3 cursor-pointer shadow-sm ${
        statusConfig.cardStyle
      } ${
        isSelected
          ? "ring-2 ring-emerald-500 border-emerald-500 dark:border-transparent dark:ring-emerald-400 shadow-md dark:shadow-emerald-950/50"
          : ""
      }`}
    >
      {/* Top row: Skill name + status icon */}
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-1.5 min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm text-slate-900 dark:text-neutral-100 group-hover:text-emerald-700 dark:group-hover:text-white transition-colors truncate">
              {skill.name}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
            {/* Difficulty pill */}
            <span className={`px-2 py-0.5 rounded-md font-mono border font-semibold uppercase ${difficultyBadge}`}>
              {skill.difficulty}
            </span>

            {/* Canonical mapping badge */}
            {skill.canonical_skill_id && (
              <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-500/20 font-medium">
                <ShieldCheck className="h-3 w-3" />
                Verified
              </span>
            )}

            {/* Prerequisite status tag */}
            {totalPrereqs === 0 ? (
              <span className="px-1.5 py-0.5 rounded bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20 font-mono">
                Foundation
              </span>
            ) : isPrereqPending ? (
              <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20 font-mono" title={`${unsatisfiedPrereqs} prerequisite(s) pending completion`}>
                <Lock className="h-2.5 w-2.5" />
                {unsatisfiedPrereqs} Prereq{unsatisfiedPrereqs > 1 ? "s" : ""} Pending
              </span>
            ) : (
              <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-neutral-800 text-slate-600 dark:text-neutral-400 border border-slate-200 dark:border-neutral-700 font-mono">
                {totalPrereqs} Prereq{totalPrereqs > 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>

        {/* User state indicator icon */}
        <div className="flex-shrink-0 pt-0.5" title={`Status: ${statusConfig.label}`}>
          {statusConfig.icon}
        </div>
      </div>

      {/* Description */}
      <p className="text-xs text-slate-600 dark:text-neutral-400 line-clamp-2 leading-relaxed">
        {skill.description}
      </p>

      {/* Bottom meta row */}
      <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-neutral-500 pt-2 border-t border-slate-100 dark:border-neutral-800/60">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1" title={`${skill.resources?.length || 0} curated learning resources`}>
            <BookOpen className="h-3 w-3 text-slate-400 dark:text-neutral-500" />
            <span>{skill.resources?.length || 0} resources</span>
          </span>
          <span className="flex items-center gap-1" title={`${skill.practice_problems?.length || 0} progressive practice problems`}>
            <Code2 className="h-3 w-3 text-slate-400 dark:text-neutral-500" />
            <span>{skill.practice_problems?.length || 0} problems</span>
          </span>
        </div>

        <ChevronRight className="h-3.5 w-3.5 text-slate-400 dark:text-neutral-600 group-hover:text-slate-700 dark:group-hover:text-neutral-300 transition-transform group-hover:translate-x-0.5" />
      </div>
    </button>
  );
}
