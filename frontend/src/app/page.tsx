"use client";

import React, { useState } from "react";
import TargetRoleSelector from "@/components/TargetRoleSelector";
import ResumeUploadPlaceholder from "@/components/ResumeUploadPlaceholder";
import GitHubConnectPlaceholder from "@/components/GitHubConnectPlaceholder";
import SkillGapExplorer from "@/components/SkillGapExplorer";
import MarketDemandSection from "@/components/market/MarketDemandSection";
import DemandIntelligenceExplorer from "@/components/DemandIntelligenceExplorer";
import RoadmapSection from "@/components/roadmap/RoadmapSection";
import CareerAssistant from "@/components/assistant/CareerAssistant";
import { Sparkles, CheckCircle2, TrendingUp, Compass, Award, Bot } from "lucide-react";

import { ensureCandidateIdentity } from "@/lib/identity";

export default function DashboardPage() {
  const [selectedRoleId, setSelectedRoleId] = useState<string>("");
  const [hasResume, setHasResume] = useState<boolean>(false);
  const [resumeFileName, setResumeFileName] = useState<string | null>(null);
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [connectedGitHubUser, setConnectedGitHubUser] = useState<string | null>(null);

  // Sync client-side state on mount from local storage and establish candidate identity
  React.useEffect(() => {
    if (typeof window !== "undefined") {
      Promise.resolve().then(async () => {
        await ensureCandidateIdentity();

        const activeResume = localStorage.getItem("skillforge_active_resume_id");
        const activeFileName = localStorage.getItem("skillforge_active_resume_filename");
        setHasResume(Boolean(activeResume));
        setResumeFileName(activeFileName || null);
        setResumeId(activeResume || null);

        const activeGitHub = localStorage.getItem("skillforge_connected_github_user");
        setConnectedGitHubUser(activeGitHub || null);
      });
    }
  }, []);

  // Memoized handlers to prevent infinite render loops in child components
  const handleResumeChange = React.useCallback((has: boolean, filename?: string, id?: string) => {
    setHasResume(has);
    setResumeFileName(filename || null);
    setResumeId(has ? (id || null) : null);
  }, []);

  const handleGitHubChange = React.useCallback((username: string | null) => {
    setConnectedGitHubUser(username);
  }, []);

  const candidateReady = Boolean(hasResume || connectedGitHubUser);

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-neutral-100 flex flex-col selection:bg-emerald-500/30 selection:text-emerald-200 scroll-pt-20">
      {/* Top Navigation Bar: Solid opaque background strictly preventing content peek-through */}
      <header className="sticky top-0 z-50 w-full h-16 bg-neutral-950 border-b border-neutral-800 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-emerald-600 via-teal-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-emerald-950/50">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-base tracking-tight bg-gradient-to-r from-white via-neutral-200 to-neutral-400 bg-clip-text text-transparent">
                  SkillForge AI
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
                  Evidence-Driven
                </span>
              </div>
              <p className="text-[10px] text-neutral-500 font-medium">
                Integrated Career Intelligence Platform
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-2 text-neutral-400 font-medium text-xs bg-neutral-900/80 px-3.5 py-1.5 rounded-xl border border-neutral-800">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Hiring Market: India</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area: Explicit top spacing derived from 64px header height + padding */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-6 sm:pt-8 pb-16 space-y-10">
        {/* Hero Banner */}
        <section aria-label="Welcome and Overview" className="scroll-mt-20 relative rounded-3xl overflow-hidden p-8 sm:p-10 border border-neutral-800/90 bg-gradient-to-br from-neutral-900/90 via-neutral-950/80 to-neutral-900/50 shadow-2xl">
          <div className="absolute top-0 right-0 -mt-8 -mr-8 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-1/3 -mb-8 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10 max-w-3xl space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-neutral-800/80 border border-neutral-700/60 text-neutral-300 text-xs font-medium">
              <Award className="h-3.5 w-3.5 text-emerald-400" />
              <span>Career Intelligence & Skill Verification</span>
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white leading-tight">
              Evidence-Based Skill-Gap & Career Roadmap
            </h1>
            <p className="text-sm sm:text-base text-neutral-400 leading-relaxed max-w-2xl">
              SkillForge AI bridges candidate resumes, verifiable GitHub repository artifacts, and empirical industry market demand to prioritize actionable career growth areas for your target role.
            </p>

            {/* Candidate Workflow Steps */}
            <div className="pt-2 flex flex-wrap items-center gap-2 text-[11px] font-mono text-neutral-400">
              <span className="px-2.5 py-1 rounded-md bg-neutral-900 border border-neutral-800 flex items-center gap-1.5">
                <CheckCircle2 className="h-3 w-3 text-emerald-400" /> 1. Target Role & Evidence
              </span>
              <span className="text-neutral-600">→</span>
              <span className="px-2.5 py-1 rounded-md bg-neutral-900 border border-neutral-800 flex items-center gap-1.5">
                <TrendingUp className="h-3 w-3 text-emerald-400" /> 2. Industry Demand Benchmark
              </span>
              <span className="text-neutral-600">→</span>
              <span className="px-2.5 py-1 rounded-md bg-neutral-900 border border-neutral-800 flex items-center gap-1.5">
                <Compass className="h-3 w-3 text-emerald-400" /> 3. Verified Skills & Gaps
              </span>
              <span className="text-neutral-600">→</span>
              <span className="px-2.5 py-1 rounded-md bg-neutral-900 border border-neutral-800 flex items-center gap-1.5">
                <Award className="h-3 w-3 text-emerald-400" /> 4. Priority Roadmap
              </span>
              <span className="text-neutral-600">→</span>
              <span className="px-2.5 py-1 rounded-md bg-neutral-900 border border-neutral-800 flex items-center gap-1.5">
                <Bot className="h-3 w-3 text-purple-400" /> 5. AI Career Assistant
              </span>
            </div>
          </div>
        </section>

        {/* 1. Target Role & Candidate Profile Evidence Section */}
        <section aria-label="Candidate Profile and Evidence Sources" className="scroll-mt-20 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold text-neutral-100 tracking-tight">
                Candidate Profile & Evidence
              </h2>
              <p className="text-xs text-neutral-400 mt-0.5">
                Select your target career track and provide resume or code repository evidence
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2.5 py-1 rounded-lg border font-medium ${
                candidateReady
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  : "bg-amber-500/10 text-amber-400 border-amber-500/20"
              }`}>
                {candidateReady ? "Candidate Profile Active" : "Profile Setup Required"}
              </span>
            </div>
          </div>

          <div className="space-y-6">
            <TargetRoleSelector selectedRoleId={selectedRoleId} onSelectRole={setSelectedRoleId} />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ResumeUploadPlaceholder onResumeChange={handleResumeChange} />
              <GitHubConnectPlaceholder onGitHubChange={handleGitHubChange} />
            </div>
          </div>
        </section>

        {/* 2. Industry Demand Benchmark */}
        <section aria-label="Industry Skill Demand Benchmark" className="scroll-mt-20">
          <MarketDemandSection
            selectedRoleId={selectedRoleId}
            onSelectRole={setSelectedRoleId}
          />
        </section>

        {/* 3. Core Skill Gap & Actionable Priorities */}
        <section aria-label="Skill Gap & Priorities" className="scroll-mt-20">
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

        {/* 4. Personalized Career Roadmap */}
        <section aria-label="Personalized Career Roadmap" className="scroll-mt-20">
          <RoadmapSection
            selectedRoleId={selectedRoleId}
            candidateReady={candidateReady}
            hasResume={hasResume}
            resumeId={resumeId}
            connectedGitHubUsername={connectedGitHubUser}
          />
        </section>

        {/* 5. AI Career Intelligence Assistant */}
        <section aria-label="AI Career Intelligence Assistant" className="scroll-mt-20">
          <CareerAssistant
            selectedRoleId={selectedRoleId}
            candidateReady={candidateReady}
            hasResume={hasResume}
            resumeId={resumeId}
            connectedGitHubUsername={connectedGitHubUser}
          />
        </section>

        {/* 6. Cross-Role Career Intelligence */}
        <section aria-label="Career Demand Intelligence Explorer" className="scroll-mt-20">
          <DemandIntelligenceExplorer />
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-neutral-800/80 bg-neutral-950/90 py-6 text-xs text-neutral-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-neutral-400">SkillForge AI</span>
            <span>•</span>
            <span>Smart India Hackathon Project</span>
            <span>•</span>
            <span>Evidence-Based Career Intelligence</span>
          </div>
          <div className="text-neutral-500 text-[11px]">
            Empirical skill gap analysis evaluated deterministically from verified candidate and market records.
          </div>
        </div>
      </footer>
    </div>
  );
}
