"use client";

import React, { useState } from "react";
import { Navbar } from "@/components/navigation/Navbar";
import { HomeView } from "@/components/home/HomeView";
import { AnalyzerView } from "@/components/analyzer/AnalyzerView";
import { DashboardView } from "@/components/dashboard/DashboardView";

export default function MainPage() {
  const [activeTab, setActiveTab] = useState<"home" | "analyzer" | "dashboard">("home");

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0a0a0c] text-neutral-900 dark:text-neutral-100 flex flex-col selection:bg-emerald-500/30 selection:text-emerald-800 dark:selection:text-emerald-200 transition-colors duration-200">
      {/* Dynamic Navigation Bar */}
      <Navbar activeTab={activeTab} onSelectTab={setActiveTab} />

      {/* Dynamic Content Views */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-16">
        {activeTab === "home" && <HomeView onNavigate={setActiveTab} />}
        {activeTab === "analyzer" && <AnalyzerView onNavigate={setActiveTab} />}
        {activeTab === "dashboard" && <DashboardView onNavigate={setActiveTab} />}
      </main>

      {/* Clean Global Footer */}
      <footer className="border-t border-neutral-200 dark:border-neutral-800/80 bg-white/80 dark:bg-neutral-950/90 py-6 text-xs text-neutral-500 dark:text-neutral-400 transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-neutral-800 dark:text-neutral-300">SkillForge AI</span>
            <span>•</span>
            <span>Deterministic Career Intelligence Platform</span>
          </div>
          <div className="text-neutral-500 dark:text-neutral-400 text-[11px]">
            Empirical skill gap analysis evaluated deterministically from verified candidate and market records.
          </div>
        </div>
      </footer>
    </div>
  );
}
