"use client";

import React from "react";
import { Navbar } from "@/components/navigation/Navbar";
import { DashboardView } from "@/components/dashboard/DashboardView";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-[#0a0a0c] text-neutral-100 flex flex-col selection:bg-emerald-500/30 selection:text-emerald-200">
      <Navbar activeTab="dashboard" />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-16">
        <DashboardView />
      </main>

      <footer className="border-t border-neutral-800/80 bg-neutral-950/90 py-6 text-xs text-neutral-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-neutral-400">SkillForge AI</span>
            <span>•</span>
            <span>Career Roadmap Dashboard</span>
          </div>
          <div className="text-neutral-500 text-[11px]">
            Empirical skill gap analysis evaluated deterministically from verified candidate and market records.
          </div>
        </div>
      </footer>
    </div>
  );
}
