"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  RoadmapListItem,
  RoadmapDetailData,
  RoadmapSkillItem,
  RoadmapSkillStatus,
  RoadmapOrdering,
  fetchRoadmapsCatalog,
  fetchRoadmapDetail,
  updateSkillProgress,
} from "@/lib/api";
import { getCandidateUserId, ensureCandidateIdentity } from "@/lib/identity";
import RoadmapRoleSelector from "./RoadmapRoleSelector";
import RoadmapProgress from "./RoadmapProgress";
import RoadmapStage from "./RoadmapStage";
import RoadmapSkillCard from "./RoadmapSkillCard";
import SkillDetailPanel from "./SkillDetailPanel";
import { Sparkles, Map, AlertCircle, RefreshCw, X, BookOpen, Layers } from "lucide-react";

export interface SkillRoadmapProps {
  targetRoleId?: string;
  userId?: string;
  initialRoadmapId?: string;
}

export default function SkillRoadmap({
  targetRoleId,
  userId: controlledUserId,
  initialRoadmapId,
}: SkillRoadmapProps) {
  const [roadmaps, setRoadmaps] = useState<RoadmapListItem[]>([]);
  const [selectedRoadmapId, setSelectedRoadmapId] = useState<string>("");
  const [roadmapDetail, setRoadmapDetail] = useState<RoadmapDetailData | null>(null);
  const [ordering, setOrdering] = useState<RoadmapOrdering>("curated");
  const [selectedSkill, setSelectedSkill] = useState<RoadmapSkillItem | null>(null);

  const [loadingCatalog, setLoadingCatalog] = useState<boolean>(true);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);
  const [updatingStatus, setUpdatingStatus] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [candidateUserId, setCandidateUserId] = useState<string | undefined>(() => {
    if (typeof window !== "undefined") {
      return getCandidateUserId() || undefined;
    }
    return undefined;
  });

  const effectiveUserId = controlledUserId || candidateUserId;

  // Initialize candidate identity if not already present
  useEffect(() => {
    if (effectiveUserId) return;
    if (typeof window !== "undefined") {
      ensureCandidateIdentity().then((id) => {
        if (id) setCandidateUserId(id);
      });
    }
  }, [effectiveUserId]);

  // 1. Fetch Catalog on Mount
  useEffect(() => {
    let isCancelled = false;

    async function loadCatalog() {
      setLoadingCatalog(true);
      setError(null);

      const res = await fetchRoadmapsCatalog();
      if (isCancelled) return;

      if (res.success && res.data && res.data.length > 0) {
        setRoadmaps(res.data);

        // Select initial roadmap
        let chosen = res.data[0];
        if (initialRoadmapId) {
          const matchInitial = res.data.find(
            (r) => r.id === initialRoadmapId || r.slug === initialRoadmapId
          );
          if (matchInitial) chosen = matchInitial;
        } else if (targetRoleId) {
          const matchRole = res.data.find((r) => r.role_id === targetRoleId);
          if (matchRole) chosen = matchRole;
        }

        setSelectedRoadmapId(chosen.id);
      } else {
        setError(res.error || "Failed to load roadmaps catalog.");
      }
      setLoadingCatalog(false);
    }

    loadCatalog();
    return () => {
      isCancelled = true;
    };
  }, [targetRoleId, initialRoadmapId]);

  // 2. Fetch Roadmap Detail when selectedRoadmapId, ordering, or identity changes
  const loadDetail = useCallback(
    async (roadmapId: string, currentOrdering: RoadmapOrdering) => {
      if (!roadmapId) return;
      setLoadingDetail(true);
      setError(null);

      const res = await fetchRoadmapDetail(roadmapId, currentOrdering, effectiveUserId);

      if (res.success && res.data) {
        setRoadmapDetail(res.data);
      } else {
        setError(res.error || "Failed to load roadmap details.");
      }
      setLoadingDetail(false);
    },
    [effectiveUserId]
  );

  useEffect(() => {
    if (!selectedRoadmapId) return;
    let ignore = false;

    async function runFetch() {
      setLoadingDetail(true);
      setError(null);

      const res = await fetchRoadmapDetail(selectedRoadmapId, ordering, effectiveUserId);
      if (ignore) return;

      if (res.success && res.data) {
        setRoadmapDetail(res.data);
      } else {
        setError(res.error || "Failed to load roadmap details.");
      }
      setLoadingDetail(false);
    }

    runFetch();
    return () => {
      ignore = true;
    };
  }, [selectedRoadmapId, ordering, effectiveUserId]);

  // Handle roadmap selection
  const handleSelectRoadmap = (newRoadmapId: string) => {
    if (newRoadmapId === selectedRoadmapId) return;
    setSelectedRoadmapId(newRoadmapId);
    setSelectedSkill(null);
  };

  // Handle ordering mode toggle
  const handleToggleOrdering = (newOrdering: RoadmapOrdering) => {
    setOrdering(newOrdering);
  };

  // Compute a flat map of all skill statuses for prerequisite lookup
  const allSkillStatuses = useMemo<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    if (!roadmapDetail) return map;

    for (const stage of roadmapDetail.stages) {
      for (const sk of stage.skills) {
        map[sk.id] = sk.user_status || "NOT_STARTED";
        map[sk.slug] = sk.user_status || "NOT_STARTED";
      }
    }
    return map;
  }, [roadmapDetail]);

  // Compute practice problem counts across the entire roadmap
  const practiceCounts = useMemo<{ total: number; completed: number }>(() => {
    if (!roadmapDetail) return { total: 0, completed: 0 };
    let total = 0;
    let completed = 0;

    for (const stage of roadmapDetail.stages) {
      for (const sk of stage.skills) {
        for (const prob of sk.practice_problems || []) {
          total += 1;
          if (prob.user_status === "COMPLETED") completed += 1;
        }
      }
    }
    return { total, completed };
  }, [roadmapDetail]);

/**
 * Authoritatively reconciles a skill's user_status across roadmap stages,
 * recommended skills, and derives exact stage done counts and summary progress.
 *
 * Invariants:
 * - 0 <= stage.completed_skills <= stage.total_skills
 * - Stage completion percentage never exceeds 100%
 * - Roadmap summary counts are strictly aggregated from all stage skills
 */
function reconcileRoadmapSkillStatus(
  detail: RoadmapDetailData,
  skillId: string,
  newStatus: RoadmapSkillStatus
): RoadmapDetailData {
  const updateSkill = (s: RoadmapSkillItem): RoadmapSkillItem =>
    s.id === skillId ? { ...s, user_status: newStatus } : s;

  const updatedStages = detail.stages.map((st) => {
    const hasSkill = st.skills.some((s) => s.id === skillId);
    if (!hasSkill) return st;

    const updatedSkills = st.skills.map(updateSkill);
    const stageCompleted = updatedSkills.filter((s) => s.user_status === "DONE").length;

    return {
      ...st,
      skills: updatedSkills,
      completed_skills: stageCompleted,
    };
  });

  const updatedRecSkills = detail.recommended_skills
    ? detail.recommended_skills.map(updateSkill)
    : null;

  let completedCount = 0;
  let learningCount = 0;
  let skippedCount = 0;
  let notStartedCount = 0;

  for (const st of updatedStages) {
    for (const s of st.skills) {
      const status = s.user_status || "NOT_STARTED";
      if (status === "DONE") completedCount += 1;
      else if (status === "LEARNING") learningCount += 1;
      else if (status === "SKIPPED") skippedCount += 1;
      else notStartedCount += 1;
    }
  }

  const totalSkills = detail.summary.total_skills;
  const progressPct =
    totalSkills > 0
      ? Math.min(100, Math.max(0, Math.round((completedCount / totalSkills) * 100)))
      : 0;

  return {
    ...detail,
    stages: updatedStages,
    recommended_skills: updatedRecSkills,
    summary: {
      ...detail.summary,
      completed_skills: completedCount,
      learning_skills: learningCount,
      skipped_skills: skippedCount,
      not_started_skills: notStartedCount,
      progress_percentage: progressPct,
    },
  };
}

  // Handle skill learning status update with safe optimistic UI
  const handleUpdateStatus = async (skillId: string, newStatus: RoadmapSkillStatus) => {
    if (!roadmapDetail) return;

    if (!effectiveUserId) {
      setError("Authentication required: Candidate identity is needed to track and persist roadmap progress.");
      return;
    }

    // Capture previous status of this specific skill for rollback
    let previousStatus: RoadmapSkillStatus = "NOT_STARTED";
    for (const st of roadmapDetail.stages) {
      const found = st.skills.find((s) => s.id === skillId);
      if (found) {
        previousStatus = (found.user_status as RoadmapSkillStatus) || "NOT_STARTED";
        break;
      }
    }

    if (previousStatus === newStatus) return;

    // Optimistically update status in local state using authoritative derivation
    setRoadmapDetail((prev) => (prev ? reconcileRoadmapSkillStatus(prev, skillId, newStatus) : prev));

    if (selectedSkill && selectedSkill.id === skillId) {
      setSelectedSkill((prev) => (prev ? { ...prev, user_status: newStatus } : null));
    }

    setUpdatingStatus(true);
    const res = await updateSkillProgress(skillId, newStatus, effectiveUserId);
    setUpdatingStatus(false);

    if (!res.success) {
      // Revert optimistic update for this specific skill without clobbering concurrent updates
      setRoadmapDetail((prev) => (prev ? reconcileRoadmapSkillStatus(prev, skillId, previousStatus) : prev));
      if (selectedSkill && selectedSkill.id === skillId) {
        setSelectedSkill((prev) => (prev ? { ...prev, user_status: previousStatus } : null));
      }
      setError(res.error || "Failed to update skill progress.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <Map className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
              Static Skill Roadmaps
            </h2>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20 font-semibold">
              12 Engineering Tracks
            </span>
          </div>
          <p className="text-xs text-slate-600 dark:text-neutral-400 max-w-2xl leading-relaxed">
            Curated, prerequisite-aware learning sequences with official documentation, video deep-dives,
            and 390 interactive coding challenges across canonical industry roles.
          </p>
        </div>

        <button
          type="button"
          onClick={() => loadDetail(selectedRoadmapId, ordering)}
          disabled={loadingDetail}
          className="self-start md:self-auto px-3 py-1.5 rounded-xl bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 text-xs font-medium text-slate-700 dark:text-neutral-300 hover:text-slate-900 dark:hover:text-white hover:border-slate-300 dark:hover:border-neutral-700 transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
          title="Refresh roadmap data"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loadingDetail ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* 12-Domain Career Track Selector */}
      <RoadmapRoleSelector
        roadmaps={roadmaps}
        selectedRoadmapId={selectedRoadmapId}
        onSelectRoadmap={handleSelectRoadmap}
        loading={loadingCatalog}
      />

      {/* Error Alert Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/40 text-rose-800 dark:text-rose-300 text-xs flex items-center justify-between gap-2 shadow-xs">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-rose-600 dark:text-rose-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-rose-600 dark:text-rose-400 hover:text-rose-800 dark:hover:text-rose-200 p-1 cursor-pointer"
            aria-label="Dismiss error"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loadingDetail && !roadmapDetail && (
        <div className="space-y-4">
          <div className="h-28 rounded-2xl bg-slate-100 dark:bg-neutral-900/60 border border-slate-200 dark:border-neutral-800 animate-pulse" />
          <div className="h-64 rounded-2xl bg-slate-100 dark:bg-neutral-900/60 border border-slate-200 dark:border-neutral-800 animate-pulse" />
        </div>
      )}

      {/* Active Roadmap View */}
      {roadmapDetail && (
        <div className="space-y-6">
          {/* Roadmap Description Header Card */}
          <div className="p-5 rounded-2xl bg-white dark:bg-neutral-900/40 border border-slate-200 dark:border-neutral-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
            <div className="space-y-1.5 max-w-3xl">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  {roadmapDetail.roadmap.title}
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-neutral-800 text-slate-600 dark:text-neutral-300 border border-slate-200 dark:border-neutral-700">
                  v{roadmapDetail.roadmap.version}
                </span>
                {roadmapDetail.roadmap.has_market_data ? (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20 font-semibold">
                    Market Intel Track
                  </span>
                ) : (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-100 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/20 font-semibold">
                    Curated Industry Track
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-600 dark:text-neutral-400 leading-relaxed">
                {roadmapDetail.roadmap.description}
              </p>
            </div>

            <div className="text-[11px] text-slate-500 dark:text-neutral-500 sm:text-right flex-shrink-0 flex items-center gap-1.5">
              <BookOpen className="h-3.5 w-3.5" />
              <span>{roadmapDetail.roadmap.total_stages} Stages • {roadmapDetail.roadmap.total_skills} Skills</span>
            </div>
          </div>

          {/* Progress Overview & Ordering Toggle */}
          <RoadmapProgress
            summary={roadmapDetail.summary}
            ordering={ordering}
            onToggleOrdering={handleToggleOrdering}
            hasMarketData={roadmapDetail.roadmap.has_market_data}
            practiceCompleted={practiceCounts.completed}
            practiceTotal={practiceCounts.total}
          />

          {/* Content Views: Recommended (Topological Sequence) vs Curated (Stage Curriculum) */}
          {ordering === "recommended" && roadmapDetail.recommended_skills ? (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                      Recommended Sequence Order
                    </h4>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-neutral-300 leading-relaxed">
                    Deterministic prerequisite-aware ordering calculated via Kahn&apos;s topological sort.
                    Foundational skills appear first, followed by dependent competencies.
                  </p>
                </div>
                <span className="text-xs font-mono px-2.5 py-1 rounded-md bg-emerald-100 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-500/30 font-semibold flex-shrink-0 self-start sm:self-auto">
                  Topological DAG
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3.5">
                {roadmapDetail.recommended_skills.map((skill, index) => (
                  <div key={skill.id} className="relative group">
                    <div className="absolute -top-2.5 left-3 z-10 px-2 py-0.5 rounded-full bg-slate-900 dark:bg-neutral-800 text-white text-[10px] font-mono font-semibold shadow-xs">
                      Step {index + 1}
                    </div>
                    <RoadmapSkillCard
                      skill={skill}
                      isSelected={skill.id === selectedSkill?.id}
                      onSelectSkill={setSelectedSkill}
                      allSkillStatuses={allSkillStatuses}
                    />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {roadmapDetail.stages.map((stage) => (
                <RoadmapStage
                  key={stage.id}
                  stage={stage}
                  selectedSkillId={selectedSkill?.id}
                  onSelectSkill={setSelectedSkill}
                  allSkillStatuses={allSkillStatuses}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!loadingCatalog && !loadingDetail && roadmaps.length === 0 && (
        <div className="text-center p-12 rounded-2xl bg-white dark:bg-neutral-900/40 border border-slate-200 dark:border-neutral-800 space-y-3">
          <Layers className="h-10 w-10 text-slate-400 dark:text-neutral-600 mx-auto" />
          <h3 className="text-base font-bold text-slate-800 dark:text-neutral-200">No Roadmaps Found</h3>
          <p className="text-xs text-slate-500 dark:text-neutral-400 max-w-sm mx-auto">
            Unable to locate static roadmap tracks. Verify database seeding in Phase 2.
          </p>
        </div>
      )}

      {/* Skill Detail Slide-Over Panel */}
      <SkillDetailPanel
        key={selectedSkill?.id}
        skill={selectedSkill}
        onClose={() => setSelectedSkill(null)}
        onUpdateStatus={handleUpdateStatus}
        updating={updatingStatus}
        userId={effectiveUserId}
        allSkillStatuses={allSkillStatuses}
      />
    </div>
  );
}
