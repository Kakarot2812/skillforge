"use client";

import React from "react";
import { RoadmapSkillItem, RoadmapStageItem } from "@/lib/api";
import RoadmapSkillCard from "./RoadmapSkillCard";

interface RoadmapStageProps {
  stage: RoadmapStageItem;
  selectedSkillId?: string;
  onSelectSkill: (skill: RoadmapSkillItem) => void;
  allSkillStatuses?: Record<string, string>;
  isLast?: boolean;
}

export default function RoadmapStage({
  stage,
  selectedSkillId,
  onSelectSkill,
  allSkillStatuses = {},
  isLast = false,
}: RoadmapStageProps) {
  const doneCount = Array.isArray(stage.skills)
    ? stage.skills.filter((s) => s.user_status === "DONE").length
    : stage.completed_skills;

  const totalCount = stage.total_skills || (Array.isArray(stage.skills) ? stage.skills.length : 0);

  const completionPct =
    totalCount > 0
      ? Math.min(100, Math.max(0, Math.round((doneCount / totalCount) * 100)))
      : 0;

  const formattedIndex = String(stage.stage_order).padStart(2, "0");

  return (
    <div className="relative pl-8 sm:pl-10 space-y-4">
      {/* Subtle vertical connecting timeline line */}
      {!isLast && (
        <div className="absolute left-3.5 sm:left-4 top-8 bottom-0 w-[1px] bg-border" />
      )}

      {/* Milestone Node in Timeline */}
      <div className="flex items-center gap-3">
        <div className="absolute -left-0.5 sm:left-0 top-0.5 w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-surface border border-border flex items-center justify-center font-mono text-xs font-bold text-foreground shadow-xs z-10">
          {formattedIndex}
        </div>

        {/* Milestone Header */}
        <div className="flex-1 flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 border-b border-border pb-2.5">
          <div className="space-y-0.5">
            <h4 className="text-sm sm:text-base font-bold text-foreground tracking-tight">
              {formattedIndex} ─ {stage.name}
            </h4>
            {stage.description && (
              <p className="text-xs text-muted leading-relaxed">
                {stage.description}
              </p>
            )}
          </div>

          <div className="flex items-center gap-3 sm:text-right shrink-0 text-xs text-muted">
            <span className="font-mono">
              {doneCount}/{totalCount} Completed
            </span>
            <div className="w-16 bg-surface-subtle border border-border rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-accent h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${completionPct}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Skills Grid for this stage */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 pt-1 pb-4">
        {stage.skills.map((skill) => (
          <RoadmapSkillCard
            key={skill.id}
            skill={skill}
            isSelected={skill.id === selectedSkillId}
            onSelectSkill={onSelectSkill}
            allSkillStatuses={allSkillStatuses}
          />
        ))}
      </div>
    </div>
  );
}
