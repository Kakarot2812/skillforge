"use client";

import React, { useState, useEffect } from "react";
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
  Code2,
  Lightbulb,
  Check,
  ChevronDown,
  ChevronUp,
  Target,
  CheckSquare,
  Sparkles,
  HelpCircle,
  ShieldCheck,
  Briefcase,
  FolderGit2,
  Lock,
} from "lucide-react";

interface SkillDetailPanelProps {
  skill: RoadmapSkillItem | null;
  onClose: () => void;
  onUpdateStatus: (skillId: string, status: RoadmapSkillStatus) => Promise<void>;
  updating?: boolean;
  userId?: string;
  allSkillStatuses?: Record<string, string>;
}

export default function SkillDetailPanel({
  skill,
  onClose,
  onUpdateStatus,
  updating = false,
  userId,
  allSkillStatuses = {},
}: SkillDetailPanelProps) {
  const [expandedProblemId, setExpandedProblemId] = useState<string | null>(null);
  const [problemStatuses, setProblemStatuses] = useState<Record<string, PracticeProblemStatus>>({});
  const [updatingProblemId, setUpdatingProblemId] = useState<string | null>(null);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!skill) return null;

  const docResources = (skill.resources || []).filter((r) => r.resource_type === "DOCUMENTATION");
  const youtubeResources = (skill.resources || []).filter((r) => r.resource_type === "YOUTUBE");
  const practiceProblems = skill.practice_problems || [];

  const handleToggleProblem = (problemId: string) => {
    setExpandedProblemId((prev) => (prev === problemId ? null : problemId));
  };

  const handleUpdateProblemStatus = async (problemId: string, newStatus: PracticeProblemStatus) => {
    setUpdatingProblemId(problemId);
    // Optimistic local update
    setProblemStatuses((prev) => ({ ...prev, [problemId]: newStatus }));

    try {
      const res = await updatePracticeProblemProgress(skill.id, problemId, newStatus, userId);
      if (!res.success) {
        // Revert on failure
        setProblemStatuses((prev) => {
          const copy = { ...prev };
          delete copy[problemId];
          return copy;
        });
      }
    } catch {
      // Revert on error
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

  const currentSkillStatus = skill.user_status || "NOT_STARTED";

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-slate-900/40 dark:bg-black/60 backdrop-blur-xs transition-opacity animate-in fade-in"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-over Drawer */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="skill-detail-title"
        className="fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-white dark:bg-neutral-950 border-l border-slate-200 dark:border-neutral-800 shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-right duration-200"
      >
        {/* Header */}
        <div className="p-5 border-b border-slate-200 dark:border-neutral-800 flex items-start justify-between gap-4 bg-slate-50/80 dark:bg-neutral-900/60 backdrop-blur-md">
          <div className="space-y-1.5 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded uppercase font-semibold text-emerald-700 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20">
                {skill.difficulty}
              </span>
              {skill.canonical_skill_id && (
                <span className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-500/20">
                  <ShieldCheck className="h-3 w-3" />
                  Canonical Skill
                </span>
              )}
            </div>
            <h3 id="skill-detail-title" className="text-xl font-bold text-slate-900 dark:text-white tracking-tight truncate">
              {skill.name}
            </h3>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 dark:text-neutral-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
            aria-label="Close detail panel"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Content Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-neutral-800">
          {/* Status Action Buttons */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-700 dark:text-neutral-300 uppercase tracking-wider">
              Your Learning Status
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <button
                type="button"
                disabled={updating}
                onClick={() => onUpdateStatus(skill.id, "NOT_STARTED")}
                className={`p-2.5 rounded-xl text-xs font-medium border flex flex-col items-center gap-1.5 transition-all cursor-pointer ${
                  currentSkillStatus === "NOT_STARTED"
                    ? "bg-slate-900 dark:bg-neutral-800 text-white border-slate-900 dark:border-neutral-600 shadow-sm"
                    : "bg-slate-50 dark:bg-neutral-900/50 text-slate-600 dark:text-neutral-400 border-slate-200 dark:border-neutral-800 hover:border-slate-300 dark:hover:border-neutral-700 hover:text-slate-900 dark:hover:text-neutral-200"
                }`}
              >
                <Circle className="h-4 w-4" />
                <span>Not Started</span>
              </button>

              <button
                type="button"
                disabled={updating}
                onClick={() => onUpdateStatus(skill.id, "LEARNING")}
                className={`p-2.5 rounded-xl text-xs font-medium border flex flex-col items-center gap-1.5 transition-all cursor-pointer ${
                  currentSkillStatus === "LEARNING"
                    ? "bg-sky-50 dark:bg-sky-500/15 text-sky-800 dark:text-sky-300 border-sky-400 dark:border-sky-500/40 shadow-sm font-semibold"
                    : "bg-slate-50 dark:bg-neutral-900/50 text-slate-600 dark:text-neutral-400 border-slate-200 dark:border-neutral-800 hover:border-slate-300 dark:hover:border-neutral-700 hover:text-slate-900 dark:hover:text-neutral-200"
                }`}
              >
                <Clock className="h-4 w-4" />
                <span>Learning</span>
              </button>

              <button
                type="button"
                disabled={updating}
                onClick={() => onUpdateStatus(skill.id, "DONE")}
                className={`p-2.5 rounded-xl text-xs font-medium border flex flex-col items-center gap-1.5 transition-all cursor-pointer ${
                  currentSkillStatus === "DONE"
                    ? "bg-emerald-50 dark:bg-emerald-500/15 text-emerald-800 dark:text-emerald-300 border-emerald-400 dark:border-emerald-500/40 shadow-sm font-semibold"
                    : "bg-slate-50 dark:bg-neutral-900/50 text-slate-600 dark:text-neutral-400 border-slate-200 dark:border-neutral-800 hover:border-slate-300 dark:hover:border-neutral-700 hover:text-slate-900 dark:hover:text-neutral-200"
                }`}
              >
                <CheckCircle2 className="h-4 w-4" />
                <span>Done</span>
              </button>

              <button
                type="button"
                disabled={updating}
                onClick={() => onUpdateStatus(skill.id, "SKIPPED")}
                className={`p-2.5 rounded-xl text-xs font-medium border flex flex-col items-center gap-1.5 transition-all cursor-pointer ${
                  currentSkillStatus === "SKIPPED"
                    ? "bg-slate-200 dark:bg-neutral-800/80 text-slate-800 dark:text-neutral-300 border-slate-400 dark:border-neutral-700 shadow-sm font-semibold"
                    : "bg-slate-50 dark:bg-neutral-900/50 text-slate-600 dark:text-neutral-400 border-slate-200 dark:border-neutral-800 hover:border-slate-300 dark:hover:border-neutral-700 hover:text-slate-900 dark:hover:text-neutral-200"
                }`}
              >
                <SkipForward className="h-4 w-4" />
                <span>Skip</span>
              </button>
            </div>
          </div>

          {/* Overview Description */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-700 dark:text-neutral-300 uppercase tracking-wider">
              Overview
            </label>
            <p className="text-xs text-slate-700 dark:text-neutral-300 leading-relaxed bg-slate-50 dark:bg-neutral-900/40 p-4 rounded-xl border border-slate-200 dark:border-neutral-800/60">
              {skill.description}
            </p>
          </div>

          {/* Key Topics & Concepts */}
          {skill.key_topics && skill.key_topics.length > 0 && (
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-700 dark:text-neutral-300 uppercase tracking-wider flex items-center gap-1.5">
                <Check className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                <span>Key Topics & Concepts</span>
              </label>
              <ul className="space-y-2 bg-slate-50 dark:bg-neutral-900/40 p-4 rounded-xl border border-slate-200 dark:border-neutral-800/80">
                {skill.key_topics.map((topic, idx) => (
                  <li key={idx} className="text-xs text-slate-700 dark:text-neutral-300 flex items-start gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 mt-1.5 flex-shrink-0" />
                    <span>{topic}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Prerequisites */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-700 dark:text-neutral-300 uppercase tracking-wider flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-slate-400" />
              <span>Prerequisites</span>
            </label>
            {skill.prerequisites && skill.prerequisites.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {skill.prerequisites.map((p) => {
                  const pStatus = allSkillStatuses[p.skill_id] || allSkillStatuses[p.skill_slug];
                  const isDone = pStatus === "DONE";

                  return (
                    <span
                      key={p.skill_id}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium border flex items-center gap-1.5 ${
                        isDone
                          ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/30"
                          : "bg-slate-50 dark:bg-neutral-900 border-slate-200 dark:border-neutral-800 text-slate-700 dark:text-neutral-300"
                      }`}
                    >
                      {isDone ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                      ) : (
                        <span className="h-2 w-2 rounded-full bg-slate-400 dark:bg-neutral-600" />
                      )}
                      <span>{p.skill_name}</span>
                      <span className="text-[10px] font-mono text-slate-400 dark:text-neutral-500">
                        ({p.difficulty})
                      </span>
                    </span>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-emerald-700 dark:text-emerald-400 font-medium bg-emerald-50 dark:bg-emerald-500/10 p-3 rounded-xl border border-emerald-200 dark:border-emerald-500/20">
                ✓ No prerequisites required — foundational skill track.
              </p>
            )}
          </div>

          {/* Role Relevance */}
          {skill.role_relevance && (
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-700 dark:text-neutral-300 uppercase tracking-wider flex items-center gap-1.5">
                <Briefcase className="h-3.5 w-3.5 text-amber-500" />
                <span>Role Relevance</span>
              </label>
              <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/40 text-xs text-slate-700 dark:text-neutral-300 leading-relaxed">
                {skill.role_relevance}
              </div>
            </div>
          )}

          {/* Practice Project */}
          {skill.practice_project && (
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-700 dark:text-neutral-300 uppercase tracking-wider flex items-center gap-1.5">
                <FolderGit2 className="h-3.5 w-3.5 text-purple-500" />
                <span>Capstone Practice Project</span>
              </label>
              <div className="p-3.5 rounded-xl bg-purple-50 dark:bg-purple-950/20 border border-purple-200 dark:border-purple-900/40 text-xs text-slate-700 dark:text-neutral-300 leading-relaxed font-mono">
                {skill.practice_project}
              </div>
            </div>
          )}

          {/* Curated Learning Resources */}
          <div className="space-y-3">
            <label className="text-xs font-bold text-slate-700 dark:text-neutral-300 uppercase tracking-wider">
              Curated Learning Resources
            </label>

            {/* Official Documentation */}
            {docResources.length > 0 && (
              <div className="space-y-2">
                <div className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-400 flex items-center gap-1.5">
                  <BookOpen className="h-3.5 w-3.5" />
                  <span>Official Documentation</span>
                </div>
                {docResources.map((res) => (
                  <div
                    key={res.id}
                    className="p-3.5 rounded-xl bg-slate-50 dark:bg-neutral-900/70 border border-slate-200 dark:border-neutral-800 flex items-start justify-between gap-3"
                  >
                    <div className="space-y-1 min-w-0">
                      <h5 className="text-xs font-semibold text-slate-900 dark:text-white truncate">{res.title}</h5>
                      <p className="text-[11px] text-slate-600 dark:text-neutral-400 leading-snug">{res.description}</p>
                    </div>
                    <a
                      href={res.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-100 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20 hover:bg-emerald-200 dark:hover:bg-emerald-500/20 transition-colors flex items-center gap-1"
                    >
                      <span>Read</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                ))}
              </div>
            )}

            {/* YouTube Video Resources */}
            {youtubeResources.length > 0 && (
              <div className="space-y-2">
                <div className="text-[11px] font-semibold text-rose-700 dark:text-rose-400 flex items-center gap-1.5">
                  <Video className="h-3.5 w-3.5" />
                  <span>Video Tutorials / Deep Dives</span>
                </div>
                {youtubeResources.map((res) => (
                  <div
                    key={res.id}
                    className="p-3.5 rounded-xl bg-slate-50 dark:bg-neutral-900/70 border border-slate-200 dark:border-neutral-800 flex items-start justify-between gap-3"
                  >
                    <div className="space-y-1 min-w-0">
                      <h5 className="text-xs font-semibold text-slate-900 dark:text-white truncate">{res.title}</h5>
                      <p className="text-[11px] text-slate-600 dark:text-neutral-400 leading-snug">{res.description}</p>
                    </div>
                    <a
                      href={res.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-100 dark:bg-rose-500/10 text-rose-800 dark:text-rose-400 border border-rose-200 dark:border-rose-500/20 hover:bg-rose-200 dark:hover:bg-rose-500/20 transition-colors flex items-center gap-1"
                    >
                      <span>Watch</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Progressive Practice Problems */}
          {practiceProblems.length > 0 && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-neutral-800 pb-2">
                <label className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
                  <Code2 className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                  <span>Progressive Practice Challenges</span>
                </label>
                <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20">
                  {completedCount} / {practiceProblems.length} Solved
                </span>
              </div>

              <p className="text-[11px] text-slate-500 dark:text-neutral-400">
                Master this skill through three progressive challenges: Foundation, Integration, and Applied Mastery.
              </p>

              <div className="space-y-3">
                {practiceProblems.map((prob, idx) => {
                  const stageLabel =
                    idx === 0
                      ? "01 — Foundation"
                      : idx === 1
                      ? "02 — Integration"
                      : "03 — Mastery";

                  const isExpanded = expandedProblemId === prob.problem_id;
                  const currentProblemStatus =
                    problemStatuses[prob.problem_id] || prob.user_status || "NOT_STARTED";
                  const isUpdatingThis = updatingProblemId === prob.problem_id;

                  return (
                    <div
                      key={prob.problem_id}
                      className={`rounded-xl border transition-all duration-200 overflow-hidden ${
                        isExpanded
                          ? "bg-slate-50 dark:bg-neutral-900/90 border-indigo-300 dark:border-indigo-500/40 shadow-md dark:shadow-indigo-950/20"
                          : "bg-white dark:bg-neutral-900/40 border-slate-200 dark:border-neutral-800/80 hover:border-slate-300 dark:hover:border-neutral-700"
                      }`}
                    >
                      {/* Problem Card Header */}
                      <div className="p-4 flex items-start justify-between gap-3">
                        <div className="space-y-1 min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[10px] font-mono font-bold uppercase text-indigo-600 dark:text-indigo-400">
                              {stageLabel}
                            </span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded font-mono font-medium bg-slate-100 dark:bg-neutral-800 text-slate-700 dark:text-neutral-300 border border-slate-200 dark:border-neutral-700">
                              {prob.difficulty}
                            </span>
                            {currentProblemStatus === "COMPLETED" && (
                              <span className="flex items-center gap-1 text-[10px] font-semibold text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-200 dark:border-emerald-500/20">
                                <CheckCircle2 className="h-3 w-3" />
                                Completed
                              </span>
                            )}
                            {currentProblemStatus === "IN_PROGRESS" && (
                              <span className="flex items-center gap-1 text-[10px] font-semibold text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-200 dark:border-amber-500/20">
                                <Clock className="h-3 w-3" />
                                In Progress
                              </span>
                            )}
                          </div>
                          <h4 className="text-xs font-bold text-slate-900 dark:text-white leading-snug">
                            {prob.title}
                          </h4>
                        </div>

                        <button
                          type="button"
                          onClick={() => handleToggleProblem(prob.problem_id)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 flex-shrink-0 cursor-pointer ${
                            isExpanded
                              ? "bg-indigo-100 dark:bg-indigo-500/20 text-indigo-800 dark:text-indigo-300 border-indigo-300 dark:border-indigo-500/40"
                              : "bg-slate-100 dark:bg-neutral-800 text-slate-700 dark:text-neutral-200 border-slate-200 dark:border-neutral-700 hover:bg-slate-200 dark:hover:bg-neutral-750"
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
                        <div className="px-4 pb-4 pt-1 border-t border-slate-200 dark:border-neutral-800/80 space-y-4 text-xs">
                          {/* Objective */}
                          <div className="space-y-1.5">
                            <span className="text-[10px] font-bold text-indigo-700 dark:text-indigo-300 uppercase tracking-wider flex items-center gap-1">
                              <Target className="h-3 w-3 text-indigo-500" />
                              Objective
                            </span>
                            <div className="p-3 rounded-lg bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-200 dark:border-indigo-900/30 text-slate-800 dark:text-neutral-200 leading-relaxed">
                              {prob.objective}
                            </div>
                          </div>

                          {/* Problem Statement */}
                          <div className="space-y-1.5">
                            <span className="text-[10px] font-bold text-slate-700 dark:text-neutral-300 uppercase tracking-wider flex items-center gap-1">
                              <HelpCircle className="h-3 w-3 text-slate-400" />
                              Problem Statement
                            </span>
                            <p className="text-slate-700 dark:text-neutral-300 leading-relaxed">
                              {prob.problem_statement}
                            </p>
                          </div>

                          {/* Specific Requirements */}
                          {prob.requirements && prob.requirements.length > 0 && (
                            <div className="space-y-1.5">
                              <span className="text-[10px] font-bold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider flex items-center gap-1">
                                <CheckSquare className="h-3 w-3" />
                                Requirements
                              </span>
                              <ul className="space-y-1.5 bg-white dark:bg-neutral-950/50 p-3 rounded-lg border border-slate-200 dark:border-neutral-800/80">
                                {prob.requirements.map((req, rIdx) => (
                                  <li key={rIdx} className="text-slate-700 dark:text-neutral-300 flex items-start gap-2">
                                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 mt-1.5 flex-shrink-0" />
                                    <span className="leading-snug">{req}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Concepts Tested */}
                          {prob.concepts_tested && prob.concepts_tested.length > 0 && (
                            <div className="space-y-1.5">
                              <span className="text-[10px] font-bold text-slate-700 dark:text-neutral-400 uppercase tracking-wider flex items-center gap-1">
                                <Sparkles className="h-3 w-3 text-amber-500" />
                                Concepts Tested
                              </span>
                              <div className="flex flex-wrap gap-1.5">
                                {prob.concepts_tested.map((concept, cIdx) => (
                                  <span
                                    key={cIdx}
                                    className="px-2 py-0.5 rounded text-[11px] bg-slate-100 dark:bg-neutral-800/80 border border-slate-200 dark:border-neutral-700/60 text-slate-700 dark:text-neutral-300 font-mono"
                                  >
                                    {concept}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Expected Outcome */}
                          <div className="space-y-1.5">
                            <span className="text-[10px] font-bold text-slate-700 dark:text-neutral-400 uppercase tracking-wider">
                              Expected Outcome
                            </span>
                            <p className="text-slate-700 dark:text-neutral-300 leading-relaxed bg-white dark:bg-neutral-950/40 p-2.5 rounded border border-slate-200 dark:border-neutral-800/60">
                              {prob.expected_outcome}
                            </p>
                          </div>

                          {/* Hints */}
                          {prob.optional_hints && prob.optional_hints.length > 0 && (
                            <div className="space-y-1.5">
                              <span className="text-[10px] font-bold text-amber-700 dark:text-amber-400 uppercase tracking-wider flex items-center gap-1">
                                <Lightbulb className="h-3 w-3" />
                                Hints & Guidance
                              </span>
                              <ul className="space-y-1 bg-amber-50 dark:bg-amber-950/15 p-2.5 rounded border border-amber-200 dark:border-amber-900/30">
                                {prob.optional_hints.map((hint, hIdx) => (
                                  <li key={hIdx} className="text-slate-700 dark:text-neutral-300 text-[11px] leading-relaxed">
                                    💡 {hint}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Challenge Status Action Bar */}
                          <div className="pt-2 border-t border-slate-200 dark:border-neutral-800 flex items-center justify-between gap-2 flex-wrap">
                            <span className="text-[11px] font-semibold text-slate-600 dark:text-neutral-400">
                              Status:
                            </span>
                            <div className="flex items-center gap-1.5">
                              <button
                                type="button"
                                disabled={isUpdatingThis}
                                onClick={() => handleUpdateProblemStatus(prob.problem_id, "NOT_STARTED")}
                                className={`px-2.5 py-1 rounded text-xs border font-medium transition-all cursor-pointer ${
                                  currentProblemStatus === "NOT_STARTED"
                                    ? "bg-slate-900 dark:bg-neutral-800 text-white border-slate-900 dark:border-neutral-600"
                                    : "bg-slate-100 dark:bg-neutral-900 text-slate-600 dark:text-neutral-400 border-slate-200 dark:border-neutral-800 hover:text-slate-900 dark:hover:text-neutral-200"
                                }`}
                              >
                                Not Started
                              </button>
                              <button
                                type="button"
                                disabled={isUpdatingThis}
                                onClick={() => handleUpdateProblemStatus(prob.problem_id, "IN_PROGRESS")}
                                className={`px-2.5 py-1 rounded text-xs border font-medium transition-all cursor-pointer ${
                                  currentProblemStatus === "IN_PROGRESS"
                                    ? "bg-amber-100 dark:bg-amber-500/20 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-500/40"
                                    : "bg-slate-100 dark:bg-neutral-900 text-slate-600 dark:text-neutral-400 border-slate-200 dark:border-neutral-800 hover:text-amber-700 dark:hover:text-amber-300"
                                }`}
                              >
                                In Progress
                              </button>
                              <button
                                type="button"
                                disabled={isUpdatingThis}
                                onClick={() => handleUpdateProblemStatus(prob.problem_id, "COMPLETED")}
                                className={`px-2.5 py-1 rounded text-xs border font-medium transition-all cursor-pointer ${
                                  currentProblemStatus === "COMPLETED"
                                    ? "bg-emerald-100 dark:bg-emerald-500/20 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/40"
                                    : "bg-slate-100 dark:bg-neutral-900 text-slate-600 dark:text-neutral-400 border-slate-200 dark:border-neutral-800 hover:text-emerald-700 dark:hover:text-emerald-300"
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
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 dark:border-neutral-800 bg-slate-50 dark:bg-neutral-950 flex items-center justify-between text-xs text-slate-500 dark:text-neutral-500">
          <span>SkillForge Static Roadmap</span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-900 dark:bg-neutral-800 text-white dark:text-neutral-200 hover:bg-slate-800 dark:hover:bg-neutral-700 transition-colors font-medium cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </>
  );
}
