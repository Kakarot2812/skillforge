"use client";

import React from "react";
import Link from "next/link";
import TargetRoleSelector from "@/components/TargetRoleSelector";
import ResumeUploadPlaceholder from "@/components/ResumeUploadPlaceholder";
import GitHubConnectPlaceholder from "@/components/GitHubConnectPlaceholder";
import SkillGapExplorer from "@/components/SkillGapExplorer";
import { SkillAnalyzerHistory } from "@/components/analyzer/SkillAnalyzerHistory";
import { useCandidate } from "@/context/CandidateContext";
import { ArrowRight } from "lucide-react";

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
    <div className="space-y-12 sm:space-y-16 pb-20 select-none">
      {/* 1. EDITORIAL HEADER BANNER */}
      <div className="editorial-card p-6 sm:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-6 transition-colors duration-200">
        <div className="space-y-2 max-w-2xl">
          <div className="inline-flex items-center gap-2 text-[11px] font-mono text-muted uppercase tracking-widest">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            <span>Deterministic Skill Intelligence</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-foreground">
            Skill &amp; Evidence Analyzer
          </h1>
          <p className="text-xs sm:text-sm text-muted leading-relaxed">
            Select your target career track, upload your resume, or connect your GitHub repositories to extract verifiable capabilities and calculate real skill deficits.
          </p>
        </div>

        {/* Readiness Status & Next Step CTA */}
        <div className="flex flex-col sm:items-end gap-3 shrink-0">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md border border-border bg-surface-subtle text-xs font-mono">
            <span
              className={`h-2 w-2 rounded-full ${
                candidateReady ? "bg-accent animate-pulse" : "bg-muted"
              }`}
            />
            <span className="text-foreground font-medium">
              {candidateReady ? "Evidence Synced" : "Evidence Pending"}
            </span>
          </div>

          {candidateReady &&
            (onNavigate ? (
              <button
                type="button"
                onClick={() => onNavigate("dashboard")}
                className="editorial-btn-primary !py-2 !px-4 !text-xs !rounded-md flex items-center gap-2 cursor-pointer"
              >
                <span>View Career Roadmap</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            ) : (
              <Link
                href="/dashboard"
                className="editorial-btn-primary !py-2 !px-4 !text-xs !rounded-md flex items-center gap-2"
              >
                <span>View Career Roadmap</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            ))}
        </div>
      </div>

      {/* 2. SECTION: TARGET CAREER TRACK */}
      <section id="target-role-selector-section" aria-label="Target Role Selector" className="space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-border text-xs">
          <span className="font-mono text-muted uppercase tracking-widest text-[11px]">
            Career Track
          </span>
          <span className="text-muted text-[11px] font-mono">Industry Target</span>
        </div>
        <TargetRoleSelector
          selectedRoleId={selectedRoleId}
          onSelectRole={setSelectedRoleId}
        />
      </section>

      {/* 3. SECTION: DUAL VERIFIABLE EVIDENCE INPUTS */}
      <section id="verifiable-evidence-section" aria-label="Candidate Evidence Sources" className="space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-border text-xs">
          <span className="font-mono text-muted uppercase tracking-widest text-[11px]">
            Verifiable Evidence
          </span>
          <span className="text-muted text-[11px] font-mono">Deterministic AST &amp; Resume</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ResumeUploadPlaceholder onResumeChange={handleResumeChange} />
          <GitHubConnectPlaceholder onGitHubChange={handleGitHubChange} />
        </div>
      </section>

      {/* 4. SECTION: DEEP SKILL GAP & MARKET DEMAND EXPLORER */}
      <section id="skill-gap-explorer-section" aria-label="Skill Gap & Priorities" className="space-y-3 pt-4 border-t border-border">
        <div className="flex items-center justify-between pb-2 border-b border-border text-xs">
          <span className="font-mono text-muted uppercase tracking-widest text-[11px]">
            Skill Gap &amp; Market Demand
          </span>
          <span className="text-muted text-[11px] font-mono">Empirical Deficit Matrix</span>
        </div>

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

      {/* 5. SECTION: SKILL ANALYZER AUDIT HISTORY */}
      <section id="skill-analyzer-history-wrapper" aria-label="Skill Analyzer History" className="space-y-3 pt-4 border-t border-border">
        <div className="flex items-center justify-between pb-2 border-b border-border text-xs">
          <span className="font-mono text-muted uppercase tracking-widest text-[11px]">
            Audit History
          </span>
          <span className="text-muted text-[11px] font-mono">Candidate Assessment Log</span>
        </div>

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
      </section>
    </div>
  );
};
