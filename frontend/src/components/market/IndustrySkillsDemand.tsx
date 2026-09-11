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
    loadAllIndustriesData();
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
      className="space-y-8 rounded-3xl p-6 sm:p-8 lg:p-10 bg-neutral-950/70 border border-neutral-800/80 shadow-xl relative select-none"
    >
      {/* 1. SECTION HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-5 border-b border-neutral-800/80">
        <div className="space-y-1.5">
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            Industry Skills Demand
          </h2>
          <p className="text-xs sm:text-sm text-neutral-400 max-w-xl">
            See which skills are most demanded across today&apos;s job market.
          </p>
        </div>

        {marketSummary && (
          <div className="flex items-center gap-2 text-[11px] font-mono text-neutral-400 bg-neutral-900/90 px-3 py-1.5 rounded-xl border border-neutral-800 shrink-0">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            <span>Market: {marketSummary.location}</span>
            <span className="text-neutral-600">•</span>
            <span>{marketSummary.dataFreshness}</span>
          </div>
        )}
      </div>

      {/* ERROR STATE */}
      {errorMessage && (
        <div
          role="alert"
          className="p-4 rounded-xl bg-rose-950/40 border border-rose-900/60 flex items-start gap-3 text-xs text-rose-300"
        >
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-400" />
          <div className="space-y-1.5 flex-1">
            <div className="font-semibold">{errorMessage}</div>
            <button
              type="button"
              onClick={loadAllIndustriesData}
              className="px-3 py-1.5 rounded-lg bg-rose-900/50 hover:bg-rose-900 text-white font-medium text-xs flex items-center gap-1.5 transition-all cursor-pointer"
            >
              <RefreshCw className="h-3 w-3" />
              <span>Retry</span>
            </button>
          </div>
        </div>
      )}

      {/* 2. COMPACT MARKET SUMMARY STATS */}
      {isLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-20 rounded-xl bg-neutral-900/70 animate-pulse border border-neutral-800" />
          ))}
        </div>
      ) : marketSummary ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="p-4 rounded-xl bg-neutral-900/50 border border-neutral-800/80 space-y-1">
            <div className="text-[11px] text-neutral-400">Industry Tracks</div>
            <div className="text-xl font-extrabold text-white">
              {marketSummary.totalIndustries} <span className="text-xs font-normal text-neutral-500">tracks</span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-neutral-900/50 border border-neutral-800/80 space-y-1">
            <div className="text-[11px] text-neutral-400">Market Avg Demand</div>
            <div className="text-xl font-extrabold text-white">
              {marketSummary.marketAvgScore} <span className="text-xs font-normal text-neutral-500">/ 100</span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-neutral-900/50 border border-neutral-800/80 space-y-1">
            <div className="text-[11px] text-neutral-400">Peak Demand Track</div>
            <div className="text-sm font-bold text-emerald-400 truncate">
              {marketSummary.highestDemandRoleTitle}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-neutral-900/50 border border-neutral-800/80 space-y-1">
            <div className="text-[11px] text-neutral-400">Top YoY Growth</div>
            <div className="text-xl font-extrabold text-emerald-400 font-mono">
              {marketSummary.highestGrowthRate}
            </div>
          </div>
        </div>
      ) : null}

      {/* 3. CLEAN DATA-DRIVEN TABLE / COMPACT GRID */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-16 rounded-xl bg-neutral-900/50 border border-neutral-800 animate-pulse" />
            ))}
          </div>
        ) : industries.length > 0 ? (
          <div className="rounded-2xl border border-neutral-800 overflow-hidden bg-neutral-900/30">
            {/* Desktop Table Header */}
            <div className="hidden md:grid grid-cols-12 gap-4 px-5 py-3 bg-neutral-900/70 border-b border-neutral-800 text-[11px] font-semibold text-neutral-400 uppercase tracking-wider">
              <div className="col-span-3">Industry Track</div>
              <div className="col-span-2">Demand Level</div>
              <div className="col-span-4">Top Skills</div>
              <div className="col-span-2 text-right">YoY Growth</div>
              <div className="col-span-1 text-right">Action</div>
            </div>

            {/* Table Rows */}
            <div className="divide-y divide-neutral-800/60">
              {industries.map((item) => {
                const { role, demand, meta } = item;
                const avgScore = meta?.average_demand_score;
                const growthRate = meta?.average_growth_rate;
                const skills = demand?.skills || [];
                const topSkillsList = skills.slice(0, 3).map((s) => s.skill_name);

                const demandLevel =
                  avgScore !== undefined
                    ? avgScore >= 80
                      ? { label: "HIGH", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" }
                      : avgScore >= 65
                      ? { label: "MODERATE", color: "text-teal-400 bg-teal-500/10 border-teal-500/20" }
                      : { label: "STABLE", color: "text-neutral-400 bg-neutral-800 border-neutral-700" }
                    : { label: "ACTIVE", color: "text-neutral-400 bg-neutral-800 border-neutral-700" };

                return (
                  <div
                    key={role.role_id}
                    onClick={() => setActiveModalIndustry(item)}
                    className="p-4 sm:px-5 sm:py-3.5 hover:bg-neutral-900/60 transition-colors cursor-pointer group flex flex-col md:grid md:grid-cols-12 gap-3 md:gap-4 items-start md:items-center"
                  >
                    {/* Column 1: Industry Track Title & Category */}
                    <div className="md:col-span-3 space-y-0.5">
                      <div className="text-sm font-bold text-white group-hover:text-emerald-300 transition-colors flex items-center gap-2">
                        <span>{role.title}</span>
                      </div>
                      {role.category && (
                        <div className="text-[11px] text-neutral-500 font-mono">
                          {role.category}
                        </div>
                      )}
                    </div>

                    {/* Column 2: Demand Level & Score */}
                    <div className="md:col-span-2 flex items-center gap-2">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded-md font-bold border ${demandLevel.color}`}>
                        {demandLevel.label}
                      </span>
                      {avgScore !== undefined && (
                        <span className="text-xs font-mono text-neutral-300 font-semibold">
                          {avgScore.toFixed(0)}
                        </span>
                      )}
                    </div>

                    {/* Column 3: Top Skills */}
                    <div className="md:col-span-4 text-xs text-neutral-300 flex flex-wrap items-center gap-1.5">
                      {topSkillsList.length > 0 ? (
                        topSkillsList.map((skill, idx) => (
                          <span
                            key={skill}
                            className="inline-flex items-center text-[11px] px-2 py-0.5 rounded-md bg-neutral-950 border border-neutral-800 text-neutral-300 font-mono"
                          >
                            {skill}
                            {idx < topSkillsList.length - 1 && <span className="ml-1.5 text-neutral-600">·</span>}
                          </span>
                        ))
                      ) : (
                        <span className="text-neutral-500 text-xs">Tracking live skills</span>
                      )}
                    </div>

                    {/* Column 4: YoY Growth */}
                    <div className="md:col-span-2 md:text-right font-mono text-xs">
                      {growthRate !== undefined ? (
                        <span className="text-emerald-400 font-semibold">
                          +{growthRate.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-neutral-500">N/A</span>
                      )}
                    </div>

                    {/* Column 5: Action */}
                    <div className="md:col-span-1 md:text-right w-full md:w-auto pt-2 md:pt-0 border-t md:border-0 border-neutral-800 flex justify-end">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveModalIndustry(item);
                        }}
                        className="text-xs text-emerald-400 group-hover:text-emerald-300 font-medium flex items-center gap-1 cursor-pointer"
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
          <div className="py-8 text-center text-xs text-neutral-500">
            No industry records found in backend.
          </div>
        )}
      </div>

      {/* 4. DETAILED INDUSTRY MODAL (DISPLAYING ONLY REAL BACKEND FIELDS) */}
      {activeModalIndustry && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150"
        >
          <div className="w-full max-w-xl max-h-[85vh] overflow-y-auto p-6 sm:p-7 bg-neutral-950 border border-neutral-800 rounded-2xl shadow-2xl space-y-5 text-neutral-100">
            {/* Modal Header */}
            <div className="flex items-start justify-between gap-4 pb-4 border-b border-neutral-800">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                    {activeModalIndustry.role.category || "Industry Track"}
                  </span>
                  <span className="text-[11px] text-neutral-400 font-mono">
                    Market: {activeModalIndustry.meta?.location || "India"}
                  </span>
                </div>
                <h3 className="text-lg sm:text-xl font-bold text-white">
                  {activeModalIndustry.role.title}
                </h3>
                {activeModalIndustry.role.description && (
                  <p className="text-xs text-neutral-400 leading-relaxed">
                    {activeModalIndustry.role.description}
                  </p>
                )}
              </div>

              <button
                type="button"
                onClick={() => setActiveModalIndustry(null)}
                className="p-1.5 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-neutral-400 hover:text-white transition-colors cursor-pointer shrink-0"
                aria-label="Close dialog"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Key Backend Metrics */}
            {activeModalIndustry.meta && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <div className="p-3 rounded-xl bg-neutral-900/60 border border-neutral-800">
                  <div className="text-[10px] text-neutral-400">Demand Score</div>
                  <div className="text-sm font-extrabold text-white font-mono mt-0.5">
                    {activeModalIndustry.meta.average_demand_score?.toFixed(1) || "N/A"}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-neutral-900/60 border border-neutral-800">
                  <div className="text-[10px] text-neutral-400">YoY Growth</div>
                  <div className="text-sm font-extrabold text-emerald-400 font-mono mt-0.5">
                    +{activeModalIndustry.meta.average_growth_rate?.toFixed(1) || "0"}%
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-neutral-900/60 border border-neutral-800">
                  <div className="text-[10px] text-neutral-400">Top Skill</div>
                  <div className="text-xs font-bold text-white truncate mt-0.5">
                    {activeModalIndustry.meta.top_skill || "N/A"}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-neutral-900/60 border border-neutral-800">
                  <div className="text-[10px] text-neutral-400">Demanded Skills</div>
                  <div className="text-sm font-extrabold text-white font-mono mt-0.5">
                    {activeModalIndustry.meta.total_demanded_skills || activeModalIndustry.demand?.skills.length || 0}
                  </div>
                </div>
              </div>
            )}

            {/* Skill Demand Visualization (Ranking / Score Bars) */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between text-xs font-semibold text-white">
                <span>Top Demanded Skills</span>
                <span className="text-[10px] font-mono text-neutral-500">
                  Relative Demand Score
                </span>
              </div>

              {activeModalIndustry.demand?.skills && activeModalIndustry.demand.skills.length > 0 ? (
                <div className="max-h-56 overflow-y-auto rounded-xl border border-neutral-800 bg-neutral-900/40 p-3 space-y-2.5 text-xs">
                  {activeModalIndustry.demand.skills.map((s, idx) => (
                    <div key={s.skill_id} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono text-neutral-500">
                            #{idx + 1}
                          </span>
                          <span className="font-semibold text-neutral-200">
                            {s.skill_name}
                          </span>
                          {s.category && (
                            <span className="text-[10px] font-mono text-neutral-500">
                              • {s.category}
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-3 font-mono text-[11px]">
                          <span className="text-emerald-400">
                            +{s.growth_rate.toFixed(1)}%
                          </span>
                          <span className="font-bold text-white w-8 text-right">
                            {s.demand_score.toFixed(0)}
                          </span>
                        </div>
                      </div>

                      {/* Visual Demand Proportion Bar */}
                      <div className="w-full h-1.5 rounded-full bg-neutral-800 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-emerald-500"
                          style={{ width: `${Math.min(Math.max(s.demand_score, 10), 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-4 text-center text-xs text-neutral-500">
                  No individual skill records returned.
                </div>
              )}
            </div>

            {/* Trajectory Signals (if available from backend) */}
            {activeModalIndustry.signals?.fastest_growing_skills && activeModalIndustry.signals.fastest_growing_skills.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-neutral-800">
                <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Fastest Growing Skills</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {activeModalIndustry.signals.fastest_growing_skills.slice(0, 4).map((s) => (
                    <div
                      key={s.skill_id}
                      className="p-2 rounded-lg bg-neutral-900/60 border border-neutral-800/80 flex items-center justify-between text-xs"
                    >
                      <span className="text-neutral-300 font-medium">{s.skill_name}</span>
                      <span className="font-mono text-emerald-400 font-bold text-[11px]">
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
                className="w-full py-2 px-4 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-white font-semibold text-xs transition-colors cursor-pointer"
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
