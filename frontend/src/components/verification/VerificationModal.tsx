"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  RoadmapMilestoneItem,
} from "@/lib/types/roadmap";
import {
  MilestoneVerificationResponse,
  MilestoneVerifyRequest,
} from "@/lib/types/verification";
import {
  verifyMilestone,
  fetchMilestoneVerification,
} from "@/lib/api";
import GitHubRepositorySelector from "./GitHubRepositorySelector";
import VerificationResult from "./VerificationResult";
import {
  X,
  ShieldCheck,
  Loader2,
  AlertCircle,
  KeyRound,
  Play,
  RotateCcw,
} from "lucide-react";

export interface VerificationModalProps {
  roadmapId: string;
  milestone: RoadmapMilestoneItem;
  isOpen: boolean;
  onClose: () => void;
  onVerificationSuccess?: () => void;
}

export default function VerificationModal({
  roadmapId,
  milestone,
  isOpen,
  onClose,
  onVerificationSuccess,
}: VerificationModalProps) {
  // Verification history & results
  const [latestVerification, setLatestVerification] = useState<MilestoneVerificationResponse | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(true);
  const [showReverifyForm, setShowReverifyForm] = useState<boolean>(false);

  // Form state
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null);
  // PAT token is held purely in volatile component state and cleared on request completion
  const [patToken, setPatToken] = useState<string>("");
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [verificationError, setVerificationError] = useState<string | null>(null);

  // Error code mapper for friendly, clear messaging
  const mapVerificationError = (status?: number, rawError?: string): string => {
    switch (status) {
      case 401:
        return "Authentication required. Please refresh candidate session context.";
      case 403:
        return "Access denied: Target repository or roadmap does not belong to candidate context.";
      case 404:
        return "Roadmap or milestone not found. Target milestone may have been updated.";
      case 409:
        return "Conflict detected during verification attempt.";
      case 422:
        return (
          rawError ||
          "Invalid verification request. Forked repositories cannot be verified per deterministic policy."
        );
      case 429:
        return "GitHub API rate limit exceeded. Please provide an optional personal access token (PAT) or wait a few minutes.";
      case 502:
        return "Upstream GitHub network failure. Please check repository accessibility and retry.";
      case 504:
        return "GitHub network connection timed out during repository inspection.";
      default:
        return rawError || "Deterministic verification failed. Please check repository evidence and try again.";
    }
  };

  // Load candidate's latest verification record
  const loadLatestHistory = useCallback(async () => {
    const milestoneId = milestone.milestone_id;
    if (!roadmapId || !milestoneId) return;
    setIsLoadingHistory(true);
    setVerificationError(null);
    try {
      const res = await fetchMilestoneVerification(roadmapId, milestoneId);
      if (res.success && res.data) {
        setLatestVerification(res.data);
        setShowReverifyForm(false);
      } else {
        // 404 is a standard empty state (no prior verification)
        setLatestVerification(null);
        setShowReverifyForm(true);
      }
    } catch {
      setLatestVerification(null);
      setShowReverifyForm(true);
    } finally {
      setIsLoadingHistory(false);
    }
  }, [roadmapId, milestone.milestone_id]);

  useEffect(() => {
    let isCancelled = false;
    if (isOpen) {
      Promise.resolve().then(() => {
        if (!isCancelled) {
          loadLatestHistory();
        }
      });
    }
    return () => {
      isCancelled = true;
    };
  }, [isOpen, loadLatestHistory]);

  // Keyboard close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !isVerifying) {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, isVerifying, onClose]);

  // Deterministic verification execution
  const handleVerify = async () => {
    if (!milestone.milestone_id) {
      setVerificationError("Milestone identifier is required for verification.");
      return;
    }

    if (!selectedRepoId) {
      setVerificationError("Please select a candidate-owned repository to verify.");
      return;
    }

    const milestoneId = milestone.milestone_id;
    setIsVerifying(true);
    setVerificationError(null);

    const payload: MilestoneVerifyRequest = {
      repository_id: selectedRepoId,
    };

    try {
      const res = await verifyMilestone(
        roadmapId,
        milestoneId,
        payload,
        patToken.trim() || undefined
      );

      if (res.success && res.data) {
        setLatestVerification(res.data);
        setShowReverifyForm(false);
        if (onVerificationSuccess) {
          onVerificationSuccess();
        }
      } else {
        setVerificationError(mapVerificationError(res.status, res.error));
      }
    } catch (err: unknown) {
      setVerificationError(
        err instanceof Error ? err.message : "Unexpected verification request failure"
      );
    } finally {
      // Guaranteed PAT cleanup across success, HTTP error, network error, or unexpected failure
      setPatToken("");
      setIsVerifying(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="verification-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-3xl max-h-[90vh] bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="p-5 sm:p-6 border-b border-neutral-800 flex items-start justify-between gap-4 bg-neutral-950/70">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-bold uppercase">
                GitHub Verification Loop
              </span>
              <span className="text-xs font-mono text-neutral-400">
                Milestone #{milestone.order_index}
              </span>
              {milestone.category && (
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-neutral-800 text-neutral-300 border border-neutral-700">
                  {milestone.category}
                </span>
              )}
            </div>
            <h2
              id="verification-modal-title"
              className="text-base sm:text-lg font-bold text-white tracking-tight"
            >
              Verify {milestone.skill_name}
            </h2>
            <p className="text-xs text-neutral-400 leading-relaxed max-w-xl">
              Deterministic project verification against candidate-owned repository deliverables and automated rubric criteria.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={isVerifying}
            className="p-1.5 rounded-lg bg-neutral-800/80 hover:bg-neutral-800 text-neutral-400 hover:text-white transition-colors cursor-pointer disabled:opacity-50"
            aria-label="Close verification dialog"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Content Scroll Area */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-6">
          {isLoadingHistory ? (
            <div className="py-12 flex flex-col items-center justify-center gap-2 text-xs text-neutral-400">
              <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
              <span>Loading latest verification audit record...</span>
            </div>
          ) : latestVerification && !showReverifyForm ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-neutral-300">
                  Latest Verification Audit Result
                </span>
                <button
                  type="button"
                  onClick={() => setShowReverifyForm(true)}
                  className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  <span>Verify with another repository / commit</span>
                </button>
              </div>

              <VerificationResult
                verification={latestVerification}
                onReverify={() => setShowReverifyForm(true)}
                isReverifying={isVerifying}
              />
            </div>
          ) : (
            <div className="space-y-5">
              {latestVerification && (
                <div className="p-3 rounded-xl bg-neutral-950/60 border border-neutral-800 flex items-center justify-between text-xs">
                  <span className="text-neutral-400">Previous Status:</span>
                  <span className="font-mono font-bold text-neutral-200">
                    {latestVerification.status}
                  </span>
                  <button
                    type="button"
                    onClick={() => setShowReverifyForm(false)}
                    className="text-indigo-400 hover:text-indigo-300 text-[11px] underline cursor-pointer"
                  >
                    View previous result
                  </button>
                </div>
              )}

              {/* Repository Selector */}
              <GitHubRepositorySelector
                selectedRepoId={selectedRepoId}
                onSelectRepo={(id) => setSelectedRepoId(id)}
                disabled={isVerifying}
              />

              {/* Optional PAT Input Section */}
              <div className="space-y-2 p-4 rounded-xl bg-neutral-950/70 border border-neutral-800">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="github-pat-input"
                    className="text-xs font-semibold text-neutral-300 flex items-center gap-1.5"
                  >
                    <KeyRound className="h-3.5 w-3.5 text-neutral-400" />
                    <span>GitHub Personal Access Token (Optional)</span>
                  </label>
                  <span className="text-[10px] font-mono text-neutral-500">
                    Volatile memory only
                  </span>
                </div>

                <p className="text-[11px] text-neutral-400 leading-relaxed">
                  Required if your repository has private artifacts or to avoid GitHub API rate limits. Your token is used only for this verification request and is not stored by SkillForge.
                </p>

                <input
                  id="github-pat-input"
                  type="password"
                  value={patToken}
                  onChange={(e) => setPatToken(e.target.value)}
                  disabled={isVerifying}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                  autoComplete="off"
                  className="w-full px-3.5 py-2 rounded-xl bg-neutral-900 border border-neutral-800 text-neutral-200 text-xs font-mono placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50 transition-all"
                />
              </div>

              {/* Error Alert Box */}
              {verificationError && (
                <div
                  role="alert"
                  aria-live="polite"
                  className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-start gap-2.5"
                >
                  <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                  <div className="space-y-0.5">
                    <p className="font-semibold">Verification Request Failed</p>
                    <p className="text-rose-400/90 text-[11px] leading-relaxed">
                      {verificationError}
                    </p>
                  </div>
                </div>
              )}

              {/* Authoritative Boundary Banner */}
              <div className="p-3 rounded-xl bg-neutral-950 border border-neutral-800/80 flex items-start gap-2.5 text-xs text-neutral-400">
                <ShieldCheck className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
                <p className="text-[11px] leading-relaxed">
                  GitHub verification is performed by SkillForge&apos;s deterministic backend verification engine. The result is authoritative for this verification attempt. AI explanations do not determine verification status.
                </p>
              </div>

              {/* Action Buttons */}
              <div className="pt-2 flex items-center justify-end gap-3 border-t border-neutral-800">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isVerifying}
                  className="px-4 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs font-medium transition-colors disabled:opacity-50 cursor-pointer"
                >
                  Cancel
                </button>

                <button
                  type="button"
                  onClick={handleVerify}
                  disabled={isVerifying || !selectedRepoId}
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white text-xs font-bold shadow-lg shadow-indigo-950/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  {isVerifying ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Verifying repository evidence...</span>
                    </>
                  ) : (
                    <>
                      <Play className="h-3.5 w-3.5 fill-current" />
                      <span>Verify Deliverables</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
