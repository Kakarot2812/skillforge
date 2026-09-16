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
  FileText,
  CheckCircle2,
  X,
} from "lucide-react";
import {
  fetchActiveRoadmap,
  generateRoadmap,
  downloadRoadmapPdf,
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

  // AI Roadmap PDF state
  const [downloadingPdf, setDownloadingPdf] = useState<boolean>(false);
  const [pdfSuccess, setPdfSuccess] = useState<boolean>(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  // Modals state
  const [resourceModalSkill, setResourceModalSkill] = useState<{ id: string; name: string } | null>(null);
  const [isExplanationOpen, setIsExplanationOpen] = useState<boolean>(false);

  const handleDownloadPdf = async () => {
    if (!roadmap?.id) return;
    setDownloadingPdf(true);
    setPdfError(null);
    setPdfSuccess(false);

    try {
      const res = await downloadRoadmapPdf(roadmap.id, { download: true });
      if (res.success) {
        setPdfSuccess(true);
        setTimeout(() => setPdfSuccess(false), 4000);
      } else {
        setPdfError(res.error || "Failed to generate AI roadmap PDF.");
      }
    } catch (err: unknown) {
      setPdfError(err instanceof Error ? err.message : "Unexpected error downloading PDF.");
    } finally {
      setDownloadingPdf(false);
    }
  };

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

  // Synchronize active roadmap when GitHub evidence updates
  useEffect(() => {
    const handleGitHubEvidenceUpdated = () => {
      if (selectedRoleId) {
        loadActiveRoadmap(selectedRoleId);
      }
    };
    window.addEventListener("skillforge:github-evidence-updated", handleGitHubEvidenceUpdated);
    return () => {
      window.removeEventListener("skillforge:github-evidence-updated", handleGitHubEvidenceUpdated);
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
        if (
          res.status === 403 ||
          res.error?.includes("Cross-user access denied: target resume")
        ) {
          if (typeof window !== "undefined") {
            try {
              localStorage.removeItem("skillforge_active_resume_id");
              localStorage.removeItem("skillforge_active_resume_filename");
            } catch {
              // ignore
            }
            window.dispatchEvent(new Event("skillforge:resume-stale"));
          }
          setError(
            "The selected resume does not belong to your active candidate profile. The stale resume selection has been cleared. Please upload your resume to generate a personalized career roadmap."
          );
        } else {
          setError(res.error || "Failed to generate deterministic roadmap.");
        }
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
      <div className="editorial-card p-6 sm:p-8 space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-6 border-b border-border">
          <div className="space-y-1.5 max-w-2xl">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-md bg-surface-subtle text-accent border border-border">
                <Award className="h-4 w-4" />
              </div>
              <h2 className="text-xl font-bold text-foreground tracking-tight">
                Personalized Career Roadmap
              </h2>
            </div>
            <p className="text-xs sm:text-sm text-muted leading-relaxed">
              Topological prerequisite sequencing (Kahn&apos;s DAG algorithm) aligning candidate skill gaps, vetted learning materials, and practical engineering challenges.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2.5">
            {roadmap && (
              <>
                <button
                  type="button"
                  onClick={handleDownloadPdf}
                  disabled={generating || loadingActive || downloadingPdf}
                  className="editorial-btn-secondary !py-2 !px-3.5 !text-xs !rounded-md flex items-center gap-2 cursor-pointer disabled:opacity-50 font-mono"
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

                <button
                  type="button"
                  onClick={() => setIsExplanationOpen(true)}
                  disabled={generating || loadingActive || downloadingPdf}
                  className="editorial-btn-secondary !py-2 !px-3.5 !text-xs !rounded-md flex items-center gap-2 cursor-pointer disabled:opacity-50 font-mono"
                >
                  <Sparkles className="h-3.5 w-3.5 text-accent" />
                  <span>AI Strategy</span>
                </button>
              </>
            )}

            <button
              type="button"
              onClick={handleGenerateRoadmap}
              disabled={generating || loadingActive || !selectedRoleId}
              className="editorial-btn-primary !py-2 !px-4 !text-xs !rounded-md flex items-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed font-mono"
            >
              {generating ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Computing DAG...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="h-3.5 w-3.5" />
                  <span>{roadmap ? "Regenerate Roadmap" : "Generate Roadmap"}</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Active Roadmap Metadata Summary (Analytics Strip) */}
        {roadmap && (
          <div className="pt-2 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 divide-y sm:divide-y-0 sm:divide-x divide-border border-b border-border pb-4">
            <div className="p-3 text-center sm:text-left">
              <span className="text-[10px] text-muted font-mono uppercase tracking-widest block">Target Role</span>
              <span className="text-xs font-bold text-foreground truncate block">{roadmap.target_role_title}</span>
            </div>

            <div className="p-3 text-center sm:text-left">
              <span className="text-[10px] text-muted font-mono uppercase tracking-widest block">Total Milestones</span>
              <span className="text-xs font-mono font-bold text-foreground">{roadmap.total_milestones} Steps</span>
            </div>

            <div className="p-3 text-center sm:text-left">
              <span className="text-[10px] text-muted font-mono uppercase tracking-widest block">High Priority</span>
              <span className="text-xs font-mono font-bold text-foreground">{roadmap.high_priority_count} Gaps</span>
            </div>

            <div className="p-3 text-center sm:text-left">
              <span className="text-[10px] text-muted font-mono uppercase tracking-widest block">Medium / Low</span>
              <span className="text-xs font-mono font-bold text-muted">
                {roadmap.medium_priority_count + roadmap.low_priority_count} Gaps
              </span>
            </div>

            <div className="p-3 text-center sm:text-left">
              <span className="text-[10px] text-muted font-mono uppercase tracking-widest block">Foundations</span>
              <span className="text-xs font-mono font-bold text-foreground">
                {roadmap.transitive_prerequisite_count} Prerequisites
              </span>
            </div>

            <div className="p-3 text-center sm:text-left">
              <span className="text-[10px] text-muted font-mono uppercase tracking-widest block">Lifecycle</span>
              <span className="text-xs font-mono font-bold text-accent flex items-center gap-1 justify-center sm:justify-start">
                <ShieldCheck className="h-3 w-3 text-accent" />
                {roadmap.status}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-md bg-danger-subtle border border-danger/30 text-danger flex items-start gap-3 text-xs">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <div className="flex-1">
            <strong className="font-medium">Roadmap Processing Notice:</strong>
            <p className="mt-0.5">{error}</p>
          </div>
          <button
            type="button"
            onClick={handleGenerateRoadmap}
            className="editorial-btn-secondary !py-1 !px-2.5 !text-xs !rounded-md"
          >
            Retry
          </button>
        </div>
      )}

      {/* PDF Error Alert */}
      {pdfError && (
        <div className="p-4 rounded-md bg-danger-subtle border border-danger/30 text-danger flex items-start justify-between gap-3 text-xs">
          <div className="flex items-start gap-2.5">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <div className="flex-1">
              <strong className="font-medium">AI Roadmap PDF Generation Notice:</strong>
              <p className="mt-0.5">{pdfError}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setPdfError(null)}
            className="text-danger hover:opacity-80 p-1 cursor-pointer"
            aria-label="Dismiss error"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loadingActive && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="p-6 rounded-md bg-surface-subtle border border-border animate-pulse space-y-3"
            >
              <div className="h-5 bg-border rounded w-1/3" />
              <div className="h-3 bg-border/60 rounded w-2/3" />
              <div className="grid grid-cols-4 gap-3 pt-2">
                <div className="h-8 bg-border/40 rounded" />
                <div className="h-8 bg-border/40 rounded" />
                <div className="h-8 bg-border/40 rounded" />
                <div className="h-8 bg-border/40 rounded" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State: No active roadmap generated yet */}
      {!loadingActive && !roadmap && !generating && (
        <div className="editorial-card text-center p-8 sm:p-12 space-y-4 border-dashed">
          <div className="h-12 w-12 rounded-md bg-surface-subtle border border-border text-muted flex items-center justify-center mx-auto">
            <Compass className="h-6 w-6 text-accent" />
          </div>
          <div className="max-w-md mx-auto space-y-1.5">
            <h3 className="text-base font-bold text-foreground">No Roadmap Generated Yet</h3>
            <p className="text-xs text-muted leading-relaxed">
              Generate a deterministic learning path tailored to your verified candidate evidence. SkillForge will sequence your missing and partial skills in topological prerequisite order.
            </p>
            {!candidateReady && (
              <p className="text-[11px] text-muted bg-surface-subtle border border-border rounded-sm px-3 py-1.5 inline-block mt-2 font-mono">
                Tip: Upload your resume or connect GitHub for evidence-grounded personalization.
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={handleGenerateRoadmap}
            disabled={!selectedRoleId}
            className="editorial-btn-primary !py-2 !px-4 !text-xs !rounded-md inline-flex items-center gap-2 font-mono cursor-pointer disabled:opacity-50"
          >
            <span>Generate Personalized Roadmap</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Milestones Chronological List (Technical Timeline) */}
      {!loadingActive && roadmap && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-muted px-1">
            <span className="font-mono uppercase tracking-widest text-[11px]">
              Milestone Sequence (Topological Order)
            </span>
            <span className="text-[11px] font-mono text-muted">
              Server-Authoritative Sequencing
            </span>
          </div>

          {/* Technical Timeline with Subtle Connecting Line */}
          <div className="relative pl-6 sm:pl-8 space-y-6">
            <div className="absolute left-2.5 sm:left-3.5 top-6 bottom-6 w-[1px] bg-border" />
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
