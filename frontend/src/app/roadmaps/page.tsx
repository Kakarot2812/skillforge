"use client";

import React from "react";
import { Navbar } from "@/components/navigation/Navbar";
import { RoadmapsView } from "@/components/roadmap/static";

export default function RoadmapsPage() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col selection:bg-accent/20 selection:text-foreground transition-colors duration-200">
      <Navbar activeTab="roadmaps" />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-16">
        <RoadmapsView />
      </main>

      <footer className="border-t border-border bg-surface/70 py-6 text-xs text-muted transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-foreground">SkillForge AI</span>
            <span>•</span>
            <span>Curated Career Skill Roadmaps</span>
          </div>
          <div className="text-muted text-[11px]">
            Comprehensive learning paths, verified documentation, and structured practice challenges across 12 domains.
          </div>
        </div>
      </footer>
    </div>
  );
}
