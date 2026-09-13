"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  fetchSkillGaps,
  fetchRoles,
  JobRole,
  SkillGapResponse,
} from "@/lib/api";
import {
  History,
  ArrowRight,
  RotateCcw,
  AlertCircle,
  FileSearch,
  ChevronDown,
  Sparkles,
  Layers,
  FileText,
  GitBranch,
} from "lucide-react";

export interface HistoryRecordItem {
  roleId: string;
  roleTitle: string;
  roleSlug: string;
  roleCategory: string;
  calculatedAt: string;
  skillMatchPercentage: number;
  skillGapsCount: number;
  strongCount: number;
  partialCount: number;
  missingCount: number;
  totalRequiredSkills: number;
  evidenceSummary: string;
  hasResume: boolean;
  hasGitHub: boolean;
}

export interface SkillAnalyzerHistoryProps {
  currentRoleId?: string;
  onSelectRole?: (roleId: string) => void;
  candidateReady?: boolean;
  hasResume?: boolean;
  hasGitHub?: boolean;
  connectedGitHubUsername?: string | null;
  resumeFileName?: string | null;
  resumeId?: string | null;
}

/**
 * Persists an analyzed role record to candidate's local storage session.
 */
export function recordCandidateAnalysis(
  roleId: string,
  location: string = "India",
  hasResume: boolean = false,
  hasGitHub: boolean = false
) {
  if (typeof window === "undefined" || !roleId) return;
  try {
    const profile = typeof window !== "undefined" ? JSON.parse(localStorage.getItem("skillforge_user_profile") || "null") : null;
    const userId = profile?.id || "guest";
    const key = `skillforge_analysis_history_${userId}`;
    const raw = localStorage.getItem(key);
    let history: Array<{
      roleId: string;
      location: string;
      timestamp: string;
      hasResume: boolean;
      hasGitHub: boolean;
    }> = [];

    if (raw) {
      try {
        history = JSON.parse(raw);
      } catch {
        history = [];
      }
    }

    // Filter out existing occurrence to move to the top
    history = history.filter((item) => item.roleId !== roleId);
    history.unshift({
      roleId,
      location,
      timestamp: new Date().toISOString(),
      hasResume,
      hasGitHub,
    });

    localStorage.setItem(key, JSON.stringify(history.slice(0, 30)));
    window.dispatchEvent(
      new CustomEvent("skillforge:analysis-performed", {
        detail: { roleId, timestamp: new Date().toISOString() },
      })
    );
  } catch (err) {
    console.error("Failed to persist analysis record:", err);
  }
}

/**
 * Format ISO timestamp into standard readable date (e.g., "12 Sep 2026").
 */
function formatHistoryDate(isoString?: string): string {
  if (!isoString) {
    return new Date().toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) {
      return new Date().toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
    }
    return date.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return isoString.split("T")[0] || "Recent";
  }
}

export const SkillAnalyzerHistory: React.FC<SkillAnalyzerHistoryProps> = ({
  currentRoleId,
  onSelectRole,
  candidateReady,
  hasResume,
  hasGitHub,
  connectedGitHubUsername,
  resumeFileName,
  resumeId,
}) => {
  const [historyRecords, setHistoryRecords] = useState<HistoryRecordItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  // Determine effective candidate credentials
  const effectiveResumeId = resumeId || null;
  const effectiveHasResume = hasResume ?? Boolean(effectiveResumeId);

  const effectiveConnectedGitHub = connectedGitHubUsername || null;
  const effectiveHasGitHub = hasGitHub ?? Boolean(effectiveConnectedGitHub);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const profile = typeof window !== "undefined" ? JSON.parse(localStorage.getItem("skillforge_user_profile") || "null") : null;
      const userIdKey = profile?.id || "guest";
      const storageKey = `skillforge_analysis_history_${userIdKey}`;

      let storedEntries: Array<{
        roleId: string;
        location: string;
        timestamp: string;
        hasResume?: boolean;
        hasGitHub?: boolean;
      }> = [];

      if (typeof window !== "undefined") {
        const raw = localStorage.getItem(storageKey);
        if (raw) {
          try {
            storedEntries = JSON.parse(raw);
          } catch {
            storedEntries = [];
          }
        }
      }

      // If user has a currently active analyzed role and it's not yet in storedEntries, prepend it
      if (currentRoleId) {
        const exists = storedEntries.some((item) => item.roleId === currentRoleId);
        if (!exists) {
          storedEntries.unshift({
            roleId: currentRoleId,
            location: "India",
            timestamp: new Date().toISOString(),
            hasResume: effectiveHasResume,
            hasGitHub: effectiveHasGitHub,
          });
        }
      }

      if (storedEntries.length === 0) {
        setHistoryRecords([]);
        setLoading(false);
        return;
      }

      // Query real backend data for each role in stored history in parallel
      const incResume = Boolean(effectiveHasResume || effectiveResumeId);
      const incGitHub = Boolean(effectiveHasGitHub || effectiveConnectedGitHub);
      const ghUser = effectiveConnectedGitHub || undefined;
      const resResumeId = effectiveResumeId || undefined;

      const results = await Promise.allSettled(
        storedEntries.map(async (entry) => {
          const res = await fetchSkillGaps(
            entry.roleId,
            entry.location || "India",
            undefined,
            incResume,
            incGitHub,
            ghUser,
            resResumeId
          );

          if (!res.success || !res.data) {
            throw new Error(res.error || `Failed to fetch gap analysis for role ${entry.roleId}`);
          }

          const gapData = res.data;
          const summary = gapData.summary;
          const total = summary.total_required_skills || 0;
          const strong = summary.strong_count || 0;
          const partial = summary.partial_count || 0;
          const missing = summary.missing_count || 0;
          const matchPercent = total > 0 ? Math.round((strong / total) * 100) : 0;
          const gapsCount = missing + partial;

          // Determine evidence label from actual candidate evidence configuration
          let evidenceSummary = "Market benchmark";
          const itemHasResume = entry.hasResume ?? incResume;
          const itemHasGitHub = entry.hasGitHub ?? incGitHub;

          if (itemHasResume && itemHasGitHub) {
            evidenceSummary = "Resume + GitHub evidence";
          } else if (itemHasResume) {
            evidenceSummary = "Resume evidence";
          } else if (itemHasGitHub) {
            evidenceSummary = "GitHub evidence";
          }

          const calculatedAt = res.meta?.calculated_at || entry.timestamp || new Date().toISOString();

          const record: HistoryRecordItem = {
            roleId: gapData.role.role_id,
            roleTitle: gapData.role.title,
            roleSlug: gapData.role.slug,
            roleCategory: gapData.role.category,
            calculatedAt,
            skillMatchPercentage: matchPercent,
            skillGapsCount: gapsCount,
            strongCount: strong,
            partialCount: partial,
            missingCount: missing,
            totalRequiredSkills: total,
            evidenceSummary,
            hasResume: itemHasResume,
            hasGitHub: itemHasGitHub,
          };

          return record;
        })
      );

      const validRecords: HistoryRecordItem[] = [];
      let hadFailures = false;

      results.forEach((result) => {
        if (result.status === "fulfilled") {
          validRecords.push(result.value);
        } else {
          hadFailures = true;
        }
      });

      // Sort by newest timestamp first
      validRecords.sort((a, b) => {
        const timeA = new Date(a.calculatedAt).getTime();
        const timeB = new Date(b.calculatedAt).getTime();
        return timeB - timeA;
      });

      if (validRecords.length === 0 && hadFailures && storedEntries.length > 0) {
        setError("Unable to load analysis history.");
      } else {
        setHistoryRecords(validRecords);
      }
    } catch (err: unknown) {
      console.error("Error loading skill analyzer history:", err);
      setError("Unable to load analysis history.");
    } finally {
      setLoading(false);
    }
  }, [
    currentRoleId,
    effectiveHasResume,
    effectiveHasGitHub,
    effectiveResumeId,
    effectiveConnectedGitHub,
  ]);

  // Initial load
  useEffect(() => {
    let isCancelled = false;
    Promise.resolve().then(() => {
      if (!isCancelled) {
        loadHistory();
      }
    });
    return () => {
      isCancelled = true;
    };
  }, [loadHistory]);

  // Listen for real-time analysis updates or identity shifts
  useEffect(() => {
    const handleAnalysisPerformed = () => {
      loadHistory();
    };

    const handleIdentityUpdated = () => {
      loadHistory();
    };

    window.addEventListener("skillforge:analysis-performed", handleAnalysisPerformed);
    window.addEventListener("skillforge:identity-updated", handleIdentityUpdated);
    window.addEventListener("skillforge:github-evidence-updated", handleAnalysisPerformed);
    window.addEventListener("skillforge:resume-stale", handleAnalysisPerformed);

    return () => {
      window.removeEventListener("skillforge:analysis-performed", handleAnalysisPerformed);
      window.removeEventListener("skillforge:identity-updated", handleIdentityUpdated);
      window.removeEventListener("skillforge:github-evidence-updated", handleAnalysisPerformed);
      window.removeEventListener("skillforge:resume-stale", handleAnalysisPerformed);
    };
  }, [loadHistory]);

  const handleViewAnalysis = (roleId: string) => {
    if (onSelectRole) {
      onSelectRole(roleId);
    }
    // Smoothly scroll up to the Skill Gap Explorer section
    if (typeof window !== "undefined") {
      const targetElement =
        document.getElementById("skill-gap-explorer-section") ||
        document.getElementById("target-role-selector-section");

      if (targetElement) {
        targetElement.scrollIntoView({ behavior: "smooth", block: "start" });
      } else {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    }
  };

  const handleStartAnalysis = () => {
    if (typeof window !== "undefined") {
      const roleSelector =
        document.getElementById("target-role-selector-section") ||
        document.getElementById("verifiable-evidence-section");
      if (roleSelector) {
        roleSelector.scrollIntoView({ behavior: "smooth", block: "start" });
      } else {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    }
  };

  // Limit initial view to most recent 5 records
  const displayedRecords = isExpanded ? historyRecords : historyRecords.slice(0, 5);

  return (
    <section
      id="skill-analyzer-history-section"
      aria-label="Skill Analyzer History"
      className="space-y-4 pt-4 border-t border-neutral-200 dark:border-neutral-800/80 transition-colors duration-200"
    >
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2">
            <div className="p-1 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <History className="h-4 w-4" />
            </div>
            <h2 className="text-lg font-bold text-neutral-900 dark:text-white tracking-tight">
              Skill Analyzer History
            </h2>
          </div>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            Your previous skill-gap analyses and career assessments.
          </p>
        </div>

        {historyRecords.length > 0 && (
          <div className="text-xs text-neutral-500 dark:text-neutral-400 font-medium">
            {historyRecords.length} {historyRecords.length === 1 ? "assessment" : "assessments"} recorded
          </div>
        )}
      </div>

      {/* Loading Skeleton State */}
      {loading && (
        <div
          role="status"
          aria-live="polite"
          className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900/70 p-5 space-y-4 shadow-sm"
        >
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-600 dark:text-emerald-400 animate-pulse">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Loading your analysis history...</span>
          </div>

          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="p-4 rounded-xl border border-neutral-100 dark:border-neutral-800/60 bg-neutral-50/50 dark:bg-neutral-800/30 animate-pulse flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="space-y-2">
                  <div className="h-4 w-44 bg-neutral-200 dark:bg-neutral-700 rounded" />
                  <div className="h-3 w-60 bg-neutral-200 dark:bg-neutral-700 rounded" />
                  <div className="h-2.5 w-32 bg-neutral-200 dark:bg-neutral-700 rounded" />
                </div>
                <div className="flex sm:flex-col items-start sm:items-end gap-2">
                  <div className="h-3 w-20 bg-neutral-200 dark:bg-neutral-700 rounded" />
                  <div className="h-6 w-28 bg-neutral-200 dark:bg-neutral-700 rounded-lg" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div
          role="alert"
          className="rounded-2xl border border-rose-200 dark:border-rose-900/50 bg-rose-50/60 dark:bg-rose-950/20 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-colors"
        >
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <div className="text-xs font-bold text-rose-900 dark:text-rose-300">
                {error}
              </div>
              <p className="text-[11px] text-rose-700 dark:text-rose-400">
                We encountered an issue retrieving your verified gap assessments.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={loadHistory}
            className="inline-flex items-center justify-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold shadow-sm transition-colors cursor-pointer self-start sm:self-auto"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && historyRecords.length === 0 && (
        <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900/70 p-8 sm:p-10 text-center space-y-4 shadow-sm transition-colors duration-200">
          <div className="mx-auto w-12 h-12 rounded-2xl bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center text-neutral-500 dark:text-neutral-400">
            <FileSearch className="h-6 w-6" />
          </div>
          <div className="space-y-1 max-w-sm mx-auto">
            <h3 className="text-sm sm:text-base font-bold text-neutral-900 dark:text-white">
              No analysis history yet
            </h3>
            <p className="text-xs text-neutral-600 dark:text-neutral-400">
              Run your first Skill Analysis to see your results here.
            </p>
          </div>
          <div>
            <button
              type="button"
              onClick={handleStartAnalysis}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-600 dark:hover:bg-emerald-500 text-white text-xs font-semibold shadow-sm hover:shadow transition-all cursor-pointer"
            >
              <span>Start Skill Analysis</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* History List */}
      {!loading && !error && historyRecords.length > 0 && (
        <div className="space-y-3">
          <div className="divide-y divide-neutral-200 dark:divide-neutral-800/80 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900/70 shadow-sm overflow-hidden transition-colors duration-200">
            {displayedRecords.map((item) => (
              <div
                key={item.roleId}
                className="p-4 sm:p-5 hover:bg-neutral-50/80 dark:hover:bg-neutral-800/40 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                {/* Left Side: Role Title, Match %, Skill Gaps, Evidence */}
                <div className="space-y-1.5 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-sm sm:text-base font-bold text-neutral-900 dark:text-white truncate">
                      {item.roleTitle}
                    </h3>
                    {item.roleCategory && (
                      <span className="text-[10px] sm:text-[11px] px-2 py-0.5 rounded-md bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 font-medium">
                        {item.roleCategory}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 sm:gap-2.5 text-xs text-neutral-600 dark:text-neutral-300 flex-wrap">
                    <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                      Skill Match: {item.skillMatchPercentage}%
                    </span>
                    <span className="text-neutral-300 dark:text-neutral-700">•</span>
                    <span className="font-medium text-neutral-700 dark:text-neutral-300">
                      {item.skillGapsCount} {item.skillGapsCount === 1 ? "skill gap" : "skill gaps"}
                    </span>
                  </div>

                  <div className="text-[11px] text-neutral-500 dark:text-neutral-400 flex items-center gap-1.5">
                    {item.hasResume && item.hasGitHub ? (
                      <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                        <span>Resume + GitHub evidence</span>
                      </span>
                    ) : item.hasResume ? (
                      <span className="inline-flex items-center gap-1 text-teal-600 dark:text-teal-400 font-medium">
                        <FileText className="h-3 w-3" />
                        <span>Resume evidence</span>
                      </span>
                    ) : item.hasGitHub ? (
                      <span className="inline-flex items-center gap-1 text-cyan-600 dark:text-cyan-400 font-medium">
                        <GitBranch className="h-3 w-3" />
                        <span>GitHub evidence</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-neutral-500 dark:text-neutral-400">
                        <Layers className="h-3 w-3" />
                        <span>{item.evidenceSummary}</span>
                      </span>
                    )}
                  </div>
                </div>

                {/* Right Side: Timestamp & View Analysis Action */}
                <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-center gap-2 shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-neutral-100 dark:border-neutral-800/60">
                  <span className="text-xs text-neutral-500 dark:text-neutral-400 font-medium">
                    {formatHistoryDate(item.calculatedAt)}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleViewAnalysis(item.roleId)}
                    className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 inline-flex items-center gap-1 group/btn cursor-pointer py-1 px-2.5 rounded-lg hover:bg-emerald-500/10 dark:hover:bg-emerald-500/10 transition-colors"
                  >
                    <span>View Analysis</span>
                    <ArrowRight className="h-3.5 w-3.5 group-hover/btn:translate-x-0.5 transition-transform" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Expandable Show More / Show Less Toggle (for > 5 records) */}
          {historyRecords.length > 5 && (
            <div className="flex justify-center pt-1">
              <button
                type="button"
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-xs font-semibold text-neutral-600 dark:text-neutral-400 hover:text-emerald-600 dark:hover:text-emerald-400 inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-neutral-200 dark:border-neutral-800 hover:border-emerald-500/30 dark:hover:border-emerald-500/30 bg-white dark:bg-neutral-900 shadow-sm transition-all cursor-pointer"
              >
                <span>
                  {isExpanded ? "Show Less" : `View All History (${historyRecords.length})`}
                </span>
                <ChevronDown
                  className={`h-3.5 w-3.5 transition-transform duration-200 ${
                    isExpanded ? "rotate-180" : ""
                  }`}
                />
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
};
