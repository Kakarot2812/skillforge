"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  TrendingUp,
  Search,
  Filter,
  ArrowUpDown,
  AlertCircle,
  BarChart3,
  RefreshCw,
} from "lucide-react";
import {
  fetchRoles,
  fetchRoleDemand,
  fetchDemandTrends,
  fetchDemandQualityAudit,
  JobRole,
  RoleSkillDemandItem,
  RoleDemandDetailResponse,
  DemandQualityAuditReport,
} from "@/lib/api";
import MarketFreshness from "./MarketFreshness";
import MarketSkillCard, { MarketSkillItemData } from "./MarketSkillCard";

export interface MarketDemandSectionProps {
  selectedRoleId?: string;
  onSelectRole?: (roleId: string) => void;
}

type TrendFilterOption = "ALL" | "RISING" | "STABLE" | "DECLINING";
type SortOption = "DEMAND_DESC" | "GROWTH_DESC" | "NAME_ASC";

export default function MarketDemandSection({
  selectedRoleId: controlledRoleId,
  onSelectRole,
}: MarketDemandSectionProps) {
  // Roles state
  const [roles, setRoles] = useState<JobRole[]>([]);
  const [internalRoleId, setInternalRoleId] = useState<string>("");
  const [loadingRoles, setLoadingRoles] = useState<boolean>(true);

  // Demand data state
  const [demandedSkills, setDemandedSkills] = useState<RoleSkillDemandItem[]>([]);
  const [trendsMap, setTrendsMap] = useState<Map<string, "RISING" | "STABLE" | "DECLINING">>(new Map());
  const [demandMeta, setDemandMeta] = useState<RoleDemandDetailResponse["meta"] | null>(null);
  const [auditReport, setAuditReport] = useState<DemandQualityAuditReport | null>(null);
  const [loadingDemand, setLoadingDemand] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filter and search state
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [trendFilter, setTrendFilter] = useState<TrendFilterOption>("ALL");
  const [sortBy, setSortBy] = useState<SortOption>("DEMAND_DESC");

  // Effective selected role ID (controlled from props if available)
  const activeRoleId = controlledRoleId || internalRoleId;

  const handleRoleChange = (newRoleId: string) => {
    setInternalRoleId(newRoleId);
    if (onSelectRole) {
      onSelectRole(newRoleId);
    }
  };

  // 1. Load canonical roles on mount
  useEffect(() => {
    let isCancelled = false;
    Promise.resolve().then(async () => {
      setLoadingRoles(true);
      try {
        const [rolesRes, auditRes] = await Promise.allSettled([
          fetchRoles(),
          fetchDemandQualityAudit(),
        ]);

        if (rolesRes.status === "fulfilled" && rolesRes.value.success && rolesRes.value.data?.data) {
          if (!isCancelled) {
            const roleList = rolesRes.value.data.data;
            setRoles(roleList);
            if (!activeRoleId && roleList.length > 0) {
              const defaultRole =
                roleList.find((r) => r.slug === "backend-engineer") || roleList[0];
              setInternalRoleId(defaultRole.role_id);
              if (onSelectRole) {
                onSelectRole(defaultRole.role_id);
              }
            }
          }
        }

        if (auditRes.status === "fulfilled" && auditRes.value.success && auditRes.value.data) {
          if (!isCancelled) {
            setAuditReport(auditRes.value.data);
          }
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          setError(err instanceof Error ? err.message : "Failed to load roles.");
        }
      } finally {
        if (!isCancelled) {
          setLoadingRoles(false);
        }
      }
    });

    return () => {
      isCancelled = true;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 2. Fetch role demand and trends when active role changes
  const loadRoleDemandData = useCallback(async (roleId: string) => {
    if (!roleId) return;
    setLoadingDemand(true);
    setError(null);

    try {
      const [demandRes, trendsRes] = await Promise.allSettled([
        fetchRoleDemand(roleId, "India"),
        fetchDemandTrends("India", roleId, 100, 0),
      ]);

      if (demandRes.status === "fulfilled" && demandRes.value.success && demandRes.value.data) {
        setDemandedSkills(demandRes.value.data.skills || []);
        setDemandMeta(demandRes.value.meta || null);
      } else {
        setDemandedSkills([]);
        setDemandMeta(null);
        if (demandRes.status === "fulfilled" && demandRes.value.error) {
          setError(demandRes.value.error);
        }
      }

      // Populate trends map with backend-computed classification
      if (trendsRes.status === "fulfilled" && trendsRes.value.success && trendsRes.value.data?.data) {
        const tMap = new Map<string, "RISING" | "STABLE" | "DECLINING">();
        trendsRes.value.data.data.forEach((item) => {
          tMap.set(item.skill_id, item.trend);
        });
        setTrendsMap(tMap);
      } else {
        setTrendsMap(new Map());
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load market demand data.");
    } finally {
      setLoadingDemand(false);
    }
  }, []);

  useEffect(() => {
    let isCancelled = false;
    if (activeRoleId) {
      Promise.resolve().then(() => {
        if (!isCancelled) {
          loadRoleDemandData(activeRoleId);
        }
      });
    }
    return () => {
      isCancelled = true;
    };
  }, [activeRoleId, loadRoleDemandData]);

  // Selected role metadata
  const selectedRole = useMemo(() => {
    return roles.find((r) => r.role_id === activeRoleId);
  }, [roles, activeRoleId]);

  // Prepare unified skills data with trend classification
  const unifiedSkills: MarketSkillItemData[] = useMemo(() => {
    return demandedSkills.map((s) => ({
      skill_id: s.skill_id,
      skill_name: s.skill_name,
      canonical_slug: s.canonical_slug,
      category: s.category,
      demand_score: s.demand_score,
      growth_rate: s.growth_rate,
      trend: trendsMap.get(s.skill_id) || "STABLE",
      sample_size: s.sample_size,
      data_updated_at: s.data_updated_at,
    }));
  }, [demandedSkills, trendsMap]);

  // Filter and Sort skills (using direct backend values)
  const filteredSkills = useMemo(() => {
    let result = [...unifiedSkills];

    // Filter by search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (s) =>
          s.skill_name.toLowerCase().includes(q) ||
          (s.category && s.category.toLowerCase().includes(q))
      );
    }

    // Filter by growth class
    if (trendFilter !== "ALL") {
      result = result.filter((s) => s.trend === trendFilter);
    }

    // Sort strictly by backend-provided values
    result.sort((a, b) => {
      if (sortBy === "DEMAND_DESC") {
        return b.demand_score - a.demand_score;
      }
      if (sortBy === "GROWTH_DESC") {
        return b.growth_rate - a.growth_rate;
      }
      if (sortBy === "NAME_ASC") {
        return a.skill_name.localeCompare(b.skill_name);
      }
      return 0;
    });

    return result;
  }, [unifiedSkills, searchQuery, trendFilter, sortBy]);

  // Navigation callbacks
  const scrollToRoadmap = () => {
    const el = document.getElementById("career-roadmap-section");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  const scrollToAssistant = (skillName?: string) => {
    const el = document.getElementById("ai-career-assistant-section");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
      if (skillName) {
        const input = document.getElementById("assistant-query-input") as HTMLTextAreaElement;
        if (input) {
          input.value = `Why is ${skillName} in demand for my role?`;
          input.focus();
        }
      }
    }
  };

  return (
    <div id="industry-market-demand-section" className="scroll-mt-20 space-y-6">
      {/* Container Card */}
      <div className="bg-white dark:bg-neutral-900/70 border border-neutral-200 dark:border-neutral-800 rounded-3xl p-6 sm:p-8 backdrop-blur-md relative overflow-hidden shadow-md shadow-neutral-200/50 dark:shadow-2xl space-y-6 transition-colors duration-200">
        {/* Subtle Background Glow */}
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        {/* Section Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-6 border-b border-neutral-200 dark:border-neutral-800 relative z-10">
          <div className="space-y-1.5 max-w-2xl">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 shadow-inner">
                <TrendingUp className="h-5 w-5" />
              </div>
              <h2 className="text-xl font-bold text-neutral-900 dark:text-white tracking-tight">
                Industry Skill Demand Benchmark
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20 font-semibold uppercase">
                P1 Deterministic Intelligence
              </span>
            </div>
            <p className="text-xs sm:text-sm text-neutral-600 dark:text-neutral-400 leading-relaxed">
              Empirical market weights, sample-size-weighted hiring volumes, and YoY growth trajectories derived deterministically from employer job postings across India.
            </p>
          </div>

          {/* Freshness & Metadata Bar */}
          <div className="flex flex-wrap items-center gap-2">
            <MarketFreshness
              dataFreshness={demandMeta?.data_freshness}
              location={demandMeta?.location || "India"}
              auditRecordsCount={auditReport?.total_demand_records}
            />

            <button
              type="button"
              onClick={() => activeRoleId && loadRoleDemandData(activeRoleId)}
              disabled={loadingDemand || !activeRoleId}
              className="p-2 rounded-xl bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-800/80 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-white border border-neutral-200 dark:border-transparent transition-colors cursor-pointer disabled:opacity-50"
              title="Refresh market demand data"
              aria-label="Refresh market data"
            >
              <RefreshCw className={`h-4 w-4 ${loadingDemand ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Role Selection Tabs (Synchronized with Dashboard State) */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-neutral-600 dark:text-neutral-400">
            <span className="font-semibold uppercase tracking-wider text-[11px]">
              Select Target Career Track
            </span>
            <span className="text-[11px] font-mono text-indigo-600 dark:text-indigo-300 font-medium">
              Synchronized with Dashboard Role
            </span>
          </div>

          {loadingRoles ? (
            <div className="animate-pulse flex gap-2 overflow-x-auto pb-1">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-10 bg-neutral-100 dark:bg-neutral-800/60 rounded-xl w-36 shrink-0 border border-neutral-200 dark:border-transparent" />
              ))}
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {roles.map((r) => {
                const isSelected = r.role_id === activeRoleId;
                return (
                  <button
                    key={r.role_id}
                    type="button"
                    onClick={() => handleRoleChange(r.role_id)}
                    className={`px-3.5 py-2 rounded-xl text-xs font-semibold transition-all duration-150 cursor-pointer border ${
                      isSelected
                        ? "bg-indigo-600 border-indigo-500 text-white shadow-md shadow-indigo-600/20 dark:shadow-indigo-950/40"
                        : "bg-neutral-50 dark:bg-neutral-900/80 border-neutral-200 dark:border-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-900 dark:hover:text-white"
                    }`}
                  >
                    {r.title}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Selected Role Summary & Aggregates Cards */}
        {selectedRole && (
          <div className="space-y-4">
            {/* Role Header Description */}
            <div className="bg-neutral-50 dark:bg-neutral-950/60 border border-neutral-200 dark:border-neutral-800/80 rounded-2xl p-4 space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-neutral-900 dark:text-white">{selectedRole.title}</h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-neutral-200 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-400 border border-neutral-300 dark:border-neutral-700/60">
                  {selectedRole.category}
                </span>
              </div>
              {selectedRole.description && (
                <p className="text-xs text-neutral-600 dark:text-neutral-400 leading-relaxed">
                  {selectedRole.description}
                </p>
              )}
            </div>

            {/* SQL-Derived Aggregate Cards (Strictly Backend Contract) */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-2xl bg-neutral-50 dark:bg-neutral-950/70 border border-neutral-200 dark:border-neutral-800">
                <span className="text-[10px] text-neutral-500 dark:text-neutral-500 uppercase tracking-wider block">
                  Demanded Skills
                </span>
                <span className="text-lg font-mono font-bold text-neutral-900 dark:text-white mt-0.5 block">
                  {demandMeta?.total_demanded_skills ?? demandedSkills.length}
                </span>
              </div>

              <div className="p-3.5 rounded-2xl bg-neutral-50 dark:bg-neutral-950/70 border border-neutral-200 dark:border-neutral-800">
                <span className="text-[10px] text-neutral-500 dark:text-neutral-500 uppercase tracking-wider block">
                  Avg Demand Score
                </span>
                <span className="text-lg font-mono font-bold text-indigo-600 dark:text-indigo-300 mt-0.5 block">
                  {demandMeta?.average_demand_score !== undefined
                    ? `${Math.round(demandMeta.average_demand_score * 100)}%`
                    : "—"}
                </span>
              </div>

              <div className="p-3.5 rounded-2xl bg-neutral-50 dark:bg-neutral-950/70 border border-neutral-200 dark:border-neutral-800">
                <span className="text-[10px] text-neutral-500 dark:text-neutral-500 uppercase tracking-wider block">
                  Highest Demand Skill
                </span>
                <span className="text-lg font-mono font-bold text-emerald-600 dark:text-emerald-400 mt-0.5 block truncate">
                  {demandMeta?.highest_demand_score !== undefined
                    ? `${Math.round(demandMeta.highest_demand_score * 100)}%`
                    : "—"}
                  {demandMeta?.top_skill && (
                    <span className="text-xs font-normal text-neutral-500 dark:text-neutral-400 ml-1.5">
                      ({demandMeta.top_skill})
                    </span>
                  )}
                </span>
              </div>

              <div className="p-3.5 rounded-2xl bg-neutral-50 dark:bg-neutral-950/70 border border-neutral-200 dark:border-neutral-800">
                <span className="text-[10px] text-neutral-500 dark:text-neutral-500 uppercase tracking-wider block">
                  Avg YoY Growth
                </span>
                <span className="text-lg font-mono font-bold text-teal-600 dark:text-teal-300 mt-0.5 block">
                  {demandMeta?.average_growth_rate !== undefined
                    ? `${demandMeta.average_growth_rate >= 0 ? "+" : ""}${Math.round(
                        demandMeta.average_growth_rate * 100
                      )}% YoY`
                    : "—"}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Market vs. Candidate Boundary Alert (Strict Requirement 9) */}
        <div className="p-4 rounded-2xl bg-indigo-50/60 dark:bg-neutral-950/80 border border-indigo-100 dark:border-neutral-800 text-xs text-neutral-700 dark:text-neutral-400 space-y-1">
          <div className="flex items-center gap-1.5 text-neutral-900 dark:text-neutral-200 font-semibold">
            <BarChart3 className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
            <span>Market Demand Boundary Invariant:</span>
          </div>
          <p className="leading-relaxed">
            Market demand metrics reflect empirical hiring statistics across employer postings. High market demand indicates what employers are recruiting for, <strong className="text-neutral-900 dark:text-neutral-200">not whether you possess or have verified the skill</strong>. Candidate possession and gaps are evaluated separately in Section 3 and Section 4.
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-700 dark:text-rose-300 flex items-start gap-3 text-xs">
            <AlertCircle className="h-4 w-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <strong className="text-rose-800 dark:text-rose-200 font-medium">Market Data Notice:</strong>
              <p className="mt-0.5 text-neutral-600 dark:text-neutral-300">{error}</p>
            </div>
            <button
              type="button"
              onClick={() => activeRoleId && loadRoleDemandData(activeRoleId)}
              className="text-neutral-500 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-200 text-xs transition-colors cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        {/* Filter and Search Controls (Requirement 12) */}
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 pt-2">
          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <Search className="h-4 w-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-500 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search skills by name or category..."
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-white dark:bg-neutral-950 border border-neutral-200 dark:border-neutral-800 text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-500 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500/50 transition-all shadow-xs"
            />
          </div>

          {/* Controls Group: Trend Filter & Sort */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Trend Filter Tabs */}
            <div className="inline-flex rounded-xl bg-neutral-100 dark:bg-neutral-950 p-1 border border-neutral-200 dark:border-neutral-800 text-xs">
              {(["ALL", "RISING", "STABLE", "DECLINING"] as TrendFilterOption[]).map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => setTrendFilter(opt)}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all cursor-pointer ${
                    trendFilter === opt
                      ? "bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white font-semibold shadow-xs"
                      : "text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200"
                  }`}
                >
                  {opt === "ALL" ? "All" : opt.charAt(0) + opt.slice(1).toLowerCase()}
                </button>
              ))}
            </div>

            {/* Sort Dropdown */}
            <div className="relative inline-flex items-center">
              <label htmlFor="market-sort-select" className="sr-only">
                Sort Skills
              </label>
              <select
                id="market-sort-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                className="pl-3 pr-8 py-2 rounded-xl bg-white dark:bg-neutral-950 border border-neutral-200 dark:border-neutral-800 text-neutral-700 dark:text-neutral-300 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/40 cursor-pointer appearance-none shadow-xs"
              >
                <option value="DEMAND_DESC">Sort: Highest Demand</option>
                <option value="GROWTH_DESC">Sort: Fastest Growing</option>
                <option value="NAME_ASC">Sort: Name (A-Z)</option>
              </select>
              <ArrowUpDown className="h-3.5 w-3.5 absolute right-2.5 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-500 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Loading Skeletons */}
        {loadingDemand && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="p-5 rounded-2xl bg-neutral-50 dark:bg-neutral-900/40 border border-neutral-200 dark:border-neutral-800 animate-pulse space-y-3"
              >
                <div className="h-4 bg-neutral-200 dark:bg-neutral-800 rounded w-1/3" />
                <div className="h-3 bg-neutral-200/60 dark:bg-neutral-800/60 rounded w-2/3" />
                <div className="grid grid-cols-2 gap-3 pt-2">
                  <div className="h-12 bg-neutral-200/40 dark:bg-neutral-800/40 rounded-xl" />
                  <div className="h-12 bg-neutral-200/40 dark:bg-neutral-800/40 rounded-xl" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loadingDemand && filteredSkills.length === 0 && (
          <div className="py-12 text-center space-y-3 max-w-md mx-auto border border-neutral-300 dark:border-neutral-800/80 border-dashed rounded-2xl bg-neutral-50/50 dark:bg-neutral-950/40 p-6">
            <div className="h-10 w-10 rounded-xl bg-neutral-200 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 flex items-center justify-center mx-auto">
              <Filter className="h-5 w-5" />
            </div>
            <h4 className="text-sm font-bold text-neutral-900 dark:text-white">No Skills Found</h4>
            <p className="text-xs text-neutral-600 dark:text-neutral-400">
              {searchQuery || trendFilter !== "ALL"
                ? "No demanded skills match your active search or trend filter. Try resetting filters."
                : "No market demand records registered for this canonical job role."}
            </p>
            {(searchQuery || trendFilter !== "ALL") && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("");
                  setTrendFilter("ALL");
                }}
                className="px-3 py-1.5 rounded-lg bg-neutral-200 hover:bg-neutral-300 dark:bg-neutral-800 dark:hover:bg-neutral-700 text-neutral-800 dark:text-neutral-200 text-xs font-medium transition-colors cursor-pointer"
              >
                Reset Filters
              </button>
            )}
          </div>
        )}

        {/* Demanded Skills Grid */}
        {!loadingDemand && filteredSkills.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-neutral-600 dark:text-neutral-400 px-1">
              <span>
                Displaying <strong className="text-neutral-900 dark:text-white">{filteredSkills.length}</strong> Demanded Skills
              </span>
              <span className="text-[11px] font-mono text-indigo-600 dark:text-indigo-400 font-medium">
                Sorted by {sortBy === "DEMAND_DESC" ? "Demand Score" : sortBy === "GROWTH_DESC" ? "Growth Rate" : "Name"}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredSkills.map((skill) => (
                <MarketSkillCard
                  key={skill.skill_id}
                  skill={skill}
                  onExploreInRoadmap={scrollToRoadmap}
                  onAskAssistant={scrollToAssistant}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
