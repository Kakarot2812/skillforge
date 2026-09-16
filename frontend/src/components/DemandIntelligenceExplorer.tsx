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
        <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-accent/10 text-accent border border-accent/30 rounded-sm">
          ↗ RISING
        </span>
      );
    } else if (trend === "DECLINING") {
      return (
        <span className="px-2 py-0.5 text-[10px] font-mono text-muted border border-border rounded-sm">
          ↘ DECLINING
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 text-[10px] font-mono text-foreground border border-border rounded-sm">
        → STABLE
      </span>
    );
  };

  return (
    <div className="editorial-card p-6 sm:p-8 space-y-6 text-foreground mb-8 select-none">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-border pb-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">
            Cross-Role Career Demand Intelligence
          </h2>
          <p className="text-xs sm:text-sm text-muted mt-1">
            Cross-market skill rankings, multi-role skill comparisons, and verified YoY growth trends.
          </p>
        </div>
        <div className="text-xs text-muted bg-surface-subtle px-3 py-1.5 rounded-md border border-border flex items-center gap-2 font-mono">
          <span>Freshness: <strong className="text-foreground">{dataFreshness}</strong></span>
          <span>•</span>
          <span>Location: <strong className="text-foreground">India</strong></span>
        </div>
      </div>

      {/* Feature Sub-Navigation Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-border pb-3">
        <button
          onClick={() => setActiveTab("ranking")}
          className={`px-3 py-1.5 rounded-md text-xs font-mono transition-all cursor-pointer border ${
            activeTab === "ranking"
              ? "bg-foreground text-background border-foreground font-semibold"
              : "bg-surface-subtle text-muted border-border hover:text-foreground"
          }`}
        >
          01 ─ Skill Rankings
        </button>
        <button
          onClick={() => setActiveTab("compare")}
          className={`px-3 py-1.5 rounded-md text-xs font-mono transition-all cursor-pointer border ${
            activeTab === "compare"
              ? "bg-foreground text-background border-foreground font-semibold"
              : "bg-surface-subtle text-muted border-border hover:text-foreground"
          }`}
        >
          02 ─ Compare Roles ({selectedRoleIds.length})
        </button>
        <button
          onClick={() => setActiveTab("signals")}
          className={`px-3 py-1.5 rounded-md text-xs font-mono transition-all cursor-pointer border ${
            activeTab === "signals"
              ? "bg-foreground text-background border-foreground font-semibold"
              : "bg-surface-subtle text-muted border-border hover:text-foreground"
          }`}
        >
          03 ─ Market Signals
        </button>
        <button
          onClick={() => setActiveTab("trends")}
          className={`px-3 py-1.5 rounded-md text-xs font-mono transition-all cursor-pointer border ${
            activeTab === "trends"
              ? "bg-foreground text-background border-foreground font-semibold"
              : "bg-surface-subtle text-muted border-border hover:text-foreground"
          }`}
        >
          04 ─ Growth Trends
        </button>
      </div>

      {/* Global Error Banner */}
      {error && (
        <div className="p-3 mb-4 rounded-md bg-danger-subtle border border-danger/30 text-danger text-xs">
          {error}
        </div>
      )}

      {/* ----------------- TAB A: SKILL RANKINGS ----------------- */}
      {activeTab === "ranking" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3">
            <span className="text-xs font-mono uppercase tracking-widest text-muted">
              {rankingFilterRole ? "Role-Specific Ranking" : "Global Weighted Demand Ranking"}
            </span>
            <select
              value={rankingFilterRole}
              onChange={(e) => setRankingFilterRole(e.target.value)}
              className="bg-surface text-foreground text-xs font-mono px-3 py-1.5 rounded-md border border-border focus:outline-none focus:border-accent"
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
                <div key={i} className="h-10 bg-surface-subtle animate-pulse rounded-md border border-border"></div>
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto border border-border rounded-md bg-surface">
              <table className="w-full text-left text-xs text-foreground">
                <thead className="bg-surface-subtle border-b border-border text-muted font-mono uppercase text-[11px]">
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
                <tbody className="divide-y divide-border">
                  {rankings.map((item, idx) => (
                    <tr key={item.skill_id} className="hover:bg-surface-subtle transition-colors">
                      <td className="py-2.5 px-3 font-mono text-muted">{idx + 1}</td>
                      <td className="py-2.5 px-3 font-medium text-foreground">{item.skill_name}</td>
                      <td className="py-2.5 px-3 text-muted">{item.category || "—"}</td>
                      <td className="py-2.5 px-3 text-right font-mono font-semibold text-foreground">
                        {Math.round(item.demand_score * 100)}%
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-accent">
                        +{Math.round(item.average_growth_rate * 100)}%
                      </td>
                      <td className="py-2.5 px-3 text-center">{getTrendBadge(item.trend)}</td>
                      <td className="py-2.5 px-3 text-right font-mono text-muted">{item.role_count}</td>
                      <td className="py-2.5 px-3 text-right font-mono text-muted">
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
            <div className="text-xs font-mono uppercase tracking-widest text-muted mb-2.5">
              Select 2 to 5 Career Tracks to Compare:
            </div>
            <div className="flex flex-wrap gap-2">
              {roles.map((r) => {
                const isSelected = selectedRoleIds.includes(r.role_id);
                return (
                  <button
                    key={r.role_id}
                    onClick={() => toggleRoleSelection(r.role_id)}
                    className={`px-3 py-1.5 rounded-md text-xs font-mono border transition-colors cursor-pointer ${
                      isSelected
                        ? "bg-accent border-accent text-white"
                        : "bg-surface-subtle border-border text-muted hover:text-foreground hover:border-foreground/20"
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
            <div className="h-48 bg-surface-subtle animate-pulse rounded-md border border-border"></div>
          ) : comparisonData ? (
            <div className="space-y-6">
              {/* Summary Stats Strip */}
              <div className="grid grid-cols-2 sm:grid-cols-4 border border-border rounded-md divide-y sm:divide-y-0 sm:divide-x divide-border bg-surface">
                <div className="p-4">
                  <div className="text-[11px] font-mono uppercase tracking-widest text-muted">Compared Roles</div>
                  <div className="text-2xl font-semibold font-mono text-foreground mt-1">
                    {comparisonData.comparison_summary.compared_roles_count}
                  </div>
                </div>
                <div className="p-4">
                  <div className="text-[11px] font-mono uppercase tracking-widest text-muted">Total Unique Skills</div>
                  <div className="text-2xl font-semibold font-mono text-foreground mt-1">
                    {comparisonData.comparison_summary.total_unique_skills}
                  </div>
                </div>
                <div className="p-4">
                  <div className="text-[11px] font-mono uppercase tracking-widest text-muted">Shared Skills</div>
                  <div className="text-2xl font-semibold font-mono text-accent mt-1">
                    {comparisonData.comparison_summary.shared_skills_count}
                  </div>
                </div>
                <div className="p-4">
                  <div className="text-[11px] font-mono uppercase tracking-widest text-muted">Market Scope</div>
                  <div className="text-2xl font-semibold font-mono text-foreground mt-1">India</div>
                </div>
              </div>

              {/* Shared Skills Table */}
              <div className="space-y-2">
                <div className="text-xs font-mono uppercase tracking-widest text-muted">
                  Shared Skills Demanded Across All Selected Roles ({comparisonData.shared_skills.length})
                </div>
                <div className="overflow-x-auto border border-border rounded-md bg-surface">
                  <table className="w-full text-left text-xs text-foreground">
                    <thead className="bg-surface-subtle border-b border-border text-muted font-mono uppercase text-[11px]">
                      <tr>
                        <th className="py-2.5 px-3">Skill</th>
                        <th className="py-2.5 px-3">Category</th>
                        <th className="py-2.5 px-3 text-right">Avg Demand</th>
                        <th className="py-2.5 px-3 text-right">Demand Diff</th>
                        {comparisonData.roles.map((r) => (
                          <th key={r.role_id} className="py-2.5 px-3 text-right">
                            {r.title}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {comparisonData.shared_skills.map((s) => (
                        <tr key={s.skill_id} className="hover:bg-surface-subtle transition-colors">
                          <td className="py-2.5 px-3 font-medium text-foreground">{s.skill_name}</td>
                          <td className="py-2.5 px-3 text-muted">{s.category || "—"}</td>
                          <td className="py-2.5 px-3 text-right font-mono font-semibold text-accent">
                            {Math.round(s.average_demand_score * 100)}%
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-muted">
                            ±{Math.round(s.demand_score_diff * 100)}%
                          </td>
                          {comparisonData.roles.map((r) => {
                            const dp = s.demands_by_role[r.role_id];
                            return (
                              <td key={r.role_id} className="py-2.5 px-3 text-right font-mono text-foreground">
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
                <div className="text-xs font-mono uppercase tracking-widest text-muted">Role-Specific Specializations</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {comparisonData.roles.map((r) => {
                    const specific = comparisonData.role_specific_skills[r.role_id] || [];
                    return (
                      <div key={r.role_id} className="bg-surface border border-border p-4 rounded-md">
                        <div className="flex justify-between items-center mb-3">
                          <span className="text-xs font-semibold uppercase tracking-wider text-foreground">{r.title}</span>
                          <span className="text-[11px] font-mono text-muted">
                            {specific.length} exclusive skill{specific.length === 1 ? "" : "s"}
                          </span>
                        </div>
                        {specific.length === 0 ? (
                          <div className="text-xs font-mono text-muted italic">No exclusive skills in this comparison</div>
                        ) : (
                          <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                            {specific.map((sk) => (
                              <div
                                key={sk.skill_id}
                                className="flex justify-between items-center text-xs py-1.5 px-2.5 rounded border border-border/50 bg-surface-subtle"
                              >
                                <span className="text-foreground">{sk.skill_name}</span>
                                <span className="font-mono text-accent font-medium">
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
            <span className="text-xs font-mono uppercase tracking-widest text-muted">
              Select Career Track for Signals:
            </span>
            <select
              value={signalsRoleId}
              onChange={(e) => setSignalsRoleId(e.target.value)}
              className="bg-surface text-foreground text-xs font-mono px-3 py-1.5 rounded-md border border-border focus:outline-none focus:border-accent"
            >
              {roles.map((r) => (
                <option key={r.role_id} value={r.role_id}>
                  {r.title}
                </option>
              ))}
            </select>
          </div>

          {loadingSignals ? (
            <div className="h-48 bg-surface-subtle animate-pulse rounded-md border border-border"></div>
          ) : signalsData ? (
            <div className="space-y-6">
              {/* Role Header Info */}
              <div className="bg-surface border border-border p-4 rounded-md">
                <div className="text-sm font-semibold text-foreground">{signalsData.role.title}</div>
                <div className="text-xs text-muted mt-1">{signalsData.role.description}</div>
              </div>

              {/* Signals Overview Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 border border-border rounded-md divide-y sm:divide-y-0 sm:divide-x divide-border bg-surface">
                <div className="p-4">
                  <div className="text-[11px] font-mono uppercase tracking-widest text-muted">Total Skills</div>
                  <div className="text-2xl font-semibold font-mono text-foreground mt-1">
                    {signalsData.metrics.total_demanded_skills}
                  </div>
                </div>
                <div className="p-4">
                  <div className="text-[11px] font-mono uppercase tracking-widest text-muted">Avg Demand</div>
                  <div className="text-2xl font-semibold font-mono text-accent mt-1">
                    {Math.round(signalsData.metrics.average_demand_score * 100)}%
                  </div>
                </div>
                <div className="p-4">
                  <div className="text-[11px] font-mono uppercase tracking-widest text-muted">Avg YoY Growth</div>
                  <div className="text-2xl font-semibold font-mono text-accent mt-1">
                    +{Math.round(signalsData.metrics.average_growth_rate * 100)}%
                  </div>
                </div>
                <div className="p-4">
                  <div className="text-[11px] font-mono uppercase tracking-widest text-muted">Rising Skills</div>
                  <div className="text-2xl font-semibold font-mono text-emerald-600 dark:text-emerald-400 mt-1">
                    {signalsData.metrics.rising_skill_count}
                  </div>
                </div>
              </div>

              {/* Top Demanded vs Fastest Growing */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-surface border border-border p-4 rounded-md">
                  <div className="text-xs font-mono uppercase tracking-widest text-muted mb-3">Top 5 Demanded Skills</div>
                  <div className="space-y-2">
                    {signalsData.top_demanded_skills.map((s, idx) => (
                      <div key={s.skill_id} className="flex justify-between items-center text-xs py-2 px-3 rounded border border-border/50 bg-surface-subtle">
                        <span className="font-medium text-foreground">{idx + 1}. {s.skill_name}</span>
                        <div className="flex items-center gap-3 font-mono">
                          <span className="text-muted">+{Math.round(s.growth_rate * 100)}%</span>
                          <span className="text-accent font-semibold">{Math.round(s.demand_score * 100)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-surface border border-border p-4 rounded-md">
                  <div className="text-xs font-mono uppercase tracking-widest text-muted mb-3">Top 5 Fastest Growing Skills</div>
                  <div className="space-y-2">
                    {signalsData.fastest_growing_skills.map((s, idx) => (
                      <div key={s.skill_id} className="flex justify-between items-center text-xs py-2 px-3 rounded border border-border/50 bg-surface-subtle">
                        <span className="font-medium text-foreground">{idx + 1}. {s.skill_name}</span>
                        <div className="flex items-center gap-3 font-mono">
                          <span className="text-emerald-600 dark:text-emerald-400 font-semibold">+{Math.round(s.growth_rate * 100)}% YoY</span>
                          <span className="text-muted">{Math.round(s.demand_score * 100)}%</span>
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
            <span className="text-xs font-mono uppercase tracking-widest text-muted">
              Market Skill Growth Trajectories (Ordered by Growth Rate)
            </span>
          </div>

          {loadingTrends ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-10 bg-surface-subtle animate-pulse rounded-md border border-border"></div>
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto border border-border rounded-md bg-surface">
              <table className="w-full text-left text-xs text-foreground">
                <thead className="bg-surface-subtle border-b border-border text-muted font-mono uppercase text-[11px]">
                  <tr>
                    <th className="py-2.5 px-3">Skill</th>
                    <th className="py-2.5 px-3">Role</th>
                    <th className="py-2.5 px-3 text-right">YoY Growth Rate</th>
                    <th className="py-2.5 px-3 text-center">Trend Status</th>
                    <th className="py-2.5 px-3 text-right">Market Demand</th>
                    <th className="py-2.5 px-3 text-right">Sample Size</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {trends.map((item) => (
                    <tr key={`${item.skill_id}-${item.role_id}`} className="hover:bg-surface-subtle transition-colors">
                      <td className="py-2.5 px-3 font-medium text-foreground">{item.skill_name}</td>
                      <td className="py-2.5 px-3 text-muted">{item.role_title}</td>
                      <td className="py-2.5 px-3 text-right font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                        +{Math.round(item.growth_rate * 100)}% YoY
                      </td>
                      <td className="py-2.5 px-3 text-center">{getTrendBadge(item.trend)}</td>
                      <td className="py-2.5 px-3 text-right font-mono text-accent font-medium">
                        {Math.round(item.demand_score * 100)}%
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-muted">
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
      <div className="mt-6 pt-4 border-t border-border flex items-center justify-between text-xs font-mono text-muted">
        <span>
          Evidence-Based Analysis: All demand intelligence is calculated from empirical job market records. LLMs do not generate, modify, or infer these metrics.
        </span>
      </div>
    </div>
  );
}
