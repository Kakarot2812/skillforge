"use client";

import React from "react";
import Link from "next/link";
import MarketDemandSection from "@/components/market/MarketDemandSection";
import RoadmapSection from "@/components/roadmap/RoadmapSection";
import CareerAssistant from "@/components/assistant/CareerAssistant";
import DemandIntelligenceExplorer from "@/components/DemandIntelligenceExplorer";
import { useCandidate } from "@/context/CandidateContext";
import { ArrowRight } from "lucide-react";

export interface DashboardViewProps {
  onNavigate?: (tab: "home" | "analyzer" | "dashboard") => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ onNavigate }) => {
  const {
    selectedRoleId,
    setSelectedRoleId,
    hasResume,
    resumeId,
    connectedGitHubUser,
    candidateReady,
  } = useCandidate();

  return (
    <div className="space-y-12 sm:space-y-16 pb-20 select-none">
      {/* 1. EXECUTIVE HEADER BANNER */}
      <div className="editorial-card p-6 sm:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-6 transition-colors duration-200">
        <div className="space-y-2 max-w-2xl">
          <div className="inline-flex items-center gap-2 text-[11px] font-mono text-muted uppercase tracking-widest">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            <span>02 / Career Analytics Suite</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-foreground">
            Career Dashboard
          </h1>
          <p className="text-xs sm:text-sm text-muted leading-relaxed">
            Track real-time hiring benchmarks, explore your personalized milestone DAG roadmap, and get evidence-grounded career coaching.
          </p>
        </div>

        {!candidateReady && (
          <div className="shrink-0">
            {onNavigate ? (
              <button
                type="button"
                onClick={() => onNavigate("analyzer")}
                className="editorial-btn-primary !py-2 !px-4 !text-xs !rounded-md flex items-center gap-2 cursor-pointer"
              >
                <span>Connect Evidence</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            ) : (
              <Link
                href="/analyzer"
                className="editorial-btn-primary !py-2 !px-4 !text-xs !rounded-md flex items-center gap-2"
              >
                <span>Connect Evidence</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            )}
          </div>
        )}
      </div>

      {/* 2. ANALYTICS METRICS STRIP (LARGE NUMBERS + THIN DIVIDERS) */}
      <div className="border-y border-border py-6 sm:py-8">
        <div className="grid grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-border">
          {/* Metric 1: Target Track */}
          <div className="p-4 sm:p-6 text-center space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-widest text-muted">
              Target Track
            </span>
            <div className="text-xl sm:text-2xl font-bold font-mono text-foreground truncate">
              {selectedRoleId ? selectedRoleId.replace(/_/g, " ").toUpperCase() : "SELECT ROLE"}
            </div>
            <p className="text-[11px] text-subtle font-normal">
              Active industry benchmark
            </p>
          </div>

          {/* Metric 2: Resume Evidence */}
          <div className="p-4 sm:p-6 text-center space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-widest text-muted">
              Resume Evidence
            </span>
            <div className={`text-xl sm:text-2xl font-bold font-mono ${hasResume ? "text-accent" : "text-foreground"}`}>
              {hasResume ? "VERIFIED" : "PENDING"}
            </div>
            <p className="text-[11px] text-subtle font-normal">
              {hasResume ? "Semantic parsing synced" : "Upload resume to verify"}
            </p>
          </div>

          {/* Metric 3: GitHub Code Evidence */}
          <div className="p-4 sm:p-6 text-center space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-widest text-muted">
              GitHub Code AST
            </span>
            <div className={`text-xl sm:text-2xl font-bold font-mono truncate ${connectedGitHubUser ? "text-accent" : "text-foreground"}`}>
              {connectedGitHubUser ? `@${connectedGitHubUser}` : "UNCONNECTED"}
            </div>
            <p className="text-[11px] text-subtle font-normal">
              {connectedGitHubUser ? "AST repository evidence" : "Connect GitHub profile"}
            </p>
          </div>

          {/* Metric 4: Market Geographic Scope */}
          <div className="p-4 sm:p-6 text-center space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-widest text-muted">
              Market Scope
            </span>
            <div className="text-xl sm:text-2xl font-bold font-mono text-foreground">
              INDIA TECH
            </div>
            <p className="text-[11px] text-subtle font-normal">
              Continuous market index
            </p>
          </div>
        </div>
      </div>

      {/* 3. SECTION 01: INDUSTRY SKILL DEMAND BENCHMARK */}
      <section aria-label="Industry Skill Demand Benchmark" className="space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-border text-xs">
          <span className="font-mono text-muted uppercase tracking-widest text-[11px]">
            Section 01 ── Market Demand Benchmark
          </span>
          <span className="text-muted text-[11px] font-mono">Live Requirements</span>
        </div>
        <MarketDemandSection
          selectedRoleId={selectedRoleId}
          onSelectRole={setSelectedRoleId}
        />
      </section>

      {/* 4. SECTION 02: PERSONALIZED CAREER ROADMAP */}
      <section aria-label="Personalized Career Roadmap" className="space-y-3 pt-4 border-t border-border">
        <div className="flex items-center justify-between pb-2 border-b border-border text-xs">
          <span className="font-mono text-muted uppercase tracking-widest text-[11px]">
            Section 02 ── Career Roadmap Milestones
          </span>
          <span className="text-muted text-[11px] font-mono">Prerequisite DAG</span>
        </div>
        <RoadmapSection
          selectedRoleId={selectedRoleId}
          candidateReady={candidateReady}
          hasResume={hasResume}
          resumeId={resumeId}
          connectedGitHubUsername={connectedGitHubUser}
        />
      </section>

      {/* 5. SECTION 03: AI CAREER INTELLIGENCE ASSISTANT */}
      <section aria-label="AI Career Intelligence Assistant" className="space-y-3 pt-4 border-t border-border">
        <div className="flex items-center justify-between pb-2 border-b border-border text-xs">
          <span className="font-mono text-muted uppercase tracking-widest text-[11px]">
            Section 03 ── AI Career Intelligence Assistant
          </span>
          <span className="text-muted text-[11px] font-mono">Deterministic Context</span>
        </div>
        <CareerAssistant
          selectedRoleId={selectedRoleId}
          candidateReady={candidateReady}
          hasResume={hasResume}
          resumeId={resumeId}
          connectedGitHubUsername={connectedGitHubUser}
        />
      </section>

      {/* 6. SECTION 04: CROSS-ROLE DEMAND INTELLIGENCE */}
      <section aria-label="Career Demand Intelligence Explorer" className="space-y-3 pt-4 border-t border-border">
        <div className="flex items-center justify-between pb-2 border-b border-border text-xs">
          <span className="font-mono text-muted uppercase tracking-widest text-[11px]">
            Section 04 ── Cross-Role Demand Matrix
          </span>
          <span className="text-muted text-[11px] font-mono">Comparative Intelligence</span>
        </div>
        <DemandIntelligenceExplorer />
      </section>
    </div>
  );
};
