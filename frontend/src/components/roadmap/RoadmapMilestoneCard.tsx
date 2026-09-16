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
    bg: "bg-surface-subtle",
    text: "text-muted",
    border: "border-border",
    icon: Clock,
  },
  IN_PROGRESS: {
    label: "In Progress",
    bg: "bg-surface-subtle",
    text: "text-foreground",
    border: "border-border",
    icon: Clock,
  },
  COMPLETED: {
    label: "Completed",
    bg: "bg-accent/5",
    text: "text-accent",
    border: "border-accent/30",
    icon: CheckCircle2,
  },
  VERIFIED: {
    label: "Verified (AST Code)",
    bg: "bg-accent/10",
    text: "text-accent",
    border: "border-accent/40",
    icon: CheckCircle2,
  },
};

const PRIORITY_BADGES: Record<string, { bg: string; text: string; border: string }> = {
  HIGH: {
    bg: "bg-surface-subtle",
    text: "text-foreground font-bold",
    border: "border-border",
  },
  MEDIUM: {
    bg: "bg-surface-subtle",
    text: "text-muted font-medium",
    border: "border-border",
  },
  LOW: {
    bg: "bg-surface-subtle",
    text: "text-subtle",
    border: "border-border",
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

  const formattedOrder = String(milestone.order_index).padStart(2, "0");

  return (
    <div
      className={`editorial-card transition-all duration-200 overflow-hidden ${
        milestone.status === "VERIFIED"
          ? "border-accent/40"
          : milestone.status === "IN_PROGRESS"
          ? "border-foreground/30"
          : ""
      }`}
    >
      {/* Top Header Card */}
      <div className="p-5 sm:p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
          {/* Milestone Order & Title (01 ─ Name) */}
          <div className="flex items-start gap-3.5">
            <div className="h-9 w-9 rounded-md bg-surface-subtle border border-border flex items-center justify-center font-mono text-xs font-bold text-foreground shrink-0">
              {formattedOrder}
            </div>
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-base font-bold text-foreground tracking-tight">
                  {formattedOrder} ─ {milestone.skill_name}
                </h3>
                {milestone.category && (
                  <span className="text-[11px] font-mono text-muted px-2 py-0.5 rounded-sm bg-surface-subtle border border-border">
                    {milestone.category}
                  </span>
                )}
                {milestone.is_transitive_prerequisite && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-sm bg-surface-subtle text-muted border border-border">
                    Prerequisite
                  </span>
                )}
              </div>
              <p className="text-xs text-muted leading-relaxed max-w-2xl">
                {milestone.reason}
              </p>
            </div>
          </div>

          {/* Milestone Status Badge */}
          <div className="flex sm:flex-col items-center sm:items-end gap-2 shrink-0">
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm text-xs font-mono border ${statusConfig.bg} ${statusConfig.text} ${statusConfig.border}`}
            >
              <StatusIcon className="h-3.5 w-3.5 shrink-0" />
              <span>{statusConfig.label}</span>
            </span>

            {priorityConfig && (
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-sm text-[10px] font-mono uppercase tracking-wider border ${priorityConfig.bg} ${priorityConfig.text} ${priorityConfig.border}`}
              >
                {milestone.priority_level} Priority
              </span>
            )}
          </div>
        </div>

        {/* Metric Badges Strip (Large Numbers + Thin Dividers) */}
        <div className="grid grid-cols-2 sm:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-border border-y border-border py-2.5 my-2">
          {/* Priority Score */}
          <div className="p-2 text-center sm:text-left">
            <span className="text-[10px] text-muted font-mono uppercase tracking-widest block">
              Priority Score
            </span>
            <span className="text-sm font-mono font-bold text-foreground">
              {milestone.priority_score !== null && milestone.priority_score !== undefined
                ? `${Math.round(milestone.priority_score * 100)}%`
                : "--"}
            </span>
          </div>

          {/* Market Demand */}
          <div className="p-2 text-center sm:text-left">
            <span className="text-[10px] text-muted font-mono uppercase tracking-widest block">
              Industry Demand
            </span>
            <span className="text-sm font-mono font-bold text-foreground">
              {milestone.demand_score !== null && milestone.demand_score !== undefined
                ? `${Math.round(milestone.demand_score * 100)}%`
                : "--"}
            </span>
          </div>

          {/* Growth Rate */}
          <div className="p-2 text-center sm:text-left">
            <span className="text-[10px] text-muted font-mono uppercase tracking-widest block">
              Market Growth
            </span>
            <span className="text-sm font-mono font-bold text-accent">
              {milestone.growth_rate !== null && milestone.growth_rate !== undefined
                ? `+${Math.round(milestone.growth_rate * 100)}%`
                : "--"}
            </span>
          </div>

          {/* Gap Status */}
          <div className="p-2 text-center sm:text-left">
            <span className="text-[10px] text-muted font-mono uppercase tracking-widest block">
              Candidate Gap
            </span>
            <span
              className={`text-sm font-mono font-bold ${
                milestone.gap_status === "MISSING" ? "text-foreground" : "text-accent"
              }`}
            >
              {milestone.gap_status}
            </span>
          </div>
        </div>

        {/* Action Row */}
        <div className="pt-2 flex flex-wrap items-center justify-between gap-3 border-t border-border">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onViewResources(milestone.skill_id, milestone.skill_name)}
              className="editorial-btn-secondary !py-1 !px-2.5 !text-xs !rounded-md flex items-center gap-1.5 cursor-pointer font-mono"
            >
              <BookOpen className="h-3.5 w-3.5" />
              <span>Learning Resources</span>
              {milestone.resources && milestone.resources.length > 0 && (
                <span className="ml-1 px-1.5 py-0.2 rounded-sm bg-surface text-foreground border border-border text-[10px] font-mono">
                  {milestone.resources.length}
                </span>
              )}
            </button>

            {project && (
              <span className="inline-flex items-center gap-1 text-xs text-muted bg-surface-subtle px-2.5 py-1 rounded-sm border border-border">
                <Code2 className="h-3.5 w-3.5 text-accent" />
                <span className="hidden sm:inline font-mono">Project:</span>
                <strong className="text-foreground font-medium truncate max-w-[150px]">
                  {project.title}
                </strong>
              </span>
            )}

            {/* Verification Button */}
            {roadmapId && (
              <button
                type="button"
                onClick={() => setIsVerificationOpen(true)}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm text-xs font-mono border transition-all cursor-pointer ${
                  milestone.status === "VERIFIED"
                    ? "bg-accent/10 text-accent border-accent/40"
                    : "editorial-btn-secondary"
                }`}
                aria-label={`Verify milestone ${milestone.skill_name} with GitHub`}
              >
                {milestone.status === "VERIFIED" ? (
                  <>
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Verified</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="h-3.5 w-3.5" />
                    <span>Verify Code</span>
                  </>
                )}
              </button>
            )}
          </div>

          {/* Expand/Collapse Toggle */}
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="editorial-btn-secondary !py-1 !px-2.5 !text-xs !rounded-md flex items-center gap-1.5 cursor-pointer ml-auto font-mono"
            aria-expanded={isExpanded}
            aria-label={`Toggle details for milestone ${milestone.skill_name}`}
          >
            <span>{isExpanded ? "Collapse" : "Details & Projects"}</span>
            {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Expandable Details Area */}
      {isExpanded && (
        <div className="border-t border-border bg-surface-subtle p-5 sm:p-6 space-y-5 animate-in slide-in-from-top-2 duration-150">
          {/* Prerequisites Section */}
          {hasPrereqs && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-mono font-semibold text-muted uppercase tracking-wider">
                <Layers className="h-3.5 w-3.5 text-subtle" />
                <span>Prerequisites (DAG Dependencies)</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {milestone.prerequisites.map((req) => (
                  <div
                    key={req.skill_id}
                    className="p-2.5 rounded-sm bg-surface border border-border flex items-center justify-between gap-2 text-xs"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          req.is_satisfied ? "bg-accent" : "bg-muted"
                        }`}
                      />
                      <span className="text-foreground font-medium truncate">{req.skill_name}</span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0 font-mono text-[10px]">
                      <span className="px-1.5 py-0.5 rounded-sm bg-surface-subtle text-muted border border-border">
                        {req.dependency_type}
                      </span>
                      <span
                        className={`px-1.5 py-0.5 rounded-sm font-semibold border ${
                          req.is_satisfied
                            ? "bg-accent/10 text-accent border-accent/40"
                            : "bg-surface-subtle text-muted border-border"
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
              <div className="flex items-center gap-1.5 text-xs font-mono font-semibold text-muted uppercase tracking-wider">
                <Compass className="h-3.5 w-3.5 text-subtle" />
                <span>Actionable Learning Competencies</span>
              </div>
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-muted">
                {milestone.learning_objectives.map((obj, idx) => (
                  <li
                    key={idx}
                    className="p-2.5 rounded-sm bg-surface border border-border flex items-start gap-2"
                  >
                    <span className="text-accent font-mono text-xs">•</span>
                    <span className="text-foreground">{obj}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Practical Project Challenge Details */}
          {project && (
            <div className="p-4 rounded-sm bg-surface border border-border space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-2.5">
                <div className="flex items-center gap-2">
                  <div className="p-1 rounded bg-surface-subtle text-accent border border-border">
                    <Code2 className="h-4 w-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-foreground">{project.title}</h4>
                    <span className="text-[11px] text-muted font-mono">Engineering Challenge</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 font-mono text-[10px]">
                  <span className="px-2 py-0.5 rounded-sm bg-surface-subtle text-foreground border border-border uppercase font-semibold">
                    Tier: {project.difficulty}
                  </span>
                  {project.estimated_hours && (
                    <span className="text-muted">
                      ~{project.estimated_hours} hrs
                    </span>
                  )}
                </div>
              </div>

              <p className="text-xs text-muted leading-relaxed">{project.description}</p>

              {/* Deliverables & Verification Criteria */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-xs">
                {project.deliverables && project.deliverables.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="font-semibold text-muted font-mono flex items-center gap-1 text-[11px] uppercase tracking-wider">
                      <FileCheck2 className="h-3 w-3 text-subtle" />
                      Deliverables:
                    </span>
                    <div className="space-y-1">
                      {project.deliverables.map((deliv, idx) => (
                        <div
                          key={idx}
                          className="px-2.5 py-1 rounded-sm bg-surface-subtle border border-border font-mono text-[11px] text-foreground truncate"
                        >
                          {deliv}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {project.verification_criteria && project.verification_criteria.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="font-semibold text-muted font-mono flex items-center gap-1 text-[11px] uppercase tracking-wider">
                      <CheckCircle2 className="h-3 w-3 text-subtle" />
                      Verification Criteria:
                    </span>
                    <div className="space-y-1">
                      {project.verification_criteria.map((crit, idx) => (
                        <div
                          key={idx}
                          className="px-2.5 py-1 rounded-sm bg-surface-subtle border border-border font-mono text-[11px] text-foreground truncate"
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
