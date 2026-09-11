"use client";

import React, { useState } from "react";
import {
  MilestoneVerificationResponse,
  VerificationStatus,
} from "@/lib/types/verification";
import VerificationEvidence from "./VerificationEvidence";
import {
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  AlertTriangle,
  RotateCcw,
  GitCommit,
  Calendar,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

export interface VerificationResultProps {
  verification: MilestoneVerificationResponse;
  onReverify?: () => void;
  isReverifying?: boolean;
}

const STATUS_CONFIGS: Record<
  VerificationStatus,
  {
    label: string;
    description: string;
    bg: string;
    text: string;
    border: string;
    barColor: string;
    icon: React.ComponentType<{ className?: string }>;
  }
> = {
  VERIFIED: {
    label: "VERIFIED",
    description:
      "Verification passed according to the deterministic backend verifier. Code deliverables and automated rubric criteria satisfied.",
    bg: "bg-emerald-500/10",
    text: "text-emerald-400",
    border: "border-emerald-500/30",
    barColor: "bg-emerald-500",
    icon: CheckCircle2,
  },
  PARTIAL: {
    label: "PARTIAL",
    description:
      "Some evidence and criteria passed, but verification did not meet the verified threshold.",
    bg: "bg-amber-500/10",
    text: "text-amber-400",
    border: "border-amber-500/30",
    barColor: "bg-amber-500",
    icon: AlertCircle,
  },
  UNVERIFIED: {
    label: "UNVERIFIED",
    description:
      "Available repository evidence did not meet the deterministic verification requirements.",
    bg: "bg-neutral-800",
    text: "text-neutral-400",
    border: "border-neutral-700",
    barColor: "bg-neutral-600",
    icon: HelpCircle,
  },
  FAILED: {
    label: "FAILED",
    description:
      "Verification could not be completed because of an external or upstream infrastructure issue.",
    bg: "bg-rose-500/10",
    text: "text-rose-400",
    border: "border-rose-500/30",
    barColor: "bg-rose-500",
    icon: AlertTriangle,
  },
};

export default function VerificationResult({
  verification,
  onReverify,
  isReverifying = false,
}: VerificationResultProps) {
  const [isEvidenceOpen, setIsEvidenceOpen] = useState<boolean>(true);

  const statusConfig = STATUS_CONFIGS[verification.status] || STATUS_CONFIGS.UNVERIFIED;
  const StatusIcon = statusConfig.icon;
  const confidencePercent =
    verification.confidence !== null && verification.confidence !== undefined
      ? Math.round(verification.confidence * 100)
      : null;

  const shortCommit = verification.commit_sha
    ? verification.commit_sha.slice(0, 7)
    : null;

  return (
    <div className="space-y-4">
      {/* Main Authoritative Result Card */}
      <div
        className={`p-5 rounded-2xl border transition-all ${statusConfig.bg} ${statusConfig.border} space-y-4`}
      >
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
          {/* Status Header */}
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold uppercase tracking-wider border ${statusConfig.bg} ${statusConfig.text} ${statusConfig.border}`}
              >
                <StatusIcon className="h-3.5 w-3.5 shrink-0" />
                <span>{statusConfig.label}</span>
              </span>

              {shortCommit && (
                <span className="inline-flex items-center gap-1 text-[11px] font-mono text-neutral-400 bg-neutral-950 px-2 py-0.5 rounded border border-neutral-800">
                  <GitCommit className="h-3 w-3 text-neutral-500" />
                  <span>{shortCommit}</span>
                </span>
              )}
            </div>

            <p className="text-xs text-neutral-300 leading-relaxed max-w-xl">
              {statusConfig.description}
            </p>
          </div>

          {/* Re-verify Action */}
          {onReverify && (
            <button
              type="button"
              onClick={onReverify}
              disabled={isReverifying}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-neutral-300 text-xs font-semibold border border-neutral-700 transition-colors disabled:opacity-50 cursor-pointer shrink-0 ml-auto sm:ml-0"
            >
              <RotateCcw className={`h-3.5 w-3.5 ${isReverifying ? "animate-spin" : ""}`} />
              <span>Verify Again</span>
            </button>
          )}
        </div>

        {/* Confidence Gauge Bar */}
        {confidencePercent !== null && (
          <div className="space-y-1.5 pt-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-neutral-400 font-medium">Deterministic Confidence</span>
              <span className={`font-mono font-bold ${statusConfig.text}`}>
                {confidencePercent}%
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-neutral-950 overflow-hidden border border-neutral-800">
              <div
                className={`h-full ${statusConfig.barColor} transition-all duration-500 rounded-full`}
                style={{ width: `${Math.max(confidencePercent, 4)}%` }}
              />
            </div>
          </div>
        )}

        {/* Metadata Footer */}
        <div className="pt-2 border-t border-neutral-800/80 flex flex-wrap items-center justify-between gap-2 text-[11px] text-neutral-400">
          <div className="flex items-center gap-1.5">
            <Calendar className="h-3 w-3 text-neutral-500" />
            <span>Verified at:</span>
            <span className="text-neutral-300 font-mono">
              {verification.created_at
                ? new Date(verification.created_at).toLocaleString()
                : "--"}
            </span>
          </div>

          <div className="flex items-center gap-1.5 font-mono text-[10px]">
            <span className="text-neutral-500">Milestone State:</span>
            <span className="px-1.5 py-0.2 rounded bg-neutral-900 text-neutral-300 border border-neutral-800">
              {verification.milestone_status}
            </span>
          </div>
        </div>
      </div>

      {/* Authoritative Boundary Notice */}
      <div className="p-3 rounded-xl bg-neutral-950/80 border border-neutral-800 flex items-start gap-2.5 text-xs text-neutral-400">
        <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
        <div className="space-y-0.5 text-[11px] leading-relaxed">
          <p className="font-semibold text-neutral-200">
            Authoritative Deterministic Verification
          </p>
          <p>
            GitHub verification is performed by SkillForge&apos;s deterministic backend verification engine. The result is authoritative for this verification attempt. AI explanations do not determine verification status.
          </p>
        </div>
      </div>

      {/* Expandable Deep Evidence Inspection */}
      <div className="rounded-2xl border border-neutral-800 bg-neutral-900/60 overflow-hidden">
        <button
          type="button"
          onClick={() => setIsEvidenceOpen(!isEvidenceOpen)}
          className="w-full p-3.5 flex items-center justify-between text-xs font-semibold text-neutral-200 hover:bg-neutral-800/50 transition-colors cursor-pointer"
          aria-expanded={isEvidenceOpen}
        >
          <span>Deterministic Evidence &amp; Evaluation Details</span>
          {isEvidenceOpen ? (
            <ChevronUp className="h-4 w-4 text-neutral-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-neutral-400" />
          )}
        </button>

        {isEvidenceOpen && (
          <div className="p-4 border-t border-neutral-800 bg-neutral-950/40">
            <VerificationEvidence
              details={verification.details || {}}
              commitSha={verification.commit_sha}
            />
          </div>
        )}
      </div>
    </div>
  );
}
