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
  fetchActiveRoadmap,
  generateRoadmap,
  downloadRoadmapPdf,
  updateSkillProgress,
} from "@/lib/api";
import { getCandidateUserId, ensureCandidateIdentity } from "@/lib/identity";
import RoadmapRoleSelector from "./RoadmapRoleSelector";
import RoadmapProgress from "./RoadmapProgress";
import RoadmapStage from "./RoadmapStage";
import RoadmapSkillCard from "./RoadmapSkillCard";
import SkillDetailPanel from "./SkillDetailPanel";
import {
  Sparkles,
  Map,
  AlertCircle,
  RefreshCw,
  X,
  BookOpen,
  Layers,
  FileText,
  CheckCircle2,
  Loader2,
} from "lucide-react";

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

  // AI Roadmap PDF state
  const [downloadingPdf, setDownloadingPdf] = useState<boolean>(false);
  const [pdfSuccess, setPdfSuccess] = useState<boolean>(false);
  const [pdfMessage, setPdfMessage] = useState<string | null>(null);

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

  // Generate and download personalized AI Career Roadmap PDF
  const handleGeneratePdf = async () => {
    if (!roadmapDetail) return;
    setDownloadingPdf(true);
    setError(null);
    setPdfMessage(null);
    setPdfSuccess(false);

    try {
      const roleId = roadmapDetail.roadmap.role_id;
      if (!roleId) {
        setError(
          "AI Personalized Roadmap PDF is available for Market Intelligence tracks (Backend, Full Stack, Frontend, Cloud/DevOps, AI/ML)."
        );
        setDownloadingPdf(false);
        return;
      }

      // Try fetching active candidate roadmap
      let candidateRoadmapId: string | null = null;
      const activeRes = await fetchActiveRoadmap(roleId, effectiveUserId);
      if (activeRes.success && activeRes.data?.id) {
        candidateRoadmapId = activeRes.data.id;
      } else {
        // Auto-generate candidate roadmap if not yet created
        const genRes = await generateRoadmap(
          { role_id: roleId, location: "India" },
          effectiveUserId
        );
        if (genRes.success && genRes.data?.id) {
          candidateRoadmapId = genRes.data.id;
        } else {
          throw new Error(genRes.error || "Failed to initialize personalized roadmap for this role.");
        }
      }

      if (!candidateRoadmapId) {
        throw new Error("Candidate roadmap could not be established.");
      }

      // Download PDF
      const pdfRes = await downloadRoadmapPdf(candidateRoadmapId, {
        download: true,
        userId: effectiveUserId,
      });

      if (pdfRes.success) {
        setPdfSuccess(true);
        setPdfMessage("Personalized AI Roadmap PDF successfully generated and downloaded!");
        setTimeout(() => {
          setPdfSuccess(false);
          setPdfMessage(null);
        }, 5000);
      } else {
        setError(pdfRes.error || "Failed to download AI roadmap PDF.");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error generating AI roadmap PDF.");
    } finally {
      setDownloadingPdf(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Header Section */}
      <div className="editorial-card p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6 transition-colors duration-200">
        <div className="space-y-1.5">
          <div className="inline-flex items-center gap-2 text-[11px] font-mono text-muted uppercase tracking-widest">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            <span>03 / Structured Milestone Sequence</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-foreground tracking-tight">
            Curated Skill Roadmaps
          </h2>
          <p className="text-xs sm:text-sm text-muted max-w-2xl leading-relaxed">
            Prerequisite-aware milestone pathways featuring official documentation, video deep-dives, and structured engineering practice.
          </p>
        </div>

        <button
          type="button"
          onClick={() => loadDetail(selectedRoadmapId, ordering)}
          disabled={loadingDetail}
          className="editorial-btn-secondary !py-2 !px-3.5 !text-xs !rounded-md self-start md:self-auto flex items-center gap-1.5 cursor-pointer"
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
        <div className="p-4 rounded-md bg-danger-subtle border border-danger/30 text-danger text-xs flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-danger hover:opacity-80 p-1 cursor-pointer"
            aria-label="Dismiss error"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* PDF Success Alert Banner */}
      {pdfMessage && (
        <div className="p-3.5 rounded-md bg-accent-subtle border border-accent/30 text-accent text-xs flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-success" />
            <span>{pdfMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setPdfMessage(null)}
            className="text-accent hover:opacity-80 p-1 cursor-pointer"
            aria-label="Dismiss message"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loadingDetail && !roadmapDetail && (
        <div className="space-y-4">
          <div className="h-28 rounded-md bg-surface-subtle border border-border animate-pulse" />
          <div className="h-64 rounded-md bg-surface-subtle border border-border animate-pulse" />
        </div>
      )}

      {/* Active Roadmap View */}
      {roadmapDetail && (
        <div className="space-y-8">
          {/* Roadmap Description Header Card */}
          <div className="editorial-card p-5 sm:p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="space-y-1.5 max-w-3xl">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-base font-bold text-foreground">
                  {roadmapDetail.roadmap.title}
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-subtle text-muted border border-border">
                  v{roadmapDetail.roadmap.version}
                </span>
                {roadmapDetail.roadmap.has_market_data ? (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent-subtle text-accent border border-accent/30 font-semibold">
                    Market Intel Track
                  </span>
                ) : (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-subtle text-muted border border-border font-semibold">
                    Curated Industry Track
                  </span>
                )}
              </div>
              <p className="text-xs text-muted leading-relaxed">
                {roadmapDetail.roadmap.description}
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 shrink-0">
              <div className="text-[11px] font-mono text-muted flex items-center gap-1.5">
                <BookOpen className="h-3.5 w-3.5" />
                <span>{roadmapDetail.roadmap.total_stages} Stages • {roadmapDetail.roadmap.total_skills} Skills</span>
              </div>

              {roadmapDetail.roadmap.has_market_data && (
                <button
                  type="button"
                  onClick={handleGeneratePdf}
                  disabled={downloadingPdf}
                  className="editorial-btn-secondary !py-1.5 !px-3 !text-xs !rounded-md flex items-center gap-1.5 cursor-pointer disabled:opacity-50 font-mono"
                  title="Generate and download publication-quality AI-powered career roadmap PDF"
                >
                  {downloadingPdf ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-accent" />
                      <span>Synthesizing PDF...</span>
                    </>
                  ) : pdfSuccess ? (
                    <>
                      <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                      <span className="text-success">PDF Downloaded</span>
                    </>
                  ) : (
                    <>
                      <FileText className="h-3.5 w-3.5 text-accent" />
                      <span>Generate AI Roadmap PDF</span>
                    </>
                  )}
                </button>
              )}
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
              <div className="p-4 rounded-md border border-border bg-surface-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-accent" />
                    <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
                      Recommended Sequence Order (Topological DAG)
                    </h4>
                  </div>
                  <p className="text-xs text-muted leading-relaxed">
                    Deterministic prerequisite-aware ordering calculated via topological sort.
                    Foundational skills appear first, followed by dependent competencies.
                  </p>
                </div>
                <span className="text-[10px] font-mono px-2.5 py-1 rounded-md bg-surface text-foreground border border-border font-semibold shrink-0 self-start sm:self-auto">
                  Topological DAG
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3.5">
                {roadmapDetail.recommended_skills.map((skill, index) => (
                  <div key={skill.id} className="relative group">
                    <div className="absolute -top-2.5 left-3 z-10 px-2 py-0.5 rounded-md bg-foreground text-background text-[10px] font-mono font-semibold shadow-xs">
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
            <div className="space-y-6 pt-2">
              {roadmapDetail.stages.map((stage, idx) => (
                <RoadmapStage
                  key={stage.id}
                  stage={stage}
                  isLast={idx === roadmapDetail.stages.length - 1}
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
        <div className="editorial-card text-center p-12 space-y-3">
          <Layers className="h-10 w-10 text-muted mx-auto" />
          <h3 className="text-base font-bold text-foreground">No Roadmaps Found</h3>
          <p className="text-xs text-muted max-w-sm mx-auto">
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
