"use client";

import React from "react";
import { RoadmapSkillItem, RoadmapStageItem } from "@/lib/api";
import RoadmapSkillCard from "./RoadmapSkillCard";
import { Layers } from "lucide-react";

interface RoadmapStageProps {
  stage: RoadmapStageItem;
  selectedSkillId?: string;
  onSelectSkill: (skill: RoadmapSkillItem) => void;
  hasMarketData: boolean;
}

export default function RoadmapStage({
  stage,
  selectedSkillId,
  onSelectSkill,
  hasMarketData,
}: RoadmapStageProps) {
  const completionPct =
    stage.total_skills > 0
      ? Math.round((stage.completed_skills / stage.total_skills) * 100)
      : 0;

  return (
    <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/30 p-5 space-y-4">
      {/* Stage Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-neutral-800/60">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono font-semibold text-emerald-400 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
              Stage {stage.stage_order}
            </span>
            <h4 className="text-base font-bold text-white tracking-tight">
              {stage.name}
            </h4>
          </div>
          {stage.description && (
            <p className="text-xs text-neutral-400 leading-relaxed max-w-2xl">
              {stage.description}
            </p>
          )}
        </div>

        {/* Stage progress */}
        <div className="flex items-center gap-3 sm:text-right flex-shrink-0">
          <div>
            <div className="text-xs font-medium text-neutral-300">
              {stage.completed_skills} / {stage.total_skills} Done
            </div>
            <div className="text-[10px] font-mono text-neutral-500">
              {completionPct}% Stage Progress
            </div>
          </div>
          <div className="w-16 bg-neutral-950 rounded-full h-1.5 overflow-hidden border border-neutral-800">
            <div
              className="bg-emerald-400 h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${completionPct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Skills Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3.5">
        {stage.skills.map((skill) => (
          <RoadmapSkillCard
            key={skill.id}
            skill={skill}
            isSelected={skill.id === selectedSkillId}
            onSelectSkill={onSelectSkill}
            hasMarketData={hasMarketData}
          />
        ))}
      </div>
    </div>
  );
}
