"use client";

import React, { useState } from "react";
import {
  RoadmapSkillItem,
  RoadmapSkillStatus,
  PracticeProblemStatus,
  updatePracticeProblemProgress,
} from "@/lib/api";
import {
  X,
  ExternalLink,
  BookOpen,
  Video,
  CheckCircle2,
  Clock,
  Circle,
  SkipForward,
  Flame,
  Code2,

  Lightbulb,
  Check,
  ChevronDown,
  ChevronUp,
  Target,
  CheckSquare,
  Sparkles,
  HelpCircle,
} from "lucide-react";

interface SkillDetailPanelProps {
  skill: RoadmapSkillItem | null;
  onClose: () => void;
  onUpdateStatus: (skillId: string, status: RoadmapSkillStatus) => Promise<void>;
  updating?: boolean;
  userId?: string;
}

export default function SkillDetailPanel({
  skill,
  onClose,
  onUpdateStatus,
  updating = false,
  userId,
}: SkillDetailPanelProps) {
  const [expandedProblemId, setExpandedProblemId] = useState<string | null>(null);
  const [problemStatuses, setProblemStatuses] = useState<Record<string, PracticeProblemStatus>>({});
  const [updatingProblemId, setUpdatingProblemId] = useState<string | null>(null);

  if (!skill) return null;

  const docResources = (skill.resources || []).filter((r) => r.resource_type === "DOCUMENTATION");
  const youtubeResources = (skill.resources || []).filter((r) => r.resource_type === "YOUTUBE");
  const practiceProblems = skill.practice_problems || [];

  const handleToggleProblem = (problemId: string) => {
    setExpandedProblemId((prev) => (prev === problemId ? null : problemId));
  };

  const handleUpdateProblemStatus = async (problemId: string, status: PracticeProblemStatus) => {
    setUpdatingProblemId(problemId);
    // Optimistic update
    setProblemStatuses((prev) => ({ ...prev, [problemId]: status }));

    try {
      await updatePracticeProblemProgress(skill.id, problemId, status, userId);
    } catch {
      // Revert if error
      setProblemStatuses((prev) => {
        const copy = { ...prev };
        delete copy[problemId];
        return copy;
      });
    } finally {
      setUpdatingProblemId(null);
    }
  };

  const completedCount = practiceProblems.filter((p) => {
    const s = problemStatuses[p.problem_id] || p.user_status;
    return s === "COMPLETED";
  }).length;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="skill-detail-title"
      className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-[#0e0e12] border-l border-neutral-800 shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-right duration-200"
    >
      {/* Header */}
      <div className="p-5 border-b border-neutral-800 flex items-start justify-between gap-4 bg-neutral-950/60 backdrop-blur-md">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono px-2 py-0.5 rounded uppercase font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20">
              {skill.difficulty}
            </span>
            {skill.priority_level === "HIGH" && (
              <span className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                <Flame className="h-3 w-3 text-amber-400 animate-pulse" />
                High Priority
              </span>
            )}
            {skill.priority_level === "MEDIUM" && (
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">
                Medium Priority
              </span>
            )}
          </div>
          <h3 id="skill-detail-title" className="text-xl font-bold text-white tracking-tight">
            {skill.name}
          </h3>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
          aria-label="Close detail panel"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Content scroll area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-neutral-800">
        {/* Status Action Buttons */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-neutral-300 uppercase tracking-wider">
            Your Learning Status
          </label>
          <div className="grid grid-cols-4 gap-2">
            <button
              disabled={updating}
              onClick={() => onUpdateStatus(skill.id, "NOT_STARTED")}
              className={`p-2.5 rounded-xl text-xs font-medium border flex flex-col items-center gap-1.5 transition-all ${
                skill.user_status === "NOT_STARTED"
                  ? "bg-neutral-800 text-white border-neutral-600 shadow-sm"
                  : "bg-neutral-900/50 text-neutral-400 border-neutral-800 hover:border-neutral-700 hover:text-neutral-200"
              }`}
            >
              <Circle className="h-3.5 w-3.5" />
              <span>Not Started</span>
            </button>

            <button
              disabled={updating}
              onClick={() => onUpdateStatus(skill.id, "LEARNING")}
              className={`p-2.5 rounded-xl text-xs font-medium border flex flex-col items-center gap-1.5 transition-all ${
                skill.user_status === "LEARNING"
                  ? "bg-amber-500/15 text-amber-300 border-amber-500/40 shadow-sm"
                  : "bg-neutral-900/50 text-neutral-400 border-neutral-800 hover:border-neutral-700 hover:text-neutral-200"
              }`}
            >
              <Clock className="h-3.5 w-3.5" />
              <span>Learning</span>
            </button>

            <button
              disabled={updating}
              onClick={() => onUpdateStatus(skill.id, "DONE")}
              className={`p-2.5 rounded-xl text-xs font-medium border flex flex-col items-center gap-1.5 transition-all ${
                skill.user_status === "DONE"
                  ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40 shadow-sm"
                  : "bg-neutral-900/50 text-neutral-400 border-neutral-800 hover:border-neutral-700 hover:text-neutral-200"
              }`}
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Done</span>
            </button>

            <button
              disabled={updating}
              onClick={() => onUpdateStatus(skill.id, "SKIPPED")}
              className={`p-2.5 rounded-xl text-xs font-medium border flex flex-col items-center gap-1.5 transition-all ${
                skill.user_status === "SKIPPED"
                  ? "bg-neutral-800/80 text-neutral-300 border-neutral-700 shadow-sm"
                  : "bg-neutral-900/50 text-neutral-400 border-neutral-800 hover:border-neutral-700 hover:text-neutral-200"
              }`}
            >
              <SkipForward className="h-3.5 w-3.5" />
              <span>Skip</span>
            </button>
          </div>
        </div>

        {/* Skill Description */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-neutral-300 uppercase tracking-wider">
            Overview
          </label>
          <p className="text-xs text-neutral-300 leading-relaxed bg-neutral-900/30 p-3.5 rounded-xl border border-neutral-800/60">
            {skill.description}
          </p>
        </div>

        {/* Key Topics */}
        {skill.key_topics && skill.key_topics.length > 0 && (
          <div className="space-y-2">
            <label className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center gap-1.5">
              <Check className="h-3.5 w-3.5 text-emerald-400" />
              <span>Key Topics & Concepts</span>
            </label>
            <ul className="space-y-2 bg-neutral-900/40 p-4 rounded-xl border border-neutral-800/80">
              {skill.key_topics.map((topic, idx) => (
                <li key={idx} className="text-xs text-neutral-300 flex items-start gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mt-1.5 flex-shrink-0" />
                  <span>{topic}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Prerequisites */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-neutral-300 uppercase tracking-wider">
            Prerequisites
          </label>
          {skill.prerequisites && skill.prerequisites.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {skill.prerequisites.map((p) => (
                <span
                  key={p.skill_id}
                  className="px-3 py-1 rounded-lg text-xs font-medium bg-neutral-900 border border-neutral-800 text-neutral-300 flex items-center gap-1.5"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-neutral-500" />
                  <span>{p.skill_name}</span>
                </span>
              ))}
            </div>
          ) : (
            <p className="text-xs text-emerald-400/90 font-medium">
              ✓ No prerequisites required — this is a foundational starting point.
            </p>
          )}
        </div>

        {/* Learning Resources */}
        <div className="space-y-3">
          <label className="text-xs font-semibold text-neutral-300 uppercase tracking-wider">
            Curated Learning Resources
          </label>

          {/* Official Documentation */}
          {docResources.length > 0 && (
            <div className="space-y-2">
              <div className="text-[11px] font-medium text-emerald-400 flex items-center gap-1.5">
                <BookOpen className="h-3.5 w-3.5" />
                <span>Official Documentation</span>
              </div>
              {docResources.map((res) => (
                <div
                  key={res.id}
                  className="p-3.5 rounded-xl bg-neutral-900/70 border border-neutral-800 flex items-start justify-between gap-3"
                >
                  <div className="space-y-1 min-w-0">
                    <h5 className="text-xs font-semibold text-white truncate">{res.title}</h5>
                    <p className="text-[11px] text-neutral-400 leading-snug">{res.description}</p>
                  </div>
                  <a
                    href={res.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 hover:text-emerald-300 transition-colors flex items-center gap-1"
                  >
                    <span>Open</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              ))}
            </div>
          )}

          {/* YouTube Video Resources */}
          {youtubeResources.length > 0 && (
            <div className="space-y-2">
              <div className="text-[11px] font-medium text-rose-400 flex items-center gap-1.5">
                <Video className="h-3.5 w-3.5" />
                <span>Video Course / Tutorial</span>
              </div>
              {youtubeResources.map((res) => (
                <div
                  key={res.id}
                  className="p-3.5 rounded-xl bg-neutral-900/70 border border-neutral-800 flex items-start justify-between gap-3"
                >
                  <div className="space-y-1 min-w-0">
                    <h5 className="text-xs font-semibold text-white truncate">{res.title}</h5>
                    <p className="text-[11px] text-neutral-400 leading-snug">{res.description}</p>
                  </div>
                  <a
                    href={res.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 hover:text-rose-300 transition-colors flex items-center gap-1"
                  >
                    <span>Watch</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* PRACTICE PROBLEMS SECTION */}
        {practiceProblems.length > 0 && (
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
              <label className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                <Code2 className="h-4 w-4 text-indigo-400" />
                <span>PRACTICE</span>
              </label>
              <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                {completedCount} / {practiceProblems.length} Completed
              </span>
            </div>

            <p className="text-[11px] text-neutral-400">
              Master this skill through three progressive challenges: Foundation, Integration, and Applied Mastery.
            </p>

            <div className="space-y-3">
              {practiceProblems.map((prob, idx) => {
                const stageLabel =
                  idx === 0
                    ? "01 — Foundation"
                    : idx === 1
                    ? "02 — Integration"
                    : idx === 2
                    ? "03 — Mastery"
                    : `0${idx + 1} — Advanced`;

                const isExpanded = expandedProblemId === prob.problem_id;
                const currentStatus =
                  problemStatuses[prob.problem_id] || prob.user_status || "NOT_STARTED";
                const isUpdating = updatingProblemId === prob.problem_id;

                return (
                  <div
                    key={prob.problem_id}
                    className={`rounded-xl border transition-all duration-200 overflow-hidden ${
                      isExpanded
                        ? "bg-neutral-900/90 border-indigo-500/40 shadow-lg shadow-indigo-950/20"
                        : "bg-neutral-900/40 border-neutral-800/80 hover:border-neutral-700"
                    }`}
                  >
                    {/* Problem Header Card */}
                    <div className="p-4 flex items-start justify-between gap-3">
                      <div className="space-y-1 min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[10px] font-mono font-semibold uppercase text-indigo-400">
                            {stageLabel}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded font-medium bg-neutral-800 text-neutral-300">
                            {prob.difficulty}
                          </span>
                          {currentStatus === "COMPLETED" && (
                            <span className="flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                              <CheckCircle2 className="h-3 w-3" />
                              Completed
                            </span>
                          )}
                          {currentStatus === "IN_PROGRESS" && (
                            <span className="flex items-center gap-1 text-[10px] font-medium text-amber-300 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                              <Clock className="h-3 w-3" />
                              In Progress
                            </span>
                          )}
                        </div>
                        <h4 className="text-xs font-semibold text-white leading-snug">
                          {prob.title}
                        </h4>
                      </div>

                      <button
                        onClick={() => handleToggleProblem(prob.problem_id)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 flex-shrink-0 ${
                          isExpanded
                            ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/40"
                            : "bg-neutral-800 text-neutral-200 border-neutral-700 hover:bg-neutral-750 hover:text-white"
                        }`}
                      >
                        <span>{isExpanded ? "Hide Details" : "Open Problem"}</span>
                        {isExpanded ? (
                          <ChevronUp className="h-3.5 w-3.5" />
                        ) : (
                          <ChevronDown className="h-3.5 w-3.5" />
                        )}
                      </button>
                    </div>

                    {/* Expandable Problem Details Body */}
                    {isExpanded && (
                      <div className="px-4 pb-4 pt-1 border-t border-neutral-800/80 space-y-4 text-xs">
                        {/* Objective */}
                        <div className="space-y-1.5">
                          <span className="text-[10px] font-semibold text-indigo-300 uppercase tracking-wider flex items-center gap-1">
                            <Target className="h-3 w-3 text-indigo-400" />
                            Objective
                          </span>
                          <div className="p-3 rounded-lg bg-indigo-950/20 border border-indigo-900/30 text-neutral-200 leading-relaxed">
                            {prob.objective}
                          </div>
                        </div>

                        {/* Problem Statement */}
                        <div className="space-y-1.5">
                          <span className="text-[10px] font-semibold text-neutral-300 uppercase tracking-wider flex items-center gap-1">
                            <HelpCircle className="h-3 w-3 text-neutral-400" />
                            Problem Statement
                          </span>
                          <p className="text-neutral-300 leading-relaxed">
                            {prob.problem_statement}
                          </p>
                        </div>

                        {/* Requirements */}
                        {prob.requirements && prob.requirements.length > 0 && (
                          <div className="space-y-1.5">
                            <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
                              <CheckSquare className="h-3 w-3" />
                              Specific Requirements
                            </span>
                            <ul className="space-y-1.5 bg-neutral-950/50 p-3 rounded-lg border border-neutral-800/80">
                              {prob.requirements.map((req, rIdx) => (
                                <li key={rIdx} className="text-neutral-300 flex items-start gap-2">
                                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mt-1.5 flex-shrink-0" />
                                  <span className="leading-snug">{req}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Concepts Tested */}
                        {prob.concepts_tested && prob.concepts_tested.length > 0 && (
                          <div className="space-y-1.5">
                            <span className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider flex items-center gap-1">
                              <Sparkles className="h-3 w-3 text-amber-400" />
                              Concepts Being Tested
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {prob.concepts_tested.map((concept, cIdx) => (
                                <span
                                  key={cIdx}
                                  className="px-2 py-0.5 rounded text-[11px] bg-neutral-800/80 border border-neutral-700/60 text-neutral-300 font-mono"
                                >
                                  {concept}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Expected Outcome */}
                        <div className="space-y-1.5">
                          <span className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">
                            Expected Outcome
                          </span>
                          <p className="text-neutral-300 leading-relaxed bg-neutral-950/40 p-2.5 rounded border border-neutral-800/60">
                            {prob.expected_outcome}
                          </p>
                        </div>

                        {/* Optional Hints */}
                        {prob.optional_hints && prob.optional_hints.length > 0 && (
                          <div className="space-y-1.5">
                            <span className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-1">
                              <Lightbulb className="h-3 w-3" />
                              Helpful Hints
                            </span>
                            <ul className="space-y-1 bg-amber-950/15 p-2.5 rounded border border-amber-900/30">
                              {prob.optional_hints.map((hint, hIdx) => (
                                <li key={hIdx} className="text-neutral-300 text-[11px] leading-relaxed">
                                  💡 {hint}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Problem Progress Action Bar */}
                        <div className="pt-2 border-t border-neutral-800 flex items-center justify-between gap-2 flex-wrap">
                          <span className="text-[11px] font-medium text-neutral-400">
                            Challenge Status:
                          </span>
                          <div className="flex items-center gap-1.5">
                            <button
                              disabled={isUpdating}
                              onClick={() => handleUpdateProblemStatus(prob.problem_id, "NOT_STARTED")}
                              className={`px-2.5 py-1 rounded text-xs border font-medium transition-all ${
                                currentStatus === "NOT_STARTED"
                                  ? "bg-neutral-800 text-white border-neutral-600"
                                  : "bg-neutral-900 text-neutral-400 border-neutral-800 hover:text-neutral-200"
                              }`}
                            >
                              Not Started
                            </button>
                            <button
                              disabled={isUpdating}
                              onClick={() => handleUpdateProblemStatus(prob.problem_id, "IN_PROGRESS")}
                              className={`px-2.5 py-1 rounded text-xs border font-medium transition-all ${
                                currentStatus === "IN_PROGRESS"
                                  ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                                  : "bg-neutral-900 text-neutral-400 border-neutral-800 hover:text-amber-300"
                              }`}
                            >
                              In Progress
                            </button>
                            <button
                              disabled={isUpdating}
                              onClick={() => handleUpdateProblemStatus(prob.problem_id, "COMPLETED")}
                              className={`px-2.5 py-1 rounded text-xs border font-medium transition-all ${
                                currentStatus === "COMPLETED"
                                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                                  : "bg-neutral-900 text-neutral-400 border-neutral-800 hover:text-emerald-300"
                              }`}
                            >
                              Completed ✓
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Why This Matters */}
        {skill.role_relevance && (
          <div className="space-y-2 pt-2">
            <label className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center gap-1.5">
              <Lightbulb className="h-3.5 w-3.5 text-amber-400" />
              <span>Why This Matters for Your Target Role</span>
            </label>
            <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-900/40 text-xs text-neutral-300 leading-relaxed">
              {skill.role_relevance}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-neutral-800 bg-neutral-950 flex items-center justify-between text-xs text-neutral-500">
        <span>SkillForge Evidence-Aware Learning Path</span>
        <button
          onClick={onClose}
          className="px-4 py-1.5 rounded-lg bg-neutral-800 text-neutral-200 hover:bg-neutral-700 transition-colors font-medium"
        >
          Done
        </button>
      </div>
    </div>
  );
}
