"use client";

import React, { useEffect, useState } from "react";
import {
  fetchRoles,
  fetchSkillDemandRanking,
  compareRoles,
  fetchRoleMarketSignals,
  fetchDemandTrends,
  JobRole,
  SkillDemandRankingItem,
  RoleCompareResponse,
  RoleMarketSignalsResponse,
  DemandTrendsResponse,
} from "../lib/api";

export default function DemandIntelligenceExplorer() {
  const [activeTab, setActiveTab] = useState<"ranking" | "compare" | "signals" | "trends">("ranking");
  const [roles, setRoles] = useState<JobRole[]>([]);
  const [loadingRoles, setLoadingRoles] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [dataFreshness, setDataFreshness] = useState<string>("2026-09-01");

  // Tab A: Rankings state
  const [rankings, setRankings] = useState<SkillDemandRankingItem[]>([]);
  const [rankingFilterRole, setRankingFilterRole] = useState<string>("");
  const [loadingRankings, setLoadingRankings] = useState<boolean>(false);

  // Tab B: Role Comparison state
  const [selectedRoleIds, setSelectedRoleIds] = useState<string[]>([]);
  const [comparisonData, setComparisonData] = useState<RoleCompareResponse["data"] | null>(null);
  const [loadingCompare, setLoadingCompare] = useState<boolean>(false);

  // Tab C: Market Signals state
  const [signalsRoleId, setSignalsRoleId] = useState<string>("");
  const [signalsData, setSignalsData] = useState<RoleMarketSignalsResponse["data"] | null>(null);
  const [loadingSignals, setLoadingSignals] = useState<boolean>(false);

  // Tab D: Trends state
  const [trends, setTrends] = useState<DemandTrendsResponse["data"]>([]);
  const [loadingTrends, setLoadingTrends] = useState<boolean>(false);

  // Load roles on mount
  useEffect(() => {
    async function loadRoles() {
      setLoadingRoles(true);
      const res = await fetchRoles();
      if (res.success && res.data?.data) {
        const rList = res.data.data;
        setRoles(rList);
        if (rList.length >= 2) {
          // Default selection for compare: first two roles
          setSelectedRoleIds([rList[0].role_id, rList[1].role_id]);
          setSignalsRoleId(rList[0].role_id);
        }
      }
      setLoadingRoles(false);
    }
    loadRoles();
  }, []);

  // Fetch rankings when tab is active or role filter changes
  useEffect(() => {
    if (activeTab !== "ranking") return;
    async function loadRankings() {
      setLoadingRankings(true);
      setError(null);
      const res = await fetchSkillDemandRanking("India", rankingFilterRole || undefined, 50, 0);
      if (res.success && res.data) {
        setRankings(res.data.data);
        if (res.data.meta?.data_freshness) {
          setDataFreshness(res.data.meta.data_freshness);
        }
      } else {
        setError(res.error || "Failed to load skill rankings.");
      }
      setLoadingRankings(false);
    }
    loadRankings();
  }, [activeTab, rankingFilterRole]);

  // Fetch comparison when compare tab is active or selectedRoleIds change
  useEffect(() => {
    if (activeTab !== "compare" || selectedRoleIds.length < 2) return;
    async function runComparison() {
      setLoadingCompare(true);
      setError(null);
      const res = await compareRoles(selectedRoleIds, "India");
      if (res.success && res.data) {
        setComparisonData(res.data);
      } else {
        setError(res.error || "Failed to compare roles.");
      }
      setLoadingCompare(false);
    }
    runComparison();
  }, [activeTab, selectedRoleIds]);

  // Fetch market signals
  useEffect(() => {
    if (activeTab !== "signals" || !signalsRoleId) return;
    async function loadSignals() {
      setLoadingSignals(true);
      setError(null);
      const res = await fetchRoleMarketSignals(signalsRoleId, "India");
      if (res.success && res.data) {
        setSignalsData(res.data);
      } else {
        setError(res.error || "Failed to load market signals.");
      }
      setLoadingSignals(false);
    }
    loadSignals();
  }, [activeTab, signalsRoleId]);

  // Fetch demand trends
  useEffect(() => {
    if (activeTab !== "trends") return;
    async function loadTrends() {
      setLoadingTrends(true);
      setError(null);
      const res = await fetchDemandTrends("India", undefined, 30, 0);
      if (res.success && res.data) {
        setTrends(res.data.data);
        if (res.data.meta?.data_freshness) {
          setDataFreshness(res.data.meta.data_freshness);
        }
      } else {
        setError(res.error || "Failed to load demand trends.");
      }
      setLoadingTrends(false);
    }
    loadTrends();
  }, [activeTab]);

  const toggleRoleSelection = (roleId: string) => {
    if (selectedRoleIds.includes(roleId)) {
      if (selectedRoleIds.length <= 2) return; // Keep at least 2
      setSelectedRoleIds(selectedRoleIds.filter((id) => id !== roleId));
    } else {
      if (selectedRoleIds.length >= 5) return; // Cap at 5
      setSelectedRoleIds([...selectedRoleIds, roleId]);
    }
  };

  const getTrendBadge = (trend: "RISING" | "STABLE" | "DECLINING") => {
    if (trend === "RISING") {
      return (
        <span className="px-2 py-0.5 text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full">
          ↗ RISING
        </span>
      );
    } else if (trend === "DECLINING") {
      return (
        <span className="px-2 py-0.5 text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded-full">
          ↘ DECLINING
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 text-xs font-semibold bg-slate-500/20 text-slate-300 border border-slate-500/30 rounded-full">
        → STABLE
      </span>
    );
  };

  return (
    <div className="bg-white/80 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-md dark:shadow-xl text-slate-800 dark:text-slate-100 mb-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200 dark:border-slate-800 pb-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              Cross-Role Career Demand Intelligence
            </h2>
            <span className="px-2 py-0.5 text-xs font-semibold bg-cyan-500/20 text-cyan-700 dark:text-cyan-300 border border-cyan-500/30 rounded-full">
              Market Benchmark
            </span>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Cross-market skill rankings, multi-role skill comparisons, and verified YoY growth trends.
          </p>
        </div>
        <div className="text-xs text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700/60 flex items-center gap-2">
          <span>Freshness: <strong className="text-slate-800 dark:text-slate-200 font-mono">{dataFreshness}</strong></span>
          <span>•</span>
          <span>Location: <strong className="text-slate-800 dark:text-slate-200 font-mono">India</strong></span>
        </div>
      </div>

      {/* Feature Sub-Navigation Tabs */}
      <div className="flex flex-wrap gap-2 mb-6 border-b border-slate-200 dark:border-slate-800 pb-3">
        <button
          onClick={() => setActiveTab("ranking")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${
            activeTab === "ranking"
              ? "bg-cyan-600 text-white shadow-md shadow-cyan-500/20"
              : "bg-slate-100 dark:bg-slate-800/60 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-slate-800"
          }`}
        >
          1. Skill Rankings
        </button>
        <button
          onClick={() => setActiveTab("compare")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${
            activeTab === "compare"
              ? "bg-cyan-600 text-white shadow-md shadow-cyan-500/20"
              : "bg-slate-100 dark:bg-slate-800/60 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-slate-800"
          }`}
        >
          2. Compare Roles ({selectedRoleIds.length})
        </button>
        <button
          onClick={() => setActiveTab("signals")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${
            activeTab === "signals"
              ? "bg-cyan-600 text-white shadow-md shadow-cyan-500/20"
              : "bg-slate-100 dark:bg-slate-800/60 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-slate-800"
          }`}
        >
          3. Role Market Signals
        </button>
        <button
          onClick={() => setActiveTab("trends")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${
            activeTab === "trends"
              ? "bg-cyan-600 text-white shadow-md shadow-cyan-500/20"
              : "bg-slate-100 dark:bg-slate-800/60 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-slate-800"
          }`}
        >
          4. Growth Trends
        </button>
      </div>

      {/* Global Error Banner */}
      {error && (
        <div className="p-3 mb-4 rounded-lg bg-red-500/10 dark:bg-red-900/30 border border-red-500/30 dark:border-red-700 text-red-700 dark:text-red-200 text-sm">
          {error}
        </div>
      )}

      {/* ----------------- TAB A: SKILL RANKINGS ----------------- */}
      {activeTab === "ranking" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3">
            <span className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              {rankingFilterRole ? "Role-Specific Ranking" : "Global Market Weighted Demand Ranking"}
            </span>
            <select
              value={rankingFilterRole}
              onChange={(e) => setRankingFilterRole(e.target.value)}
              className="bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-cyan-500"
            >
              <option value="">All Roles (Global Weighted)</option>
              {roles.map((r) => (
                <option key={r.role_id} value={r.role_id}>
                  {r.title}
                </option>
              ))}
            </select>
          </div>

          {loadingRankings ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-10 bg-slate-100 dark:bg-slate-800/50 animate-pulse rounded-lg"></div>
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
              <table className="w-full text-left text-xs text-slate-700 dark:text-slate-300">
                <thead className="bg-slate-100 dark:bg-slate-800/70 text-slate-600 dark:text-slate-400 uppercase text-[11px]">
                  <tr>
                    <th className="py-2.5 px-3">#</th>
                    <th className="py-2.5 px-3">Skill</th>
                    <th className="py-2.5 px-3">Category</th>
                    <th className="py-2.5 px-3 text-right">Market Demand</th>
                    <th className="py-2.5 px-3 text-right">YoY Growth</th>
                    <th className="py-2.5 px-3 text-center">Trend</th>
                    <th className="py-2.5 px-3 text-right">Roles</th>
                    <th className="py-2.5 px-3 text-right">Sample Size</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {rankings.map((item, idx) => (
                    <tr key={item.skill_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                      <td className="py-2.5 px-3 font-mono text-slate-400">{idx + 1}</td>
                      <td className="py-2.5 px-3 font-medium text-slate-900 dark:text-white">{item.skill_name}</td>
                      <td className="py-2.5 px-3 text-slate-500 dark:text-slate-400">{item.category || "—"}</td>
                      <td className="py-2.5 px-3 text-right font-mono font-semibold text-cyan-600 dark:text-cyan-300">
                        {Math.round(item.demand_score * 100)}%
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-slate-700 dark:text-slate-300">
                        +{Math.round(item.average_growth_rate * 100)}%
                      </td>
                      <td className="py-2.5 px-3 text-center">{getTrendBadge(item.trend)}</td>
                      <td className="py-2.5 px-3 text-right font-mono text-slate-500 dark:text-slate-400">{item.role_count}</td>
                      <td className="py-2.5 px-3 text-right font-mono text-slate-400 dark:text-slate-500">
                        {item.total_sample_size.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ----------------- TAB B: ROLE COMPARISON ----------------- */}
      {activeTab === "compare" && (
        <div className="space-y-6">
          <div>
            <div className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-2">
              Select 2 to 5 Career Tracks to Compare:
            </div>
            <div className="flex flex-wrap gap-2">
              {roles.map((r) => {
                const isSelected = selectedRoleIds.includes(r.role_id);
                return (
                  <button
                    key={r.role_id}
                    onClick={() => toggleRoleSelection(r.role_id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
                      isSelected
                        ? "bg-cyan-600 border-cyan-500 text-white"
                        : "bg-slate-100 dark:bg-slate-800/70 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
                    }`}
                  >
                    {isSelected ? "✓ " : "+ "}
                    {r.title}
                  </button>
                );
              })}
            </div>
          </div>

          {loadingCompare ? (
            <div className="h-48 bg-slate-100 dark:bg-slate-800/40 animate-pulse rounded-lg"></div>
          ) : comparisonData ? (
            <div className="space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 p-3 rounded-lg">
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">Compared Roles</div>
                  <div className="text-xl font-bold font-mono text-slate-900 dark:text-white mt-0.5">
                    {comparisonData.comparison_summary.compared_roles_count}
                  </div>
                </div>
                <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 p-3 rounded-lg">
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">Total Unique Skills</div>
                  <div className="text-xl font-bold font-mono text-slate-900 dark:text-white mt-0.5">
                    {comparisonData.comparison_summary.total_unique_skills}
                  </div>
                </div>
                <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 p-3 rounded-lg">
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">Shared Skills</div>
                  <div className="text-xl font-bold font-mono text-cyan-600 dark:text-cyan-300 mt-0.5">
                    {comparisonData.comparison_summary.shared_skills_count}
                  </div>
                </div>
                <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 p-3 rounded-lg">
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">Location</div>
                  <div className="text-xl font-bold font-mono text-slate-800 dark:text-slate-300 mt-0.5">India</div>
                </div>
              </div>

              {/* Shared Skills Table */}
              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs font-semibold text-slate-700 dark:text-slate-300">
                  <span>Shared Skills Demanded Across All Selected Roles ({comparisonData.shared_skills.length})</span>
                </div>
                <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
                  <table className="w-full text-left text-xs text-slate-700 dark:text-slate-300">
                    <thead className="bg-slate-100 dark:bg-slate-800/70 text-slate-600 dark:text-slate-400 uppercase text-[11px]">
                      <tr>
                        <th className="py-2 px-3">Skill</th>
                        <th className="py-2 px-3">Category</th>
                        <th className="py-2 px-3 text-right">Avg Demand</th>
                        <th className="py-2 px-3 text-right">Demand Diff</th>
                        {comparisonData.roles.map((r) => (
                          <th key={r.role_id} className="py-2 px-3 text-right">
                            {r.title}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                      {comparisonData.shared_skills.map((s) => (
                        <tr key={s.skill_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                          <td className="py-2 px-3 font-medium text-slate-900 dark:text-white">{s.skill_name}</td>
                          <td className="py-2 px-3 text-slate-500 dark:text-slate-400">{s.category || "—"}</td>
                          <td className="py-2 px-3 text-right font-mono font-semibold text-cyan-600 dark:text-cyan-300">
                            {Math.round(s.average_demand_score * 100)}%
                          </td>
                          <td className="py-2 px-3 text-right font-mono text-slate-500 dark:text-slate-400">
                            ±{Math.round(s.demand_score_diff * 100)}%
                          </td>
                          {comparisonData.roles.map((r) => {
                            const dp = s.demands_by_role[r.role_id];
                            return (
                              <td key={r.role_id} className="py-2 px-3 text-right font-mono">
                                {dp ? `${Math.round(dp.demand_score * 100)}%` : "—"}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Role-Specific Skills Section */}
              <div className="space-y-3">
                <div className="text-xs font-semibold text-slate-700 dark:text-slate-300">Role-Specific Specializations</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {comparisonData.roles.map((r) => {
                    const specific = comparisonData.role_specific_skills[r.role_id] || [];
                    return (
                      <div key={r.role_id} className="bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-750 p-4 rounded-lg">
                        <div className="flex justify-between items-center mb-2">
                          <span className="text-sm font-semibold text-slate-900 dark:text-white">{r.title}</span>
                          <span className="text-xs text-slate-500 dark:text-slate-400">
                            {specific.length} exclusive skill{specific.length === 1 ? "" : "s"}
                          </span>
                        </div>
                        {specific.length === 0 ? (
                          <div className="text-xs text-slate-500 italic">No exclusive skills in this comparison</div>
                        ) : (
                          <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                            {specific.map((sk) => (
                              <div
                                key={sk.skill_id}
                                className="flex justify-between items-center text-xs py-1 px-2 rounded bg-slate-100 dark:bg-slate-800/60"
                              >
                                <span className="text-slate-800 dark:text-slate-200">{sk.skill_name}</span>
                                <span className="font-mono text-cyan-600 dark:text-cyan-300">
                                  {Math.round(sk.demand_score * 100)}%
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* ----------------- TAB C: MARKET SIGNALS ----------------- */}
      {activeTab === "signals" && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3">
            <span className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Select Career Track for Signals:
            </span>
            <select
              value={signalsRoleId}
              onChange={(e) => setSignalsRoleId(e.target.value)}
              className="bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-cyan-500"
            >
              {roles.map((r) => (
                <option key={r.role_id} value={r.role_id}>
                  {r.title}
                </option>
              ))}
            </select>
          </div>

          {loadingSignals ? (
            <div className="h-48 bg-slate-100 dark:bg-slate-800/40 animate-pulse rounded-lg"></div>
          ) : signalsData ? (
            <div className="space-y-6">
              {/* Role Header Info */}
              <div className="bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 p-4 rounded-lg">
                <div className="text-sm font-semibold text-slate-900 dark:text-white">{signalsData.role.title}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{signalsData.role.description}</div>
              </div>

              {/* Signals Overview Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 p-3 rounded-lg">
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">Total Skills</div>
                  <div className="text-xl font-bold font-mono text-slate-900 dark:text-white mt-0.5">
                    {signalsData.metrics.total_demanded_skills}
                  </div>
                </div>
                <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 p-3 rounded-lg">
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">Avg Demand</div>
                  <div className="text-xl font-bold font-mono text-cyan-600 dark:text-cyan-300 mt-0.5">
                    {Math.round(signalsData.metrics.average_demand_score * 100)}%
                  </div>
                </div>
                <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 p-3 rounded-lg">
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">Avg YoY Growth</div>
                  <div className="text-xl font-bold font-mono text-teal-600 dark:text-teal-300 mt-0.5">
                    +{Math.round(signalsData.metrics.average_growth_rate * 100)}%
                  </div>
                </div>
                <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 p-3 rounded-lg">
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">Rising Skills</div>
                  <div className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400 mt-0.5">
                    {signalsData.metrics.rising_skill_count}
                  </div>
                </div>
              </div>

              {/* Top Demanded vs Fastest Growing */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-750 p-4 rounded-lg">
                  <div className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-3">Top 5 Demanded Skills</div>
                  <div className="space-y-2">
                    {signalsData.top_demanded_skills.map((s, idx) => (
                      <div key={s.skill_id} className="flex justify-between items-center text-xs py-1.5 px-2.5 rounded bg-slate-100 dark:bg-slate-800/60">
                        <span className="font-medium text-slate-900 dark:text-white">{idx + 1}. {s.skill_name}</span>
                        <div className="flex items-center gap-3 font-mono">
                          <span className="text-slate-500 dark:text-slate-400">+{Math.round(s.growth_rate * 100)}%</span>
                          <span className="text-cyan-600 dark:text-cyan-300 font-semibold">{Math.round(s.demand_score * 100)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-750 p-4 rounded-lg">
                  <div className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-3">Top 5 Fastest Growing Skills</div>
                  <div className="space-y-2">
                    {signalsData.fastest_growing_skills.map((s, idx) => (
                      <div key={s.skill_id} className="flex justify-between items-center text-xs py-1.5 px-2.5 rounded bg-slate-100 dark:bg-slate-800/60">
                        <span className="font-medium text-slate-900 dark:text-white">{idx + 1}. {s.skill_name}</span>
                        <div className="flex items-center gap-3 font-mono">
                          <span className="text-emerald-600 dark:text-emerald-400 font-semibold">+{Math.round(s.growth_rate * 100)}% YoY</span>
                          <span className="text-slate-500 dark:text-slate-400">{Math.round(s.demand_score * 100)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* ----------------- TAB D: GROWTH TRENDS ----------------- */}
      {activeTab === "trends" && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
              Market Skill Growth Trajectories (Ordered by Growth Rate)
            </span>
          </div>

          {loadingTrends ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-10 bg-slate-100 dark:bg-slate-800/50 animate-pulse rounded-lg"></div>
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
              <table className="w-full text-left text-xs text-slate-700 dark:text-slate-300">
                <thead className="bg-slate-100 dark:bg-slate-800/70 text-slate-600 dark:text-slate-400 uppercase text-[11px]">
                  <tr>
                    <th className="py-2.5 px-3">Skill</th>
                    <th className="py-2.5 px-3">Role</th>
                    <th className="py-2.5 px-3 text-right">YoY Growth Rate</th>
                    <th className="py-2.5 px-3 text-center">Trend Status</th>
                    <th className="py-2.5 px-3 text-right">Market Demand</th>
                    <th className="py-2.5 px-3 text-right">Sample Size</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {trends.map((item) => (
                    <tr key={`${item.skill_id}-${item.role_id}`} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                      <td className="py-2.5 px-3 font-medium text-slate-900 dark:text-white">{item.skill_name}</td>
                      <td className="py-2.5 px-3 text-slate-500 dark:text-slate-400">{item.role_title}</td>
                      <td className="py-2.5 px-3 text-right font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                        +{Math.round(item.growth_rate * 100)}% YoY
                      </td>
                      <td className="py-2.5 px-3 text-center">{getTrendBadge(item.trend)}</td>
                      <td className="py-2.5 px-3 text-right font-mono text-cyan-600 dark:text-cyan-300">
                        {Math.round(item.demand_score * 100)}%
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-slate-400 dark:text-slate-500">
                        {item.sample_size.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Evidence Analysis Note */}
      <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500">
        <span>
          🛡️ <strong>Evidence-Based Analysis</strong>: All demand intelligence is calculated from empirical job market records. LLMs do not generate, modify, or infer these metrics.
        </span>
      </div>
    </div>
  );
}
