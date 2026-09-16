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
    BEGINNER: "text-accent bg-accent/5 border-accent/30",
    INTERMEDIATE: "text-foreground bg-surface-subtle border-border",
    ADVANCED: "text-foreground bg-surface-subtle border-border font-bold",
  }[skill.difficulty] || "text-muted bg-surface-subtle border-border";

  // User learning status visual config
  const status = skill.user_status || "NOT_STARTED";
  const statusConfig = {
    DONE: {
      icon: <CheckCircle2 className="h-4 w-4 text-accent" />,
      label: "Done",
      cardStyle: "border-accent/40 bg-accent/5",
    },
    LEARNING: {
      icon: <Clock className="h-4 w-4 text-foreground animate-pulse" />,
      label: "Learning",
      cardStyle: "border-foreground/30 bg-surface-subtle",
    },
    SKIPPED: {
      icon: <SkipForward className="h-4 w-4 text-muted" />,
      label: "Skipped",
      cardStyle: "border-border bg-surface-subtle opacity-60 hover:opacity-100",
    },
    NOT_STARTED: {
      icon: <Circle className="h-4 w-4 text-subtle" />,
      label: "Not Started",
      cardStyle: "border-border bg-surface hover:border-foreground/40",
    },
  }[status] || {
    icon: <Circle className="h-4 w-4 text-subtle" />,
    label: "Not Started",
    cardStyle: "border-border bg-surface hover:border-foreground/40",
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
      className={`group relative text-left w-full p-4 rounded-md border transition-all duration-200 flex flex-col justify-between gap-3 cursor-pointer shadow-xs ${
        statusConfig.cardStyle
      } ${
        isSelected
          ? "ring-1 ring-accent border-accent shadow-xs"
          : ""
      }`}
    >
      {/* Top row: Skill name + status icon */}
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-1.5 min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm text-foreground group-hover:text-accent transition-colors truncate">
              {skill.name}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
            {/* Difficulty pill */}
            <span className={`px-2 py-0.5 rounded-sm font-mono border font-semibold uppercase ${difficultyBadge}`}>
              {skill.difficulty}
            </span>

            {/* Canonical mapping badge */}
            {skill.canonical_skill_id && (
              <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-sm bg-surface-subtle text-foreground border border-border font-mono font-medium">
                <ShieldCheck className="h-3 w-3 text-accent" />
                Verified
              </span>
            )}

            {/* Prerequisite status tag */}
            {totalPrereqs === 0 ? (
              <span className="px-1.5 py-0.5 rounded-sm bg-surface-subtle text-muted border border-border font-mono">
                Foundation
              </span>
            ) : isPrereqPending ? (
              <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-sm bg-surface-subtle text-muted border border-border font-mono" title={`${unsatisfiedPrereqs} prerequisite(s) pending completion`}>
                <Lock className="h-2.5 w-2.5" />
                {unsatisfiedPrereqs} Prereq{unsatisfiedPrereqs > 1 ? "s" : ""} Pending
              </span>
            ) : (
              <span className="px-1.5 py-0.5 rounded-sm bg-surface-subtle text-muted border border-border font-mono">
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
      <p className="text-xs text-muted line-clamp-2 leading-relaxed">
        {skill.description}
      </p>

      {/* Bottom meta row */}
      <div className="flex items-center justify-between text-[11px] text-muted pt-2 border-t border-border font-mono">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1" title={`${skill.resources?.length || 0} curated learning resources`}>
            <BookOpen className="h-3 w-3 text-subtle" />
            <span>{skill.resources?.length || 0} resources</span>
          </span>
          <span className="flex items-center gap-1" title={`${skill.practice_problems?.length || 0} progressive practice problems`}>
            <Code2 className="h-3 w-3 text-subtle" />
            <span>{skill.practice_problems?.length || 0} problems</span>
          </span>
        </div>

        <ChevronRight className="h-3.5 w-3.5 text-subtle group-hover:text-foreground transition-transform group-hover:translate-x-0.5" />
      </div>
    </button>
  );
}
