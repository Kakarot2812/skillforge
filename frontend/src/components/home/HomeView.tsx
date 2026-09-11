"use client";

import React from "react";
import Link from "next/link";
import {
  ArrowRight,
  TrendingUp,
  FileCode,
  Cpu,
  BarChart2,
  GitPullRequest,
  Compass,
  CheckCircle2,
} from "lucide-react";
import { IndustrySkillsDemand } from "@/components/market/IndustrySkillsDemand";

export interface HomeViewProps {
  onNavigate?: (tab: "home" | "analyzer" | "dashboard") => void;
}

export const HomeView: React.FC<HomeViewProps> = ({ onNavigate }) => {
  const scrollToIndustryDemand = () => {
    const el = document.getElementById("industry-demand-section");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="space-y-12 sm:space-y-16 pb-16">
      {/* ========================================================================= */}
      {/* 1. HERO SECTION WITH WORKFLOW PIPELINE GRAPHIC */}
      {/* ========================================================================= */}
      <section className="relative rounded-3xl overflow-hidden p-6 sm:p-10 lg:p-12 border border-neutral-800/80 bg-neutral-950/80 backdrop-blur-md shadow-xl">
        {/* Subtle ambient light */}
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none -z-10" />
        <div className="absolute bottom-0 left-1/4 w-80 h-80 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none -z-10" />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 items-center">
          {/* Left Column: Headline, Description & CTAs */}
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>AI Career Intelligence Platform</span>
            </div>

            <h1 className="text-3xl sm:text-5xl font-black tracking-tight text-white leading-[1.15]">
              Know Your Skill Gap. <br />
              <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-indigo-400 bg-clip-text text-transparent">
                Build the Right Career.
              </span>
            </h1>

            <p className="text-sm sm:text-base text-neutral-300/90 leading-relaxed max-w-xl">
              SkillForge analyzes your real skills, compares them with industry demand, and creates a practical roadmap to your target career.
            </p>

            {/* CTAs */}
            <div className="pt-2 flex flex-wrap items-center gap-3.5">
              {onNavigate ? (
                <button
                  type="button"
                  onClick={() => onNavigate("analyzer")}
                  className="px-6 py-3 rounded-xl font-semibold text-sm text-white bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-950/50 hover:shadow-emerald-900/50 transition-all flex items-center gap-2 group cursor-pointer"
                >
                  <span>Analyze My Skills</span>
                  <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
                </button>
              ) : (
                <Link
                  href="/analyzer"
                  className="px-6 py-3 rounded-xl font-semibold text-sm text-white bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-950/50 hover:shadow-emerald-900/50 transition-all flex items-center gap-2 group"
                >
                  <span>Analyze My Skills</span>
                  <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
                </Link>
              )}

              <button
                type="button"
                onClick={scrollToIndustryDemand}
                className="px-5 py-3 rounded-xl font-semibold text-sm text-neutral-300 hover:text-white bg-neutral-900 hover:bg-neutral-850 border border-neutral-800 hover:border-neutral-700 transition-all flex items-center gap-2 cursor-pointer"
              >
                <TrendingUp className="h-4 w-4 text-emerald-400" />
                <span>Explore Industry Demand</span>
              </button>
            </div>
          </div>

          {/* Right Column: Clean Visual Workflow Pipeline Graphic */}
          <div className="lg:col-span-5">
            <div className="p-5 sm:p-6 rounded-2xl bg-neutral-900/80 border border-neutral-800 shadow-inner space-y-3">
              <div className="flex items-center justify-between text-xs text-neutral-400 pb-2 border-b border-neutral-800/80">
                <span className="font-semibold text-neutral-200">Intelligence Pipeline</span>
                <span className="font-mono text-[10px] text-emerald-400">Automated Flow</span>
              </div>

              {/* Step 1: Your Skills */}
              <div className="p-3 rounded-xl bg-neutral-950/90 border border-neutral-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20 shrink-0">
                    <FileCode className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-white">YOUR SKILLS</div>
                    <div className="text-[11px] text-neutral-400">Resume &amp; GitHub AST Evidence</div>
                  </div>
                </div>
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              </div>

              {/* Arrow Connector */}
              <div className="flex justify-center -my-1 text-neutral-600">
                <span className="text-xs font-mono">↓</span>
              </div>

              {/* Step 2: Skill Analysis */}
              <div className="p-3 rounded-xl bg-neutral-950/90 border border-neutral-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-lg bg-teal-500/10 text-teal-400 flex items-center justify-center border border-teal-500/20 shrink-0">
                    <Cpu className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-white">SKILL ANALYSIS</div>
                    <div className="text-[11px] text-neutral-400">Verified Capability Extraction</div>
                  </div>
                </div>
                <div className="h-2 w-2 rounded-full bg-teal-400 animate-pulse" />
              </div>

              {/* Arrow Connector */}
              <div className="flex justify-center -my-1 text-neutral-600">
                <span className="text-xs font-mono">↓</span>
              </div>

              {/* Step 3: Industry Demand */}
              <div className="p-3 rounded-xl bg-neutral-950/90 border border-neutral-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center border border-blue-500/20 shrink-0">
                    <BarChart2 className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-white">INDUSTRY DEMAND</div>
                    <div className="text-[11px] text-neutral-400">Live Hiring Market Weights</div>
                  </div>
                </div>
                <span className="text-[10px] font-mono text-blue-400 font-bold">5 Tracks</span>
              </div>

              {/* Arrow Connector */}
              <div className="flex justify-center -my-1 text-neutral-600">
                <span className="text-xs font-mono">↓</span>
              </div>

              {/* Step 4: Skill Gap */}
              <div className="p-3 rounded-xl bg-neutral-950/90 border border-neutral-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center border border-amber-500/20 shrink-0">
                    <GitPullRequest className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-white">SKILL GAP</div>
                    <div className="text-[11px] text-neutral-400">Target Deficit Matrix</div>
                  </div>
                </div>
                <span className="text-[10px] font-mono text-amber-400 font-bold">Scored</span>
              </div>

              {/* Arrow Connector */}
              <div className="flex justify-center -my-1 text-neutral-600">
                <span className="text-xs font-mono">↓</span>
              </div>

              {/* Step 5: Career Roadmap */}
              <div className="p-3 rounded-xl bg-neutral-950/90 border border-emerald-500/30 bg-gradient-to-r from-emerald-950/30 to-neutral-950 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-lg bg-emerald-500/20 text-emerald-300 flex items-center justify-center border border-emerald-500/30 shrink-0">
                    <Compass className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-white">CAREER ROADMAP</div>
                    <div className="text-[11px] text-emerald-400">Structured Milestone DAG</div>
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 text-emerald-400 shrink-0" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 2. INDUSTRY SKILLS DEMAND (COMPACT DATA-DRIVEN COMPONENT) */}
      {/* ========================================================================= */}
      <div id="industry-demand-section">
        <IndustrySkillsDemand />
      </div>

      {/* ========================================================================= */}
      {/* 3. HOW SKILLFORGE WORKS (4 SIMPLE CONCISE STEPS) */}
      {/* ========================================================================= */}
      <section className="space-y-6">
        <div className="text-center sm:text-left space-y-1">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            How SkillForge Works
          </h2>
          <p className="text-xs sm:text-sm text-neutral-400">
            A 4-step deterministic process from skill verification to career acceleration
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Step 01 */}
          <div className="p-5 rounded-2xl bg-neutral-900/60 border border-neutral-800 hover:border-neutral-700 transition-all flex flex-col justify-between space-y-3">
            <div className="space-y-2">
              <div className="text-xs font-mono font-bold text-emerald-400">01</div>
              <h3 className="text-sm font-bold text-white">Connect Evidence</h3>
              <p className="text-xs text-neutral-400 leading-relaxed">
                Connect your GitHub profile and upload your resume for deterministic ingestion.
              </p>
            </div>
            <div className="text-[11px] font-mono text-neutral-500">Resume + GitHub</div>
          </div>

          {/* Step 02 */}
          <div className="p-5 rounded-2xl bg-neutral-900/60 border border-neutral-800 hover:border-neutral-700 transition-all flex flex-col justify-between space-y-3">
            <div className="space-y-2">
              <div className="text-xs font-mono font-bold text-teal-400">02</div>
              <h3 className="text-sm font-bold text-white">Analyze Skills</h3>
              <p className="text-xs text-neutral-400 leading-relaxed">
                Extract verified capabilities and project proficiencies through AST parsing.
              </p>
            </div>
            <div className="text-[11px] font-mono text-neutral-500">Extract capabilities</div>
          </div>

          {/* Step 03 */}
          <div className="p-5 rounded-2xl bg-neutral-900/60 border border-neutral-800 hover:border-neutral-700 transition-all flex flex-col justify-between space-y-3">
            <div className="space-y-2">
              <div className="text-xs font-mono font-bold text-blue-400">03</div>
              <h3 className="text-sm font-bold text-white">Compare Market</h3>
              <p className="text-xs text-neutral-400 leading-relaxed">
                Benchmark verified skills against real-time industry hiring demand weights.
              </p>
            </div>
            <div className="text-[11px] font-mono text-neutral-500">Industry benchmark</div>
          </div>

          {/* Step 04 */}
          <div className="p-5 rounded-2xl bg-neutral-900/60 border border-neutral-800 hover:border-neutral-700 transition-all flex flex-col justify-between space-y-3">
            <div className="space-y-2">
              <div className="text-xs font-mono font-bold text-indigo-400">04</div>
              <h3 className="text-sm font-bold text-white">Build Roadmap</h3>
              <p className="text-xs text-neutral-400 leading-relaxed">
                Identify priority skill deficits and follow actionable milestone roadmaps.
              </p>
            </div>
            <div className="text-[11px] font-mono text-neutral-500">Milestone execution</div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 4. CLEAN DIRECT CTA BANNER */}
      {/* ========================================================================= */}
      <section className="p-6 sm:p-8 rounded-2xl bg-neutral-900/80 border border-neutral-800 flex flex-col sm:flex-row items-center justify-between gap-5">
        <div className="space-y-1 text-center sm:text-left">
          <h3 className="text-base sm:text-lg font-bold text-white">
            Ready to identify your skill gaps?
          </h3>
          <p className="text-xs text-neutral-400 max-w-lg">
            Benchmark your profile against target industry roles and generate your step-by-step career roadmap.
          </p>
        </div>

        {onNavigate ? (
          <button
            type="button"
            onClick={() => onNavigate("analyzer")}
            className="px-5 py-2.5 rounded-xl font-semibold text-xs sm:text-sm text-white bg-emerald-600 hover:bg-emerald-500 shadow-md transition-all shrink-0 flex items-center gap-2 cursor-pointer"
          >
            <span>Analyze My Skills</span>
            <ArrowRight className="h-4 w-4" />
          </button>
        ) : (
          <Link
            href="/analyzer"
            className="px-5 py-2.5 rounded-xl font-semibold text-xs sm:text-sm text-white bg-emerald-600 hover:bg-emerald-500 shadow-md transition-all shrink-0 flex items-center gap-2"
          >
            <span>Analyze My Skills</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        )}
      </section>
    </div>
  );
};
