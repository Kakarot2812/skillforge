"use client";

import React from "react";
import Link from "next/link";
import TargetRoleSelector from "@/components/TargetRoleSelector";
import ResumeUploadPlaceholder from "@/components/ResumeUploadPlaceholder";
import GitHubConnectPlaceholder from "@/components/GitHubConnectPlaceholder";
import SkillGapExplorer from "@/components/SkillGapExplorer";
import { SkillAnalyzerHistory } from "@/components/analyzer/SkillAnalyzerHistory";
import { useCandidate } from "@/context/CandidateContext";
import { ScanLine, ArrowRight, ShieldCheck } from "lucide-react";

export interface AnalyzerViewProps {
  onNavigate?: (tab: "home" | "analyzer" | "dashboard") => void;
}

export const AnalyzerView: React.FC<AnalyzerViewProps> = ({ onNavigate }) => {
  const {
    selectedRoleId,
    setSelectedRoleId,
    hasResume,
    resumeFileName,
    resumeId,
    connectedGitHubUser,
    candidateReady,
    handleResumeChange,
    handleGitHubChange,
  } = useCandidate();

  return (
    <div className="space-y-10 pb-16">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 sm:p-8 rounded-3xl bg-white dark:bg-neutral-900/80 border border-neutral-200 dark:border-neutral-800 shadow-md shadow-neutral-200/50 dark:shadow-none transition-colors duration-200">
        <div className="space-y-1.5">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-400 text-xs font-semibold">
            <ScanLine className="h-3.5 w-3.5" />
            <span>Candidate Skill Gap & Evidence Analyzer</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">
            Skill & Evidence Analyzer
          </h1>
          <p className="text-xs sm:text-sm text-neutral-600 dark:text-neutral-400 max-w-2xl">
            Select your target career track, upload your resume, or connect your GitHub profile to extract verifiable skills and evaluate gaps against market benchmarks.
          </p>
        </div>

        {/* Ready Badge & CTA */}
        <div className="flex flex-col sm:items-end gap-2 shrink-0">
          <span
            className={`text-xs px-3 py-1.5 rounded-xl border font-semibold inline-flex items-center gap-1.5 ${
              candidateReady
                ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20"
                : "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20"
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                candidateReady ? "bg-emerald-500 dark:bg-emerald-400 animate-pulse" : "bg-amber-500 dark:bg-amber-400"
              }`}
            />
            <span>{candidateReady ? "Evidence Ready" : "Evidence Needed"}</span>
          </span>

          {candidateReady &&
            (onNavigate ? (
              <button
                type="button"
                onClick={() => onNavigate("dashboard")}
                className="text-xs text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 font-semibold inline-flex items-center gap-1 cursor-pointer"
              >
                <span>Go to Roadmap Dashboard</span>
                <ArrowRight className="h-3 w-3" />
              </button>
            ) : (
              <Link
                href="/dashboard"
                className="text-xs text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 font-semibold inline-flex items-center gap-1"
              >
                <span>Go to Roadmap Dashboard</span>
                <ArrowRight className="h-3 w-3" />
              </Link>
            ))}
        </div>
      </div>

      {/* Target Career Track Selector */}
      <section id="target-role-selector-section" aria-label="Target Role Selector" className="space-y-4">
        <TargetRoleSelector
          selectedRoleId={selectedRoleId}
          onSelectRole={setSelectedRoleId}
        />
      </section>

      {/* Dual Evidence Inputs: Resume & GitHub */}
      <section id="verifiable-evidence-section" aria-label="Candidate Evidence Sources" className="space-y-4">
        <div className="space-y-1">
          <h2 className="text-base font-bold text-neutral-900 dark:text-neutral-200 tracking-tight flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <span>Provide Verifiable Evidence</span>
          </h2>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            Provide at least one evidence source for deterministic AST validation and semantic parsing.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ResumeUploadPlaceholder onResumeChange={handleResumeChange} />
          <GitHubConnectPlaceholder onGitHubChange={handleGitHubChange} />
        </div>
      </section>

      {/* Deep Skill Gap Explorer */}
      <section id="skill-gap-explorer-section" aria-label="Skill Gap & Priorities" className="space-y-4 pt-4 border-t border-neutral-200 dark:border-neutral-800/80">
        <SkillGapExplorer
          selectedRoleId={selectedRoleId}
          onSelectRole={setSelectedRoleId}
          candidateReady={candidateReady}
          hasResume={hasResume}
          hasGitHub={Boolean(connectedGitHubUser)}
          connectedGitHubUsername={connectedGitHubUser}
          resumeFileName={resumeFileName}
          resumeId={resumeId}
        />
      </section>

      {/* Skill Analyzer History (Placed BELOW Skill Gap & Priorities) */}
      <SkillAnalyzerHistory
        currentRoleId={selectedRoleId}
        onSelectRole={setSelectedRoleId}
        candidateReady={candidateReady}
        hasResume={hasResume}
        hasGitHub={Boolean(connectedGitHubUser)}
        connectedGitHubUsername={connectedGitHubUser}
        resumeFileName={resumeFileName}
        resumeId={resumeId}
      />
    </div>
  );
};
