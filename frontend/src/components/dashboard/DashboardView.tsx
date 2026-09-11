"use client";

import React from "react";
import Link from "next/link";
import MarketDemandSection from "@/components/market/MarketDemandSection";
import RoadmapSection from "@/components/roadmap/RoadmapSection";
import CareerAssistant from "@/components/assistant/CareerAssistant";
import DemandIntelligenceExplorer from "@/components/DemandIntelligenceExplorer";
import { useCandidate } from "@/context/CandidateContext";
import {
  LayoutDashboard,
  TrendingUp,
  Compass,
  Bot,
  BarChart3,
  Briefcase,
  ShieldCheck,
  FileText,
  ArrowRight,
} from "lucide-react";

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
    <div className="space-y-10 pb-16">
      {/* Dashboard Top Header & Executive Stats Cards */}
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 sm:p-8 rounded-3xl bg-neutral-900/80 border border-neutral-800">
          <div className="space-y-1.5">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
              <LayoutDashboard className="h-3.5 w-3.5" />
              <span>Career Roadmap & Market Intelligence</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Career Dashboard
            </h1>
            <p className="text-xs sm:text-sm text-neutral-400 max-w-2xl">
              Track real-time hiring benchmarks, explore your personalized milestone DAG roadmap, and get evidence-grounded career coaching.
            </p>
          </div>

          {!candidateReady && (
            <div className="shrink-0">
              {onNavigate ? (
                <button
                  type="button"
                  onClick={() => onNavigate("analyzer")}
                  className="px-4 py-2.5 rounded-xl bg-amber-500/15 text-amber-300 hover:bg-amber-500/25 border border-amber-500/30 text-xs font-semibold flex items-center gap-1.5 transition-all"
                >
                  <span>Connect Evidence</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              ) : (
                <Link
                  href="/analyzer"
                  className="px-4 py-2.5 rounded-xl bg-amber-500/15 text-amber-300 hover:bg-amber-500/25 border border-amber-500/30 text-xs font-semibold flex items-center gap-1.5 transition-all"
                >
                  <span>Connect Evidence</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              )}
            </div>
          )}
        </div>

        {/* 4 Summary Stat Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl bg-neutral-900/60 border border-neutral-800 flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20 shrink-0">
              <Briefcase className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="text-[11px] text-neutral-400 font-medium truncate">Target Track</div>
              <div className="text-xs font-bold text-white truncate">
                {selectedRoleId ? selectedRoleId.replace(/_/g, " ").toUpperCase() : "Select Track"}
              </div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-neutral-900/60 border border-neutral-800 flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-teal-500/10 text-teal-400 flex items-center justify-center border border-teal-500/20 shrink-0">
              <FileText className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="text-[11px] text-neutral-400 font-medium truncate">Resume Evidence</div>
              <div className="text-xs font-bold text-white truncate">
                {hasResume ? "Verified & Parsed" : "Not Provided"}
              </div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-neutral-900/60 border border-neutral-800 flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center border border-indigo-500/20 shrink-0">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="text-[11px] text-neutral-400 font-medium truncate">GitHub Code Evidence</div>
              <div className="text-xs font-bold text-white truncate">
                {connectedGitHubUser ? `@${connectedGitHubUser}` : "Not Connected"}
              </div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-neutral-900/60 border border-neutral-800 flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center border border-purple-500/20 shrink-0">
              <TrendingUp className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="text-[11px] text-neutral-400 font-medium truncate">Hiring Benchmark</div>
              <div className="text-xs font-bold text-white truncate">India Tech Market</div>
            </div>
          </div>
        </div>
      </div>

      {/* 1. Industry Market Demand Benchmark */}
      <section aria-label="Industry Skill Demand Benchmark" className="space-y-4">
        <MarketDemandSection
          selectedRoleId={selectedRoleId}
          onSelectRole={setSelectedRoleId}
        />
      </section>

      {/* 2. Personalized Career Roadmap */}
      <section aria-label="Personalized Career Roadmap" className="space-y-4">
        <RoadmapSection
          selectedRoleId={selectedRoleId}
          candidateReady={candidateReady}
          hasResume={hasResume}
          resumeId={resumeId}
          connectedGitHubUsername={connectedGitHubUser}
        />
      </section>

      {/* 3. AI Career Intelligence Assistant */}
      <section aria-label="AI Career Intelligence Assistant" className="space-y-4">
        <CareerAssistant
          selectedRoleId={selectedRoleId}
          candidateReady={candidateReady}
          hasResume={hasResume}
          resumeId={resumeId}
          connectedGitHubUsername={connectedGitHubUser}
        />
      </section>

      {/* 4. Cross-Role Demand Intelligence */}
      <section aria-label="Career Demand Intelligence Explorer" className="space-y-4">
        <DemandIntelligenceExplorer />
      </section>
    </div>
  );
};
