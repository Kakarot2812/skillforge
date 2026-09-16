"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  TrendingUp,
  BarChart3,
  Flame,
  ArrowRight,
  Briefcase,
  AlertCircle,
  RefreshCw,
  X,
  Layers,
  Sparkles,
} from "lucide-react";
import {
  fetchRoles,
  fetchRoleDemand,
  fetchRoleMarketSignals,
  JobRole,
  RoleDemandDetailData,
  RoleDemandDetailResponse,
  RoleMarketSignalsResponse,
} from "@/lib/api";

export interface CompleteIndustryData {
  role: JobRole;
  demand?: RoleDemandDetailData;
  meta?: RoleDemandDetailResponse["meta"];
  signals?: RoleMarketSignalsResponse["data"];
}

export const IndustrySkillsDemand: React.FC = () => {
  const [industries, setIndustries] = useState<CompleteIndustryData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Selected industry for detailed view modal
  const [activeModalIndustry, setActiveModalIndustry] = useState<CompleteIndustryData | null>(null);

  // Fetch all industries and their respective demand data concurrently from existing backend
  const loadAllIndustriesData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      // 1. Fetch canonical job roles from GET /api/v1/roles
      const rolesRes = await fetchRoles(undefined, 50, 0);
      if (!rolesRes.success || !rolesRes.data?.data || rolesRes.data.data.length === 0) {
        setErrorMessage(rolesRes.error || "No industry market records found in backend.");
        setIsLoading(false);
        return;
      }

      const canonicalRoles = rolesRes.data.data;

      // 2. Concurrently fetch demand breakdown and market signals for ALL industries
      const industryPromises = canonicalRoles.map(async (role) => {
        try {
          const [demandRes, signalsRes] = await Promise.all([
            fetchRoleDemand(role.role_id),
            fetchRoleMarketSignals(role.role_id),
          ]);

          return {
            role,
            demand: demandRes.success ? demandRes.data : undefined,
            meta: demandRes.success ? demandRes.meta : undefined,
            signals: signalsRes.success ? signalsRes.data : undefined,
          } as CompleteIndustryData;
        } catch {
          return {
            role,
          } as CompleteIndustryData;
        }
      });

      const loadedIndustries = await Promise.all(industryPromises);
      setIndustries(loadedIndustries);
    } catch {
      setErrorMessage("Unable to load industry market data. Please verify backend connection.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let isCancelled = false;
    Promise.resolve().then(() => {
      if (!isCancelled) {
        loadAllIndustriesData();
      }
    });
    return () => {
      isCancelled = true;
    };
  }, [loadAllIndustriesData]);

  // Keyboard escape listener to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setActiveModalIndustry(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Compute market summary stats directly from real backend numbers
  const marketSummary = useMemo(() => {
    if (industries.length === 0) return null;

    let totalDemandScoreSum = 0;
    let scoredIndustriesCount = 0;
    let highestDemandRoleTitle = "";
    let highestDemandScore = -1;
    let fastestGrowingRoleTitle = "";
    let highestGrowthRate = -999;
    const skillSet = new Set<string>();

    industries.forEach(({ role, meta, demand }) => {
      if (meta?.average_demand_score !== undefined) {
        totalDemandScoreSum += meta.average_demand_score;
        scoredIndustriesCount += 1;

        if (meta.average_demand_score > highestDemandScore) {
          highestDemandScore = meta.average_demand_score;
          highestDemandRoleTitle = role.title;
        }
      }

      if (meta?.average_growth_rate !== undefined) {
        if (meta.average_growth_rate > highestGrowthRate) {
          highestGrowthRate = meta.average_growth_rate;
          fastestGrowingRoleTitle = role.title;
        }
      }

      if (demand?.skills) {
        demand.skills.forEach((s) => skillSet.add(s.skill_name));
      }
    });

    const marketAvgScore =
      scoredIndustriesCount > 0 ? totalDemandScoreSum / scoredIndustriesCount : 0;

    return {
      totalIndustries: industries.length,
      marketAvgScore: marketAvgScore.toFixed(1),
      highestDemandRoleTitle: highestDemandRoleTitle || "N/A",
      highestDemandScore: highestDemandScore > 0 ? highestDemandScore.toFixed(1) : "N/A",
      fastestGrowingRoleTitle: fastestGrowingRoleTitle || "N/A",
      highestGrowthRate: highestGrowthRate > -999 ? `+${highestGrowthRate.toFixed(1)}%` : "N/A",
      totalUniqueSkillsCount: skillSet.size,
      location: industries[0]?.meta?.location || "India",
      dataFreshness: industries[0]?.meta?.data_freshness || "2026-09-01",
    };
  }, [industries]);

  return (
    <section
      aria-label="Industry Skills Demand"
      className="editorial-card p-6 sm:p-8 lg:p-10 relative select-none transition-colors duration-200"
    >
      {/* 1. SECTION HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-4 pb-5 border-b border-border">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2 text-[11px] font-mono text-muted uppercase tracking-widest">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            <span>Market Intelligence Index</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
            Industry Skills Demand
          </h2>
          <p className="text-xs sm:text-sm text-muted max-w-xl">
            Empirical demand benchmarks, skill requirements, and YoY hiring trends across job roles.
          </p>
        </div>

        {marketSummary && (
          <div className="flex items-center gap-2 text-[11px] font-mono text-muted bg-surface-subtle px-3 py-1.5 rounded-md border border-border shrink-0 self-start sm:self-auto">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            <span>Market: {marketSummary.location}</span>
            <span className="text-subtle">•</span>
            <span>{marketSummary.dataFreshness}</span>
          </div>
        )}
      </div>

      {/* ERROR STATE */}
      {errorMessage && (
        <div
          role="alert"
          className="p-4 rounded-md bg-danger-subtle border border-danger/30 flex items-start gap-3 text-xs text-danger"
        >
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <div className="space-y-1.5 flex-1">
            <div className="font-semibold">{errorMessage}</div>
            <button
              type="button"
              onClick={loadAllIndustriesData}
              className="editorial-btn-secondary !py-1 !px-2.5 !text-xs !rounded-md flex items-center gap-1.5 cursor-pointer"
            >
              <RefreshCw className="h-3 w-3" />
              <span>Retry</span>
            </button>
          </div>
        </div>
      )}

      {/* 2. ANALYTICS METRICS STRIP (LARGE NUMBERS + THIN DIVIDERS) */}
      {isLoading ? (
        <div className="border-y border-border py-6 my-6">
          <div className="grid grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-border">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="p-4 sm:p-6 text-center space-y-2 animate-pulse">
                <div className="h-3 bg-surface-subtle rounded w-20 mx-auto" />
                <div className="h-7 bg-surface-subtle rounded w-16 mx-auto" />
              </div>
            ))}
          </div>
        </div>
      ) : marketSummary ? (
        <div className="border-y border-border py-6 my-6">
          <div className="grid grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-border">
            <div className="p-4 sm:p-6 text-center space-y-1">
              <span className="text-[11px] font-mono uppercase tracking-widest text-muted">
                Industry Tracks
              </span>
              <div className="text-2xl sm:text-3xl font-bold font-mono text-foreground">
                {marketSummary.totalIndustries}
              </div>
              <p className="text-[11px] text-subtle font-normal">Active market verticals</p>
            </div>

            <div className="p-4 sm:p-6 text-center space-y-1">
              <span className="text-[11px] font-mono uppercase tracking-widest text-muted">
                Market Avg Demand
              </span>
              <div className="text-2xl sm:text-3xl font-bold font-mono text-foreground">
                {marketSummary.marketAvgScore}
                <span className="text-xs font-normal text-muted ml-1">/ 100</span>
              </div>
              <p className="text-[11px] text-subtle font-normal">Composite demand score</p>
            </div>

            <div className="p-4 sm:p-6 text-center space-y-1">
              <span className="text-[11px] font-mono uppercase tracking-widest text-muted">
                Peak Demand Track
              </span>
              <div className="text-lg sm:text-xl font-bold font-mono text-accent truncate">
                {marketSummary.highestDemandRoleTitle}
              </div>
              <p className="text-[11px] text-subtle font-normal">Highest employer volume</p>
            </div>

            <div className="p-4 sm:p-6 text-center space-y-1">
              <span className="text-[11px] font-mono uppercase tracking-widest text-muted">
                Top YoY Growth
              </span>
              <div className="text-2xl sm:text-3xl font-bold font-mono text-accent">
                {marketSummary.highestGrowthRate}
              </div>
              <p className="text-[11px] text-subtle font-normal">Annual expansion rate</p>
            </div>
          </div>
        </div>
      ) : null}

      {/* 3. CLEAN DATA-DRIVEN TABLE */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-14 rounded-md bg-surface-subtle border border-border animate-pulse" />
            ))}
          </div>
        ) : industries.length > 0 ? (
          <div className="border border-border rounded-md overflow-hidden bg-surface">
            {/* Desktop Table Header */}
            <div className="hidden md:grid grid-cols-12 gap-4 px-5 py-3 bg-surface-subtle border-b border-border text-[11px] font-mono font-semibold text-muted uppercase tracking-wider">
              <div className="col-span-3">Industry Track</div>
              <div className="col-span-2">Demand Level</div>
              <div className="col-span-4">Top Skills</div>
              <div className="col-span-2 text-right">YoY Growth</div>
              <div className="col-span-1 text-right">Action</div>
            </div>

            {/* Table Rows */}
            <div className="divide-y divide-border">
              {industries.map((item) => {
                const { role, demand, meta } = item;
                const avgScore = meta?.average_demand_score;
                const growthRate = meta?.average_growth_rate;
                const skills = demand?.skills || [];
                const topSkillsList = skills.slice(0, 3).map((s) => s.skill_name);

                const demandLevel =
                  avgScore !== undefined
                    ? avgScore >= 80
                      ? { label: "HIGH", color: "text-accent border-accent/40 bg-accent/5" }
                      : avgScore >= 65
                      ? { label: "MODERATE", color: "text-foreground border-border bg-surface-subtle" }
                      : { label: "STABLE", color: "text-muted border-border bg-surface-subtle" }
                    : { label: "ACTIVE", color: "text-muted border-border bg-surface-subtle" };

                return (
                  <div
                    key={role.role_id}
                    onClick={() => setActiveModalIndustry(item)}
                    className="p-4 sm:px-5 sm:py-3.5 hover:bg-surface-subtle transition-colors cursor-pointer group flex flex-col md:grid md:grid-cols-12 gap-3 md:gap-4 items-start md:items-center"
                  >
                    {/* Column 1: Industry Track Title & Category */}
                    <div className="md:col-span-3 space-y-0.5">
                      <div className="text-sm font-bold text-foreground group-hover:text-accent transition-colors flex items-center gap-2">
                        <span>{role.title}</span>
                      </div>
                      {role.category && (
                        <div className="text-[11px] text-muted font-mono">
                          {role.category}
                        </div>
                      )}
                    </div>

                    {/* Column 2: Demand Level & Score */}
                    <div className="md:col-span-2 flex items-center gap-2">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded-sm font-bold border ${demandLevel.color}`}>
                        {demandLevel.label}
                      </span>
                      {avgScore !== undefined && (
                        <span className="text-xs font-mono text-muted font-semibold">
                          {avgScore.toFixed(0)}
                        </span>
                      )}
                    </div>

                    {/* Column 3: Top Skills */}
                    <div className="md:col-span-4 text-xs text-foreground flex flex-wrap items-center gap-1.5">
                      {topSkillsList.length > 0 ? (
                        topSkillsList.map((skill, idx) => (
                          <span
                            key={skill}
                            className="inline-flex items-center text-[11px] px-2 py-0.5 rounded-sm bg-surface-subtle border border-border text-foreground font-mono"
                          >
                            {skill}
                            {idx < topSkillsList.length - 1 && <span className="ml-1.5 text-subtle">·</span>}
                          </span>
                        ))
                      ) : (
                        <span className="text-muted text-xs">Tracking live skills</span>
                      )}
                    </div>

                    {/* Column 4: YoY Growth */}
                    <div className="md:col-span-2 md:text-right font-mono text-xs">
                      {growthRate !== undefined ? (
                        <span className="text-accent font-semibold">
                          +{growthRate.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-muted">N/A</span>
                      )}
                    </div>

                    {/* Column 5: Action */}
                    <div className="md:col-span-1 md:text-right w-full md:w-auto pt-2 md:pt-0 border-t md:border-0 border-border flex justify-end">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveModalIndustry(item);
                        }}
                        className="text-xs text-muted group-hover:text-accent font-mono flex items-center gap-1 cursor-pointer transition-colors"
                      >
                        <span className="md:hidden">View Details</span>
                        <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 transition-transform" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-muted font-mono">
            No industry records found in backend.
          </div>
        )}
      </div>

      {/* 4. DETAILED INDUSTRY MODAL (DISPLAYING ONLY REAL BACKEND FIELDS) */}
      {activeModalIndustry && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-150"
        >
          <div className="editorial-card w-full max-w-xl max-h-[85vh] overflow-y-auto p-6 sm:p-7 bg-surface border border-border rounded-md shadow-2xl space-y-5 text-foreground">
            {/* Modal Header */}
            <div className="flex items-start justify-between gap-4 pb-4 border-b border-border">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-sm bg-surface-subtle text-foreground border border-border font-bold">
                    {activeModalIndustry.role.category || "Industry Track"}
                  </span>
                  <span className="text-[11px] text-muted font-mono">
                    Market: {activeModalIndustry.meta?.location || "India"}
                  </span>
                </div>
                <h3 className="text-lg sm:text-xl font-bold text-foreground">
                  {activeModalIndustry.role.title}
                </h3>
                {activeModalIndustry.role.description && (
                  <p className="text-xs text-muted leading-relaxed">
                    {activeModalIndustry.role.description}
                  </p>
                )}
              </div>

              <button
                type="button"
                onClick={() => setActiveModalIndustry(null)}
                className="p-1.5 rounded-md hover:bg-surface-subtle text-muted hover:text-foreground transition-colors cursor-pointer shrink-0"
                aria-label="Close dialog"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Key Backend Metrics (Minimal Strip) */}
            {activeModalIndustry.meta && (
              <div className="grid grid-cols-2 sm:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-border border border-border rounded-md bg-surface-subtle">
                <div className="p-3 text-center">
                  <div className="text-[10px] font-mono uppercase text-muted">Demand Score</div>
                  <div className="text-sm font-bold text-foreground font-mono mt-0.5">
                    {activeModalIndustry.meta.average_demand_score?.toFixed(1) || "N/A"}
                  </div>
                </div>

                <div className="p-3 text-center">
                  <div className="text-[10px] font-mono uppercase text-muted">YoY Growth</div>
                  <div className="text-sm font-bold text-accent font-mono mt-0.5">
                    +{activeModalIndustry.meta.average_growth_rate?.toFixed(1) || "0"}%
                  </div>
                </div>

                <div className="p-3 text-center">
                  <div className="text-[10px] font-mono uppercase text-muted">Top Skill</div>
                  <div className="text-xs font-bold text-foreground truncate mt-0.5">
                    {activeModalIndustry.meta.top_skill || "N/A"}
                  </div>
                </div>

                <div className="p-3 text-center">
                  <div className="text-[10px] font-mono uppercase text-muted">Skills Count</div>
                  <div className="text-sm font-bold text-foreground font-mono mt-0.5">
                    {activeModalIndustry.meta.total_demanded_skills || activeModalIndustry.demand?.skills.length || 0}
                  </div>
                </div>
              </div>
            )}

            {/* Skill Demand Visualization (Ranking / Score Bars) */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between text-xs font-semibold text-foreground">
                <span>Top Demanded Skills</span>
                <span className="text-[10px] font-mono text-muted">
                  Relative Demand Score
                </span>
              </div>

              {activeModalIndustry.demand?.skills && activeModalIndustry.demand.skills.length > 0 ? (
                <div className="max-h-56 overflow-y-auto rounded-md border border-border bg-surface-subtle p-3 space-y-2.5 text-xs">
                  {activeModalIndustry.demand.skills.map((s, idx) => (
                    <div key={s.skill_id} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono text-muted">
                            #{idx + 1}
                          </span>
                          <span className="font-semibold text-foreground">
                            {s.skill_name}
                          </span>
                          {s.category && (
                            <span className="text-[10px] font-mono text-muted">
                              • {s.category}
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-3 font-mono text-[11px]">
                          <span className="text-accent font-semibold">
                            +{s.growth_rate.toFixed(1)}%
                          </span>
                          <span className="font-bold text-foreground w-8 text-right">
                            {s.demand_score.toFixed(0)}
                          </span>
                        </div>
                      </div>

                      {/* Hairline Demand Proportion Bar */}
                      <div className="w-full h-1 bg-border overflow-hidden rounded-none">
                        <div
                          className="h-full bg-accent transition-all duration-300"
                          style={{ width: `${Math.min(Math.max(s.demand_score, 10), 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-4 text-center text-xs text-muted font-mono">
                  No individual skill records returned.
                </div>
              )}
            </div>

            {/* Trajectory Signals (if available from backend) */}
            {activeModalIndustry.signals?.fastest_growing_skills && activeModalIndustry.signals.fastest_growing_skills.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-border">
                <div className="text-xs font-semibold text-foreground flex items-center gap-1.5 font-mono uppercase tracking-wider">
                  <Sparkles className="h-3.5 w-3.5 text-accent" />
                  <span>Fastest Growing Skills</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {activeModalIndustry.signals.fastest_growing_skills.slice(0, 4).map((s) => (
                    <div
                      key={s.skill_id}
                      className="p-2 rounded-sm bg-surface border border-border flex items-center justify-between text-xs"
                    >
                      <span className="text-foreground font-medium">{s.skill_name}</span>
                      <span className="font-mono text-accent font-bold text-[11px]">
                        +{s.growth_rate.toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Modal Close CTA */}
            <div className="pt-1">
              <button
                type="button"
                onClick={() => setActiveModalIndustry(null)}
                className="editorial-btn-secondary w-full !py-2 !rounded-md text-xs font-mono uppercase tracking-wider cursor-pointer"
              >
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
