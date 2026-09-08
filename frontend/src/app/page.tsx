"use client";

import React, { useState } from "react";
import ConnectionStatus from "@/components/ConnectionStatus";
import TargetRoleSelector from "@/components/TargetRoleSelector";
import ResumeUploadPlaceholder from "@/components/ResumeUploadPlaceholder";
import GitHubConnectPlaceholder from "@/components/GitHubConnectPlaceholder";
import SkillGapExplorer from "@/components/SkillGapExplorer";
import IndustryDemandExplorer from "@/components/IndustryDemandExplorer";
import DemandIntelligenceExplorer from "@/components/DemandIntelligenceExplorer";
import { Sparkles, Terminal, BookOpen, GitPullRequest, Layers, CheckCircle2 } from "lucide-react";

export default function DashboardPage() {
  const [selectedRoleId, setSelectedRoleId] = useState<string>("");
  const [hasResume, setHasResume] = useState<boolean>(false);
  const [resumeFileName, setResumeFileName] = useState<string | null>(null);
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [connectedGitHubUser, setConnectedGitHubUser] = useState<string | null>(null);

  // Sync client-side state on mount from local storage
  React.useEffect(() => {
    if (typeof window !== "undefined") {
      const activeResume = localStorage.getItem("skillforge_active_resume_id");
      const activeFileName = localStorage.getItem("skillforge_active_resume_filename");
      setHasResume(Boolean(activeResume));
      setResumeFileName(activeFileName || null);
      setResumeId(activeResume || null);

      const activeGitHub = localStorage.getItem("skillforge_connected_github_user");
      setConnectedGitHubUser(activeGitHub || null);
    }
  }, []);

  const candidateReady = Boolean(hasResume || connectedGitHubUser);
  return (
    <div className="min-h-screen bg-[#0a0a0c] text-neutral-100 flex flex-col selection:bg-emerald-500/30 selection:text-emerald-200">
      {/* Top Navigation Bar */}
      <header className="border-b border-neutral-800/80 bg-neutral-950/70 backdrop-blur-md sticky top-0 z-50">
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
                  MVP Complete
                </span>
              </div>
              <p className="text-[10px] text-neutral-500 font-medium">
                Integrated Career Intelligence Platform
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs">
            <div className="hidden md:flex items-center gap-2 text-neutral-400 font-mono text-[11px] bg-neutral-900/80 px-3 py-1.5 rounded-lg border border-neutral-800">
              <Terminal className="h-3.5 w-3.5 text-emerald-400" />
              <span>Next.js 14 • FastAPI • PostgreSQL • pgvector</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Hero Banner */}
        <div className="relative rounded-3xl overflow-hidden p-8 sm:p-10 border border-neutral-800/90 bg-gradient-to-br from-neutral-900/90 via-neutral-950/80 to-neutral-900/50 shadow-2xl">
          <div className="absolute top-0 right-0 -mt-8 -mr-8 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-1/3 -mb-8 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10 max-w-3xl space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-neutral-800/80 border border-neutral-700/60 text-neutral-300 text-xs font-medium">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>SIH Platform Architecture • Local Environment Active</span>
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white leading-tight">
              Evidence-Based AI Skill-Gap & Career Roadmap
            </h1>
            <p className="text-sm sm:text-base text-neutral-400 leading-relaxed max-w-2xl">
              SkillForge AI bridges the gap between candidate resumes, verifiable GitHub repository artifacts, and empirical industry market demand. Multi-source career roadmap engine operational across Phases 1–5.
            </p>

            {/* Architecture Pipeline Pills */}
            <div className="pt-2 flex flex-wrap items-center gap-2 text-[11px] font-mono text-neutral-400">
              <span className="px-2.5 py-1 rounded-md bg-neutral-900 border border-neutral-800 flex items-center gap-1.5">
                <CheckCircle2 className="h-3 w-3 text-emerald-400" /> Resume Parser
              </span>
              <span className="text-neutral-600">→</span>
              <span className="px-2.5 py-1 rounded-md bg-neutral-900 border border-neutral-800 flex items-center gap-1.5">
                <CheckCircle2 className="h-3 w-3 text-emerald-400" /> GitHub Intelligence
              </span>
              <span className="text-neutral-600">→</span>
              <span className="px-2.5 py-1 rounded-md bg-neutral-900 border border-neutral-800 flex items-center gap-1.5">
                <CheckCircle2 className="h-3 w-3 text-emerald-400" /> Demand Engine
              </span>
              <span className="text-neutral-600">→</span>
              <span className="px-2.5 py-1 rounded-md bg-neutral-900 border border-neutral-800 flex items-center gap-1.5">
                <CheckCircle2 className="h-3 w-3 text-emerald-400" /> Roadmap & Resources
              </span>
              <span className="text-neutral-600">→</span>
              <span className="px-2.5 py-1 rounded-md bg-neutral-900 border border-neutral-800 flex items-center gap-1.5">
                <CheckCircle2 className="h-3 w-3 text-emerald-400" /> Verification Loop
              </span>
            </div>
          </div>
        </div>

        {/* Live Stack Connection Monitor */}
        <section aria-label="System Diagnostics">
          <ConnectionStatus />
        </section>

        {/* Core Career Intelligence Modules */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-neutral-100 tracking-tight">
                SkillForge AI Modules
              </h2>
              <p className="text-xs text-neutral-400 mt-0.5">
                Integrated Career Intelligence Pipeline (Phases 1–5 Complete)
              </p>
            </div>
            <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20 font-semibold">
              4 Active Modules
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <TargetRoleSelector selectedRoleId={selectedRoleId} onSelectRole={setSelectedRoleId} />
            <ResumeUploadPlaceholder
              onResumeChange={(has, filename, id) => {
                setHasResume(has);
                setResumeFileName(filename || null);
                setResumeId(has ? (id || null) : null);
              }}
            />
            <GitHubConnectPlaceholder
              onGitHubChange={(username) => {
                setConnectedGitHubUser(username);
              }}
            />
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
          </div>
        </section>

        {/* Phase 4: Industry Demand Engine */}
        <section aria-label="Industry Demand Explorer">
          <IndustryDemandExplorer />
        </section>

        {/* Phase 4 Checkpoint 3: Cross-Role Demand Intelligence */}
        <section aria-label="Demand Intelligence Explorer">
          <DemandIntelligenceExplorer />
        </section>

        {/* Phase Timeline & Architecture Roadmap */}
        <section className="bg-neutral-900/40 border border-neutral-800/80 rounded-2xl p-6 backdrop-blur-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-neutral-800">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-emerald-400" />
              <h3 className="text-sm font-semibold text-neutral-200">
                MVP Implementation Phases Sequence
              </h3>
            </div>
            <span className="text-[11px] font-mono text-emerald-400 font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
              Phase 5 / 5 Complete
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2.5 pt-2 text-xs">
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
              <div className="text-[10px] font-mono text-emerald-400 uppercase font-semibold">Phase 1 (Complete)</div>
              <div className="font-semibold text-white mt-1">Foundation</div>
              <div className="text-[11px] text-emerald-400/80 mt-0.5">Next.js + FastAPI + DB</div>
            </div>

            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
              <div className="text-[10px] font-mono text-emerald-400 uppercase font-semibold">Phase 2 (Complete)</div>
              <div className="font-semibold text-white mt-1">Resume AI</div>
              <div className="text-[11px] text-emerald-400/80 mt-0.5">PDF/DOCX Extraction</div>
            </div>

            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
              <div className="text-[10px] font-mono text-emerald-400 uppercase font-semibold">Phase 3 (Complete)</div>
              <div className="font-semibold text-white mt-1">GitHub AI</div>
              <div className="text-[11px] text-emerald-400/80 mt-0.5">Manifest & Code Proof</div>
            </div>

            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
              <div className="text-[10px] font-mono text-emerald-400 uppercase font-semibold">Phase 4 (Complete)</div>
              <div className="font-semibold text-white mt-1">Demand Engine</div>
              <div className="text-[11px] text-emerald-400/80 mt-0.5">Market Job Analytics</div>
            </div>

            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
              <div className="text-[10px] font-mono text-emerald-400 uppercase font-semibold">Phase 5 (Complete)</div>
              <div className="font-semibold text-white mt-1">Gap & Priority</div>
              <div className="text-[11px] text-emerald-400/80 mt-0.5">Scoring Algorithm</div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-neutral-800/80 bg-neutral-950/90 py-6 text-xs text-neutral-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-neutral-400">SkillForge AI</span>
            <span>•</span>
            <span>Smart India Hackathon Project</span>
          </div>
          <div className="flex items-center gap-4 text-neutral-400 font-mono text-[11px]">
            <span>FastAPI: http://localhost:8000</span>
            <span>Frontend: http://localhost:3000</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
