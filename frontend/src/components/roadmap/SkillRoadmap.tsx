"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  RoadmapListItem,
  RoadmapDetailData,
  RoadmapSkillItem,
  RoadmapSkillStatus,
  fetchRoadmapsCatalog,
  fetchRoadmapDetail,
  updateSkillProgress,
} from "@/lib/api";
import RoadmapRoleSelector from "./RoadmapRoleSelector";
import RoadmapProgress from "./RoadmapProgress";
import RoadmapStage from "./RoadmapStage";
import RoadmapSkillCard from "./RoadmapSkillCard";
import SkillDetailPanel from "./SkillDetailPanel";
import { Sparkles, Map, AlertCircle, RefreshCw, Layers, Compass, ArrowRight, X } from "lucide-react";

interface SkillRoadmapProps {
  targetRoleId?: string;
  userId?: string;
}

export default function SkillRoadmap({ targetRoleId, userId: controlledUserId }: SkillRoadmapProps) {
  const [roadmaps, setRoadmaps] = useState<RoadmapListItem[]>([]);
  const [selectedRoadmapId, setSelectedRoadmapId] = useState<string>("");
  const [roadmapDetail, setRoadmapDetail] = useState<RoadmapDetailData | null>(null);
  const [ordering, setOrdering] = useState<"curated" | "recommended">("curated");
  const [selectedSkill, setSelectedSkill] = useState<RoadmapSkillItem | null>(null);

  const [loadingCatalog, setLoadingCatalog] = useState<boolean>(true);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);
  const [updatingStatus, setUpdatingStatus] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | undefined>(controlledUserId);

  // Sync active user identity from controlled prop or localStorage
  useEffect(() => {
    if (controlledUserId) {
      setUserId(controlledUserId);
      return;
    }
    if (typeof window !== "undefined") {
      const storedUserId = localStorage.getItem("skillforge_user_id");
      // Clean up legacy hardcoded dummy ID to prevent 404 User Not Found
      if (storedUserId === "00000000-0000-0000-0000-000000000001") {
        localStorage.removeItem("skillforge_user_id");
        setUserId(undefined);
      } else if (storedUserId && storedUserId.trim() !== "") {
        setUserId(storedUserId.trim());
      } else {
        setUserId(undefined);
      }
    }
  }, [controlledUserId]);

  // 1. Fetch Roadmaps Catalog on Mount
  useEffect(() => {
    async function loadCatalog() {
      setLoadingCatalog(true);
      setError(null);
      const res = await fetchRoadmapsCatalog();
      if (res.success && res.data && res.data.length > 0) {
        setRoadmaps(res.data);

        // If a targetRoleId is provided that matches a canonical roadmap, select it
        let initialRoadmap = res.data[0];
        if (targetRoleId) {
          const matched = res.data.find((r) => r.role_id === targetRoleId);
          if (matched) initialRoadmap = matched;
        }
        setSelectedRoadmapId(initialRoadmap.id);
      } else {
        setError(res.error || "Failed to load roadmaps catalog.");
      }
      setLoadingCatalog(false);
    }
    loadCatalog();
  }, [targetRoleId]);

  // 2. Fetch Roadmap Detail when selectedRoadmapId or ordering changes
  const loadDetail = useCallback(
    async (roadmapId: string, currentOrdering: "curated" | "recommended") => {
      if (!roadmapId) return;
      setLoadingDetail(true);
      setError(null);

      const res = await fetchRoadmapDetail(roadmapId, {
        ordering: currentOrdering,
        userId: userId,
      });

      if (res.success && res.data) {
        setRoadmapDetail(res.data);
      } else {
        setError(res.error || "Failed to load roadmap details.");
      }
      setLoadingDetail(false);
    },
    [userId]
  );

  useEffect(() => {
    if (selectedRoadmapId) {
      loadDetail(selectedRoadmapId, ordering);
    }
  }, [selectedRoadmapId, ordering, loadDetail]);

  // Handle roadmap selection
  const handleSelectRoadmap = (newRoadmapId: string) => {
    setSelectedRoadmapId(newRoadmapId);
    setSelectedSkill(null);
  };

  // Handle viewing mode toggle
  const handleToggleOrdering = (newOrdering: "curated" | "recommended") => {
    setOrdering(newOrdering);
  };

  // Handle status update (with optimistic UI update)
  const handleUpdateStatus = async (skillId: string, newStatus: RoadmapSkillStatus) => {
    if (!roadmapDetail) return;
    if (!userId) {
      setError("Authentication required: Sign in or provide a verified user profile to track and persist roadmap learning progress.");
      return;
    }

    // Optimistically update status in local state
    setRoadmapDetail((prev) => {
      if (!prev) return prev;

      let completedDelta = 0;
      let learningDelta = 0;
      let skippedDelta = 0;
      let notStartedDelta = 0;

      const updateSkillInList = (s: RoadmapSkillItem): RoadmapSkillItem => {
        if (s.id !== skillId) return s;

        // Old status decrement
        if (s.user_status === "DONE") completedDelta -= 1;
        else if (s.user_status === "LEARNING") learningDelta -= 1;
        else if (s.user_status === "SKIPPED") skippedDelta -= 1;
        else notStartedDelta -= 1;

        // New status increment
        if (newStatus === "DONE") completedDelta += 1;
        else if (newStatus === "LEARNING") learningDelta += 1;
        else if (newStatus === "SKIPPED") skippedDelta += 1;
        else notStartedDelta += 1;

        return { ...s, user_status: newStatus };
      };

      const updatedStages = prev.stages.map((st) => ({
        ...st,
        skills: st.skills.map(updateSkillInList),
        completed_skills:
          st.completed_skills +
          (newStatus === "DONE" ? 1 : 0) -
          (st.skills.find((s) => s.id === skillId)?.user_status === "DONE" ? 1 : 0),
      }));

      const updatedRecSkills = prev.recommended_skills
        ? prev.recommended_skills.map(updateSkillInList)
        : null;

      const newCompleted = Math.max(0, prev.summary.completed_skills + completedDelta);
      const newTotal = prev.summary.total_skills;
      const newPct = newTotal > 0 ? Math.round((newCompleted / newTotal) * 100) : 0;

      return {
        ...prev,
        stages: updatedStages,
        recommended_skills: updatedRecSkills,
        summary: {
          ...prev.summary,
          completed_skills: newCompleted,
          learning_skills: Math.max(0, prev.summary.learning_skills + learningDelta),
          skipped_skills: Math.max(0, prev.summary.skipped_skills + skippedDelta),
          not_started_skills: Math.max(0, prev.summary.not_started_skills + notStartedDelta),
          progress_percentage: newPct,
        },
      };
    });

    if (selectedSkill && selectedSkill.id === skillId) {
      setSelectedSkill((prev) => (prev ? { ...prev, user_status: newStatus } : null));
    }

    setUpdatingStatus(true);
    const res = await updateSkillProgress(skillId, newStatus, userId);
    setUpdatingStatus(false);

    if (!res.success) {
      // Revert / reload detail if update failed
      loadDetail(selectedRoadmapId, ordering);
      setError(res.error || "Failed to update skill progress.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Headline */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <Map className="h-4 w-4 text-emerald-400" />
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Personalized Skill Roadmaps
            </h2>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
              Evidence-Aware
            </span>
          </div>
          <p className="text-xs text-neutral-400 max-w-2xl leading-relaxed">
            Close verified skill gaps through structured, prerequisite-safe learning paths
            curated with official documentation and vetted video courses.
          </p>
        </div>

        <button
          onClick={() => loadDetail(selectedRoadmapId, ordering)}
          disabled={loadingDetail}
          className="self-start md:self-auto px-3 py-1.5 rounded-xl bg-neutral-900 border border-neutral-800 text-xs font-medium text-neutral-300 hover:text-white hover:border-neutral-700 transition-colors flex items-center gap-1.5"
          title="Refresh roadmap data"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loadingDetail ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Domain Selection Tabs */}
      <RoadmapRoleSelector
        roadmaps={roadmaps}
        selectedRoadmapId={selectedRoadmapId}
        onSelectRoadmap={handleSelectRoadmap}
        loading={loadingCatalog}
      />

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-950/20 border border-rose-900/40 text-rose-300 text-xs flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-rose-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-rose-400 hover:text-rose-200 p-1"
            aria-label="Dismiss error"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loadingDetail && !roadmapDetail && (
        <div className="space-y-4">
          <div className="h-28 rounded-2xl bg-neutral-900/60 border border-neutral-800 animate-pulse" />
          <div className="h-64 rounded-2xl bg-neutral-900/60 border border-neutral-800 animate-pulse" />
        </div>
      )}

      {/* Active Roadmap View */}
      {roadmapDetail && (
        <div className="space-y-6">
          {/* Roadmap Description Header */}
          <div className="p-4 rounded-2xl bg-gradient-to-r from-neutral-900/80 via-neutral-900/40 to-neutral-950/30 border border-neutral-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="space-y-1 max-w-3xl">
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">
                  {roadmapDetail.roadmap.title}
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-neutral-800 text-neutral-300 border border-neutral-700">
                  {roadmapDetail.roadmap.version}
                </span>
                {roadmapDetail.roadmap.has_market_data ? (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Empirical Market Demand
                  </span>
                ) : (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    Curated Industry Catalog
                  </span>
                )}
              </div>
              <p className="text-xs text-neutral-400 leading-relaxed">
                {roadmapDetail.roadmap.description}
              </p>
            </div>
          </div>

          {/* Progress Overview & View Mode Switcher */}
          <RoadmapProgress
            summary={roadmapDetail.summary}
            ordering={ordering}
            onToggleOrdering={handleToggleOrdering}
            hasMarketData={roadmapDetail.roadmap.has_market_data}
          />

          {/* Content Views: Recommended vs Curated Stages */}
          {ordering === "recommended" && roadmapDetail.recommended_skills ? (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-950/30 to-teal-950/20 border border-emerald-900/40 flex items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-emerald-400" />
                    <h4 className="text-sm font-semibold text-white">
                      Recommended Sequence Order
                    </h4>
                  </div>
                  <p className="text-xs text-neutral-300 leading-relaxed">
                    Prioritizes high-demand actionable gaps while strictly preserving foundational
                    prerequisite dependencies. Learn skills in order from left to right, top to
                    bottom.
                  </p>
                </div>
                <span className="text-xs font-mono px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 font-semibold flex-shrink-0">
                  Topological DAG
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3.5">
                {roadmapDetail.recommended_skills.map((skill, index) => (
                  <div key={skill.id} className="relative group">
                    <div className="absolute -top-2.5 left-3 z-10 px-2 py-0.5 rounded-full bg-neutral-900 border border-neutral-700 text-[10px] font-mono text-neutral-400 group-hover:text-emerald-400 group-hover:border-emerald-500/50 transition-colors">
                      Step {index + 1}
                    </div>
                    <RoadmapSkillCard
                      skill={skill}
                      isSelected={skill.id === selectedSkill?.id}
                      onSelectSkill={setSelectedSkill}
                      hasMarketData={roadmapDetail.roadmap.has_market_data}
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
                  hasMarketData={roadmapDetail.roadmap.has_market_data}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Right-Side Skill Detail Slide-Over Panel */}
      <SkillDetailPanel
        skill={selectedSkill}
        onClose={() => setSelectedSkill(null)}
        onUpdateStatus={handleUpdateStatus}
        updating={updatingStatus}
        userId={userId}
      />

    </div>
  );
}
