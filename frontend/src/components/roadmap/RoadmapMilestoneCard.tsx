"use client";

import React, { useState } from "react";
import {
  RoadmapMilestoneItem,
  MilestoneStatus,
} from "@/lib/types/roadmap";
import {
  CheckCircle2,
  Clock,
  Code2,
  ChevronDown,
  ChevronUp,
  BookOpen,
  Compass,
  FileCheck2,
  Layers,
  ShieldCheck,
} from "lucide-react";
import VerificationModal from "@/components/verification/VerificationModal";

export interface RoadmapMilestoneCardProps {
  milestone: RoadmapMilestoneItem;
  roadmapId?: string | null;
  onViewResources: (skillId: string, skillName: string) => void;
  onMilestoneVerified?: () => void;
}

const STATUS_BADGES: Record<
  MilestoneStatus,
  { label: string; bg: string; text: string; border: string; icon: React.ComponentType<{ className?: string }> }
> = {
  NOT_STARTED: {
    label: "Not Started",
    bg: "bg-slate-100 dark:bg-neutral-800/80",
    text: "text-slate-600 dark:text-neutral-400",
    border: "border-slate-200 dark:border-neutral-700",
    icon: Clock,
  },
  IN_PROGRESS: {
    label: "In Progress",
    bg: "bg-blue-500/10",
    text: "text-blue-600 dark:text-blue-400",
    border: "border-blue-500/30",
    icon: Clock,
  },
  COMPLETED: {
    label: "Completed",
    bg: "bg-amber-500/10",
    text: "text-amber-600 dark:text-amber-400",
    border: "border-amber-500/30",
    icon: CheckCircle2,
  },
  VERIFIED: {
    label: "Verified (Code Artifacts)",
    bg: "bg-emerald-500/10",
    text: "text-emerald-600 dark:text-emerald-400",
    border: "border-emerald-500/30",
    icon: CheckCircle2,
  },
};

const PRIORITY_BADGES: Record<string, { bg: string; text: string; border: string }> = {
  HIGH: {
    bg: "bg-rose-500/10",
    text: "text-rose-600 dark:text-rose-400",
    border: "border-rose-500/20",
  },
  MEDIUM: {
    bg: "bg-amber-500/10",
    text: "text-amber-600 dark:text-amber-400",
    border: "border-amber-500/20",
  },
  LOW: {
    bg: "bg-blue-500/10",
    text: "text-blue-600 dark:text-blue-400",
    border: "border-blue-500/20",
  },
};

export default function RoadmapMilestoneCard({
  milestone,
  roadmapId,
  onViewResources,
  onMilestoneVerified,
}: RoadmapMilestoneCardProps) {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [isVerificationOpen, setIsVerificationOpen] = useState<boolean>(false);

  const statusConfig = STATUS_BADGES[milestone.status] || STATUS_BADGES.NOT_STARTED;
  const StatusIcon = statusConfig.icon;
  const priorityConfig = milestone.priority_level
    ? PRIORITY_BADGES[milestone.priority_level] || PRIORITY_BADGES.LOW
    : null;

  const project = milestone.project;
  const hasPrereqs = milestone.prerequisites && milestone.prerequisites.length > 0;
  const hasObjectives = milestone.learning_objectives && milestone.learning_objectives.length > 0;

  return (
    <div
      className={`rounded-2xl border transition-all duration-200 overflow-hidden ${
        milestone.status === "VERIFIED"
          ? "bg-emerald-50/20 dark:bg-neutral-900/90 border-emerald-500/30 shadow-md dark:shadow-emerald-950/20"
          : milestone.status === "IN_PROGRESS"
          ? "bg-blue-50/20 dark:bg-neutral-900/90 border-blue-500/40 shadow-md dark:shadow-blue-950/20"
          : "bg-white/80 dark:bg-neutral-900/60 border-slate-200/90 dark:border-neutral-800/90 hover:border-slate-300 dark:hover:border-neutral-700/80 shadow-sm"
      }`}
    >
      {/* Top Header Card */}
      <div className="p-5 sm:p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
          {/* Milestone Order & Title */}
          <div className="flex items-start gap-3.5">
            <div className="h-10 w-10 rounded-xl bg-slate-100 dark:bg-neutral-955 border border-slate-200 dark:border-neutral-800 flex items-center justify-center font-mono text-sm font-bold text-slate-800 dark:text-neutral-200 shrink-0 shadow-inner">
              #{milestone.order_index}
            </div>
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white tracking-tight">
                  {milestone.skill_name}
                </h3>
                {milestone.category && (
                  <span className="text-[11px] font-mono text-slate-600 dark:text-neutral-400 px-2 py-0.5 rounded bg-slate-100 dark:bg-neutral-800/80 border border-slate-200 dark:border-neutral-700/60">
                    {milestone.category}
                  </span>
                )}
                {milestone.is_transitive_prerequisite && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20 font-semibold">
                    Foundational Prerequisite
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-600 dark:text-neutral-400 leading-relaxed max-w-2xl">
                {milestone.reason}
              </p>
            </div>
          </div>

          {/* Milestone Status Badge */}
          <div className="flex sm:flex-col items-center sm:items-end gap-2 shrink-0">
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${statusConfig.bg} ${statusConfig.text} ${statusConfig.border}`}
            >
              <StatusIcon className="h-3.5 w-3.5 shrink-0" />
              <span>{statusConfig.label}</span>
            </span>

            {priorityConfig && (
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-mono font-bold uppercase tracking-wider border ${priorityConfig.bg} ${priorityConfig.text} ${priorityConfig.border}`}
              >
                {milestone.priority_level} Priority
              </span>
            )}
          </div>
        </div>

        {/* Metric Badges Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-2">
          {/* Priority Score */}
          <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-neutral-950/60 border border-slate-200 dark:border-neutral-800/80 text-center sm:text-left">
            <span className="text-[10px] font-medium text-slate-500 dark:text-neutral-500 uppercase tracking-wider block">
              Priority Score
            </span>
            <span className="text-sm font-mono font-bold text-slate-800 dark:text-neutral-200">
              {milestone.priority_score !== null && milestone.priority_score !== undefined
                ? `${Math.round(milestone.priority_score * 100)}%`
                : "--"}
            </span>
          </div>

          {/* Market Demand */}
          <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-neutral-950/60 border border-slate-200 dark:border-neutral-800/80 text-center sm:text-left">
            <span className="text-[10px] font-medium text-slate-500 dark:text-neutral-500 uppercase tracking-wider block">
              Industry Demand
            </span>
            <span className="text-sm font-mono font-bold text-slate-800 dark:text-neutral-200">
              {milestone.demand_score !== null && milestone.demand_score !== undefined
                ? `${Math.round(milestone.demand_score * 100)}%`
                : "--"}
            </span>
          </div>

          {/* Growth Rate */}
          <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-neutral-950/60 border border-slate-200 dark:border-neutral-800/80 text-center sm:text-left">
            <span className="text-[10px] font-medium text-slate-500 dark:text-neutral-500 uppercase tracking-wider block">
              Market Growth
            </span>
            <span className="text-sm font-mono font-bold text-emerald-600 dark:text-emerald-400">
              {milestone.growth_rate !== null && milestone.growth_rate !== undefined
                ? `+${Math.round(milestone.growth_rate * 100)}%`
                : "--"}
            </span>
          </div>

          {/* Gap Status */}
          <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-neutral-950/60 border border-slate-200 dark:border-neutral-800/80 text-center sm:text-left">
            <span className="text-[10px] font-medium text-slate-500 dark:text-neutral-500 uppercase tracking-wider block">
              Candidate Gap
            </span>
            <span
              className={`text-sm font-mono font-bold ${
                milestone.gap_status === "MISSING" ? "text-rose-600 dark:text-rose-400" : "text-amber-600 dark:text-amber-400"
              }`}
            >
              {milestone.gap_status}
            </span>
          </div>
        </div>

        {/* Action Row */}
        <div className="pt-2 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 dark:border-neutral-800/60">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onViewResources(milestone.skill_id, milestone.skill_name)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-500/10 hover:bg-blue-500/20 text-blue-600 dark:text-blue-400 border border-blue-500/20 text-xs font-semibold transition-colors cursor-pointer"
            >
              <BookOpen className="h-3.5 w-3.5" />
              <span>Approved Learning Resources</span>
              {milestone.resources && milestone.resources.length > 0 && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full bg-blue-500/20 text-blue-700 dark:text-blue-300 text-[10px] font-mono">
                  {milestone.resources.length}
                </span>
              )}
            </button>

            {project && (
              <span className="inline-flex items-center gap-1 text-xs text-slate-600 dark:text-neutral-400 bg-slate-100 dark:bg-neutral-950 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-neutral-800">
                <Code2 className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
                <span className="hidden sm:inline">Project Challenge:</span>
                <strong className="text-slate-800 dark:text-neutral-200 font-medium truncate max-w-[150px]">
                  {project.title}
                </strong>
              </span>
            )}

            {/* Verification Button */}
            {roadmapId && (
              <button
                type="button"
                onClick={() => setIsVerificationOpen(true)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                  milestone.status === "VERIFIED"
                    ? "bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                    : "bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 border-indigo-500/30"
                }`}
                aria-label={`Verify milestone ${milestone.skill_name} with GitHub`}
              >
                {milestone.status === "VERIFIED" ? (
                  <>
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Verified (Inspect)</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="h-3.5 w-3.5" />
                    <span>Verify with GitHub</span>
                  </>
                )}
              </button>
            )}
          </div>

          {/* Expand/Collapse Toggle */}
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-neutral-950 hover:bg-slate-200 dark:hover:bg-neutral-800 text-slate-700 dark:text-neutral-300 text-xs font-medium border border-slate-200 dark:border-neutral-800 transition-colors cursor-pointer ml-auto"
            aria-expanded={isExpanded}
            aria-label={`Toggle details for milestone ${milestone.skill_name}`}
          >
            <span>{isExpanded ? "Collapse Details" : "View Details & Projects"}</span>
            {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Expandable Details Area */}
      {isExpanded && (
        <div className="border-t border-slate-200 dark:border-neutral-800 bg-slate-50/80 dark:bg-neutral-950/70 p-5 sm:p-6 space-y-5 animate-in slide-in-from-top-2 duration-150">
          {/* Prerequisites Section */}
          {hasPrereqs && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 dark:text-neutral-300">
                <Layers className="h-3.5 w-3.5 text-slate-400 dark:text-neutral-500" />
                <span>Prerequisites (Topological DAG Dependencies):</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {milestone.prerequisites.map((req) => (
                  <div
                    key={req.skill_id}
                    className="p-2.5 rounded-xl bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 flex items-center justify-between gap-2 text-xs"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <span
                        className={`h-2 w-2 rounded-full ${
                          req.is_satisfied ? "bg-emerald-500 dark:bg-emerald-400" : "bg-amber-500 dark:bg-amber-400"
                        }`}
                      />
                      <span className="text-slate-800 dark:text-neutral-200 font-medium truncate">{req.skill_name}</span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0 font-mono text-[10px]">
                      <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-neutral-800 text-slate-600 dark:text-neutral-400 border border-slate-200 dark:border-neutral-700">
                        {req.dependency_type}
                      </span>
                      <span
                        className={`px-1.5 py-0.5 rounded font-semibold ${
                          req.is_satisfied
                            ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                        }`}
                      >
                        {req.is_satisfied ? "Satisfied" : "Pending"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Learning Objectives */}
          {hasObjectives && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 dark:text-neutral-300">
                <Compass className="h-3.5 w-3.5 text-slate-400 dark:text-neutral-500" />
                <span>Actionable Learning Competencies:</span>
              </div>
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-600 dark:text-neutral-400">
                {milestone.learning_objectives.map((obj, idx) => (
                  <li
                    key={idx}
                    className="p-2.5 rounded-xl bg-white/80 dark:bg-neutral-900/60 border border-slate-200 dark:border-neutral-800/80 flex items-start gap-2"
                  >
                    <span className="text-blue-500 dark:text-blue-400 font-mono text-xs">•</span>
                    <span className="text-slate-700 dark:text-neutral-300">{obj}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Practical Project Challenge Details */}
          {project && (
            <div className="p-4 rounded-xl bg-white dark:bg-neutral-900 border border-indigo-500/20 space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 dark:border-neutral-800 pb-2.5">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                    <Code2 className="h-4 w-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-white">{project.title}</h4>
                    <span className="text-[11px] text-slate-500 dark:text-neutral-400">Practical Engineering Challenge</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-500/20 uppercase font-semibold">
                    Tier: {project.difficulty}
                  </span>
                  {project.estimated_hours && (
                    <span className="text-[11px] text-slate-500 dark:text-neutral-400 font-mono">
                      ~{project.estimated_hours} hrs
                    </span>
                  )}
                </div>
              </div>

              <p className="text-xs text-slate-600 dark:text-neutral-300 leading-relaxed">{project.description}</p>

              {/* Deliverables & Verification Criteria */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-xs">
                {project.deliverables && project.deliverables.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="font-semibold text-slate-600 dark:text-neutral-400 flex items-center gap-1">
                      <FileCheck2 className="h-3 w-3 text-slate-400 dark:text-neutral-500" />
                      Expected Code Deliverables:
                    </span>
                    <div className="space-y-1">
                      {project.deliverables.map((deliv, idx) => (
                        <div
                          key={idx}
                          className="px-2.5 py-1 rounded bg-slate-50 dark:bg-neutral-950 border border-slate-200 dark:border-neutral-800 font-mono text-[11px] text-slate-700 dark:text-neutral-300 truncate"
                        >
                          {deliv}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {project.verification_criteria && project.verification_criteria.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="font-semibold text-slate-600 dark:text-neutral-400 flex items-center gap-1">
                      <CheckCircle2 className="h-3 w-3 text-slate-400 dark:text-neutral-500" />
                      Automated Rubric Criteria:
                    </span>
                    <div className="space-y-1">
                      {project.verification_criteria.map((crit, idx) => (
                        <div
                          key={idx}
                          className="px-2.5 py-1 rounded bg-slate-50 dark:bg-neutral-950 border border-slate-200 dark:border-neutral-800 font-mono text-[11px] text-slate-700 dark:text-neutral-300 truncate"
                        >
                          {crit}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Verification Modal */}
      {isVerificationOpen && roadmapId && (
        <VerificationModal
          roadmapId={roadmapId}
          milestone={milestone}
          isOpen={isVerificationOpen}
          onClose={() => setIsVerificationOpen(false)}
          onVerificationSuccess={onMilestoneVerified}
        />
      )}
    </div>
  );
}
