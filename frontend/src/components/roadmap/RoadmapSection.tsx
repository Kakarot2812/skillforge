"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  Compass,
  Sparkles,
  RefreshCw,
  Loader2,
  AlertCircle,
  Award,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";
import {
  fetchActiveRoadmap,
  generateRoadmap,
  CanonicalRoadmapData,
} from "@/lib/api";
import RoadmapMilestoneCard from "./RoadmapMilestoneCard";
import RoadmapResourcesModal from "./RoadmapResourcesModal";
import RoadmapExplanationModal from "./RoadmapExplanationModal";

export interface RoadmapSectionProps {
  selectedRoleId: string;
  candidateReady: boolean;
  hasResume: boolean;
  resumeId: string | null;
  connectedGitHubUsername: string | null;
}

export default function RoadmapSection({
  selectedRoleId,
  candidateReady,
  hasResume,
  resumeId,
  connectedGitHubUsername,
}: RoadmapSectionProps) {
  const [roadmap, setRoadmap] = useState<CanonicalRoadmapData | null>(null);
  const [loadingActive, setLoadingActive] = useState<boolean>(false);
  const [generating, setGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [resourceModalSkill, setResourceModalSkill] = useState<{ id: string; name: string } | null>(null);
  const [isExplanationOpen, setIsExplanationOpen] = useState<boolean>(false);

  // Fetch candidate's active roadmap for the target role
  const loadActiveRoadmap = useCallback(async (roleId: string) => {
    if (!roleId) return;
    setLoadingActive(true);
    setError(null);
    try {
      const res = await fetchActiveRoadmap(roleId);
      if (res.success && res.data) {
        setRoadmap(res.data);
      } else {
        // 404 indicates no active roadmap exists yet for this role
        setRoadmap(null);
        if (res.status !== 404 && res.error) {
          setError(res.error);
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load active roadmap");
    } finally {
      setLoadingActive(false);
    }
  }, []);

  useEffect(() => {
    let isCancelled = false;
    if (selectedRoleId) {
      Promise.resolve().then(() => {
        if (!isCancelled) {
          loadActiveRoadmap(selectedRoleId);
        }
      });
    }
    return () => {
      isCancelled = true;
    };
  }, [selectedRoleId, loadActiveRoadmap]);

  // Generate deterministic canonical roadmap
  const handleGenerateRoadmap = async () => {
    if (!selectedRoleId) return;
    setGenerating(true);
    setError(null);
    try {
      const res = await generateRoadmap({
        role_id: selectedRoleId,
        location: "India",
        resume_id: resumeId || undefined,
        include_resume: hasResume,
        include_github: Boolean(connectedGitHubUsername),
        github_username: connectedGitHubUsername || undefined,
      });

      if (res.success && res.data) {
        setRoadmap(res.data);
      } else {
        setError(res.error || "Failed to generate deterministic roadmap.");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unexpected error generating roadmap");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div id="career-roadmap-section" className="scroll-mt-20 space-y-6">
      {/* Section Header */}
      <div className="bg-neutral-900/60 border border-neutral-800 rounded-2xl p-6 sm:p-8 backdrop-blur-md relative overflow-hidden shadow-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-6 border-b border-neutral-800">
          <div className="space-y-1.5 max-w-2xl">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <Award className="h-5 w-5" />
              </div>
              <h2 className="text-xl font-bold text-white tracking-tight">
                Personalized Career Roadmap
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold uppercase">
                Post-MVP Phase 4
              </span>
            </div>
            <p className="text-xs sm:text-sm text-neutral-400 leading-relaxed">
              Topological prerequisite sequencing (Kahn&apos;s DAG algorithm) aligning candidate skill gaps, vetted learning materials, and practical engineering challenges.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2.5">
            {roadmap && (
              <button
                type="button"
                onClick={() => setIsExplanationOpen(true)}
                disabled={generating || loadingActive}
                className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 active:bg-purple-600/40 text-purple-200 border border-purple-500/30 text-xs font-semibold transition-all cursor-pointer disabled:opacity-50"
              >
                <Sparkles className="h-4 w-4 text-purple-400" />
                <span>AI Coaching &amp; Strategy</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleGenerateRoadmap}
              disabled={generating || loadingActive || !selectedRoleId}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white text-xs font-bold shadow-lg shadow-emerald-950/40 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {generating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Computing DAG...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4" />
                  <span>{roadmap ? "Regenerate Roadmap" : "Generate Roadmap"}</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Active Roadmap Metadata Summary Bar */}
        {roadmap && (
          <div className="pt-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-3 rounded-xl bg-neutral-950/60 border border-neutral-800">
              <span className="text-[10px] text-neutral-500 uppercase tracking-wider block">Target Role</span>
              <span className="text-xs font-bold text-white truncate block">{roadmap.target_role_title}</span>
            </div>

            <div className="p-3 rounded-xl bg-neutral-950/60 border border-neutral-800">
              <span className="text-[10px] text-neutral-500 uppercase tracking-wider block">Total Milestones</span>
              <span className="text-xs font-mono font-bold text-emerald-400">{roadmap.total_milestones} Steps</span>
            </div>

            <div className="p-3 rounded-xl bg-neutral-950/60 border border-neutral-800">
              <span className="text-[10px] text-neutral-500 uppercase tracking-wider block">High Priority</span>
              <span className="text-xs font-mono font-bold text-rose-400">{roadmap.high_priority_count} Gaps</span>
            </div>

            <div className="p-3 rounded-xl bg-neutral-950/60 border border-neutral-800">
              <span className="text-[10px] text-neutral-500 uppercase tracking-wider block">Medium / Low</span>
              <span className="text-xs font-mono font-bold text-amber-400">
                {roadmap.medium_priority_count + roadmap.low_priority_count} Gaps
              </span>
            </div>

            <div className="p-3 rounded-xl bg-neutral-950/60 border border-neutral-800">
              <span className="text-[10px] text-neutral-500 uppercase tracking-wider block">Foundations</span>
              <span className="text-xs font-mono font-bold text-purple-400">
                {roadmap.transitive_prerequisite_count} Prerequisites
              </span>
            </div>

            <div className="p-3 rounded-xl bg-neutral-950/60 border border-neutral-800">
              <span className="text-[10px] text-neutral-500 uppercase tracking-wider block">Roadmap Lifecycle</span>
              <span className="text-xs font-mono font-bold text-blue-400 flex items-center gap-1">
                <ShieldCheck className="h-3.5 w-3.5 text-blue-400" />
                {roadmap.status}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 flex items-start gap-3 text-xs">
          <AlertCircle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <strong className="text-rose-200">Roadmap Processing Notice:</strong>
            <p className="mt-1 text-neutral-300">{error}</p>
          </div>
          <button
            type="button"
            onClick={handleGenerateRoadmap}
            className="px-3 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 font-medium text-xs transition-colors cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loadingActive && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="p-6 rounded-2xl bg-neutral-900/40 border border-neutral-800 animate-pulse space-y-3"
            >
              <div className="h-5 bg-neutral-800 rounded w-1/3" />
              <div className="h-3 bg-neutral-800/60 rounded w-2/3" />
              <div className="grid grid-cols-4 gap-3 pt-2">
                <div className="h-10 bg-neutral-800/40 rounded" />
                <div className="h-10 bg-neutral-800/40 rounded" />
                <div className="h-10 bg-neutral-800/40 rounded" />
                <div className="h-10 bg-neutral-800/40 rounded" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State: No active roadmap generated yet */}
      {!loadingActive && !roadmap && !generating && (
        <div className="p-8 sm:p-12 rounded-2xl bg-neutral-900/40 border border-neutral-800 border-dashed text-center space-y-4">
          <div className="h-14 w-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto shadow-inner">
            <Compass className="h-7 w-7" />
          </div>
          <div className="max-w-md mx-auto space-y-1.5">
            <h3 className="text-base font-bold text-white">No Roadmap Generated Yet</h3>
            <p className="text-xs text-neutral-400 leading-relaxed">
              Generate a deterministic learning path tailored to your verified candidate evidence. SkillForge will sequence your missing and partial skills in topological prerequisite order.
            </p>
            {!candidateReady && (
              <p className="text-[11px] text-amber-400/90 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-1.5 inline-block mt-2">
                Tip: Upload your resume or connect your GitHub above for evidence-based personalization.
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={handleGenerateRoadmap}
            disabled={!selectedRoleId}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-950/50 transition-all cursor-pointer"
          >
            <span>Generate Personalized Roadmap</span>
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Milestones Chronological List */}
      {!loadingActive && roadmap && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-neutral-400 px-1">
            <span className="font-semibold text-neutral-300">
              Milestone Sequence (Topological Order)
            </span>
            <span className="text-[11px] font-mono text-emerald-400">
              ✓ Server-Authoritative Sequencing
            </span>
          </div>

          <div className="space-y-4">
            {roadmap.milestones.map((milestone) => (
              <RoadmapMilestoneCard
                key={milestone.milestone_id || `${milestone.skill_id}-${milestone.order_index}`}
                milestone={milestone}
                roadmapId={roadmap.id}
                onViewResources={(skillId, skillName) =>
                  setResourceModalSkill({ id: skillId, name: skillName })
                }
                onMilestoneVerified={() => loadActiveRoadmap(selectedRoleId)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Curated Resources Modal */}
      {resourceModalSkill && (
        <RoadmapResourcesModal
          skillId={resourceModalSkill.id}
          skillName={resourceModalSkill.name}
          isOpen={Boolean(resourceModalSkill)}
          onClose={() => setResourceModalSkill(null)}
        />
      )}

      {/* AI Explanation / Coaching Modal */}
      {roadmap && roadmap.id && (
        <RoadmapExplanationModal
          roadmapId={roadmap.id}
          roleTitle={roadmap.target_role_title}
          isOpen={isExplanationOpen}
          onClose={() => setIsExplanationOpen(false)}
        />
      )}
    </div>
  );
}
