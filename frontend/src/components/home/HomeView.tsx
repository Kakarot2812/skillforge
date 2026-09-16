"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight, TrendingUp } from "lucide-react";
import { IndustrySkillsDemand } from "@/components/market/IndustrySkillsDemand";
import { TechnicalWaveVisual } from "./TechnicalWaveVisual";

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

  const pipelineSteps = [
    {
      id: "skills",
      title: "Your Skills",
      desc: "Resume & GitHub AST Evidence",
      badge: "Ingestion",
    },
    {
      id: "analysis",
      title: "Skill Analysis",
      desc: "Verified Capability Extraction",
      badge: "Verification",
    },
    {
      id: "demand",
      title: "Industry Demand",
      desc: "Live Hiring Market Weights",
      badge: "Benchmark",
    },
    {
      id: "gap",
      title: "Skill Gap",
      desc: "Target Deficit Matrix",
      badge: "Scoring",
    },
    {
      id: "roadmap",
      title: "Career Roadmap",
      desc: "Structured Milestone DAG",
      badge: "Execution",
    },
  ];

  const workflowSteps = [
    {
      id: "connect",
      title: "Connect Evidence",
      desc: "Connect your GitHub profile and upload your resume for deterministic ingestion.",
      meta: "Resume + GitHub",
    },
    {
      id: "analyze",
      title: "Analyze Skills",
      desc: "Extract verified capabilities and project proficiencies through AST parsing.",
      meta: "Capability Extraction",
    },
    {
      id: "compare",
      title: "Compare Market",
      desc: "Benchmark verified skills against real-time industry hiring demand weights.",
      meta: "Industry Benchmark",
    },
    {
      id: "roadmap",
      title: "Build Roadmap",
      desc: "Identify priority skill deficits and follow actionable milestone roadmaps.",
      meta: "Milestone Execution",
    },
  ];

  return (
    <div className="space-y-16 sm:space-y-24 pb-20 select-none">
      {/* ========================================================================= */}
      {/* 1. HERO SECTION WITH SUBTLE TECHNICAL WAVE CONTOUR LINES */}
      {/* ========================================================================= */}
      <section className="relative min-h-[58vh] sm:min-h-[64vh] flex flex-col items-center justify-center text-center px-4 py-16 sm:py-24 overflow-hidden rounded-2xl border border-border bg-surface/70 backdrop-blur-xs transition-colors duration-200">
        {/* Subtle mathematical harmonic wave lines behind hero */}
        <TechnicalWaveVisual />

        <div className="max-w-4xl mx-auto space-y-6 relative z-10">
          {/* Subtle Category Pill */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-md border border-border bg-surface-subtle/80 text-secondary text-xs font-medium">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            <span>AI Career Intelligence Platform</span>
          </div>

          {/* Large, Bold, Clean Editorial Headline */}
          <h1 className="text-4xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tight leading-[1.06] text-foreground">
            Know Your Skill Gap.
            <span className="block text-accent font-bold tracking-tight mt-1 sm:mt-2">
              Build the Right Career.
            </span>
          </h1>

          {/* Comfortable & Readable Description */}
          <p className="text-base sm:text-lg text-secondary leading-relaxed max-w-2xl mx-auto font-normal">
            SkillForge analyzes your real skills, compares them with industry demand, and creates a practical roadmap to your target career.
          </p>

          {/* Simple Premium Action Buttons */}
          <div className="pt-4 flex flex-wrap items-center justify-center gap-3.5 sm:gap-4">
            {onNavigate ? (
              <button
                type="button"
                onClick={() => onNavigate("analyzer")}
                className="editorial-btn-primary !px-7 !py-3.5 !rounded-md shadow-xs flex items-center gap-2 group cursor-pointer"
              >
                <span>Analyze My Skills</span>
                <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
              </button>
            ) : (
              <Link
                href="/analyzer"
                className="editorial-btn-primary !px-7 !py-3.5 !rounded-md shadow-xs flex items-center gap-2 group"
              >
                <span>Analyze My Skills</span>
                <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
              </Link>
            )}

            <button
              type="button"
              onClick={scrollToIndustryDemand}
              className="editorial-btn-secondary !px-6 !py-3.5 !rounded-md flex items-center gap-2 cursor-pointer"
            >
              <TrendingUp className="h-4 w-4 text-accent" />
              <span>Explore Industry Demand</span>
            </button>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 2. INTELLIGENCE PIPELINE (CLEAN FLOW WITHOUT NUMERIC PREFIXES) */}
      {/* ========================================================================= */}
      <section className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 pb-3 border-b border-border">
          <div className="space-y-1">
            <h2 className="text-xl sm:text-2xl font-bold text-foreground">
              Intelligence Pipeline
            </h2>
            <p className="text-xs sm:text-sm text-muted">
              Automated deterministic flow from candidate evidence to validated career roadmap
            </p>
          </div>
          <div className="text-xs text-muted font-medium shrink-0">
            5-Stage Pipeline
          </div>
        </div>

        {/* Desktop 5-step horizontal flow with connecting hairlines */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 lg:gap-4 relative">
          {pipelineSteps.map((step, idx) => (
            <div
              key={step.id}
              className="editorial-card p-4 sm:p-5 flex flex-col justify-between space-y-4 relative group"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-muted font-medium px-2 py-0.5 rounded border border-border/80 bg-surface-subtle">
                    {step.badge}
                  </span>
                </div>
                <h3 className="text-sm font-semibold text-foreground">
                  {step.title}
                </h3>
                <p className="text-xs text-muted leading-relaxed">
                  {step.desc}
                </p>
              </div>

              {/* Step indicator footer */}
              <div className="pt-2.5 border-t border-border flex items-center justify-between text-xs text-subtle font-medium">
                <span>Stage</span>
                {idx < pipelineSteps.length - 1 && (
                  <span className="hidden md:inline text-muted font-bold">→</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 3. INDUSTRY SKILLS DEMAND (EXISTING DATA-DRIVEN COMPONENT) */}
      {/* ========================================================================= */}
      <div id="industry-demand-section" className="scroll-mt-20">
        <IndustrySkillsDemand />
      </div>

      {/* ========================================================================= */}
      {/* 4. HOW SKILLFORGE WORKS (4 STEPS) */}
      {/* ========================================================================= */}
      <section className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 pb-3 border-b border-border">
          <div className="space-y-1">
            <h2 className="text-xl sm:text-2xl font-bold text-foreground">
              How SkillForge Works
            </h2>
            <p className="text-xs sm:text-sm text-muted">
              A 4-step deterministic process from skill verification to career acceleration
            </p>
          </div>
          <div className="text-xs text-muted font-medium shrink-0">
            Standard Method
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {workflowSteps.map((step) => (
            <div
              key={step.id}
              className="editorial-card p-5 sm:p-6 flex flex-col justify-between space-y-4"
            >
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-foreground">
                  {step.title}
                </h3>
                <p className="text-xs text-muted leading-relaxed">
                  {step.desc}
                </p>
              </div>
              <div className="pt-3 border-t border-border text-xs text-subtle font-medium">
                {step.meta}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 5. CLEAN DIRECT CTA BANNER */}
      {/* ========================================================================= */}
      <section className="editorial-card p-6 sm:p-10 flex flex-col sm:flex-row items-center justify-between gap-6 transition-colors duration-200">
        <div className="space-y-1.5 text-center sm:text-left">
          <h3 className="text-lg sm:text-xl font-bold text-foreground">
            Ready to identify your skill gaps?
          </h3>
          <p className="text-xs sm:text-sm text-muted max-w-xl">
            Benchmark your profile against target industry roles and generate your step-by-step career roadmap.
          </p>
        </div>

        {onNavigate ? (
          <button
            type="button"
            onClick={() => onNavigate("analyzer")}
            className="editorial-btn-primary !px-6 !py-3 !rounded-md shrink-0 flex items-center gap-2 group cursor-pointer"
          >
            <span>Analyze My Skills</span>
            <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
          </button>
        ) : (
          <Link
            href="/analyzer"
            className="editorial-btn-primary !px-6 !py-3 !rounded-md shrink-0 flex items-center gap-2 group"
          >
            <span>Analyze My Skills</span>
            <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        )}
      </section>
    </div>
  );
};
