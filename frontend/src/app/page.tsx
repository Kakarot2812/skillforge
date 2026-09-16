"use client";

import React, { useState } from "react";
import { Navbar } from "@/components/navigation/Navbar";
import { HomeView } from "@/components/home/HomeView";
import { AnalyzerView } from "@/components/analyzer/AnalyzerView";
import { DashboardView } from "@/components/dashboard/DashboardView";

export default function MainPage() {
  const [activeTab, setActiveTab] = useState<"home" | "analyzer" | "dashboard">("home");

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col selection:bg-accent/20 selection:text-foreground transition-colors duration-200">
      {/* Dynamic Navigation Bar */}
      <Navbar activeTab={activeTab} onSelectTab={setActiveTab} />

      {/* Dynamic Content Views */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-16">
        {activeTab === "home" && <HomeView onNavigate={setActiveTab} />}
        {activeTab === "analyzer" && <AnalyzerView onNavigate={setActiveTab} />}
        {activeTab === "dashboard" && <DashboardView onNavigate={setActiveTab} />}
      </main>

      {/* Clean Global Footer */}
      <footer className="border-t border-border bg-surface/70 py-6 text-xs text-muted transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-foreground">SkillForge AI</span>
            <span>•</span>
            <span>Deterministic Career Intelligence Platform</span>
          </div>
          <div className="text-muted text-[11px]">
            Empirical skill gap analysis evaluated deterministically from verified candidate and market records.
          </div>
        </div>
      </footer>
    </div>
  );
}
