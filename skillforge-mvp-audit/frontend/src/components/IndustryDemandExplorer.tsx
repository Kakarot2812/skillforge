"use client";

import React, { useEffect, useState } from "react";
import {
  fetchRoles,
  fetchRoleDemand,
  fetchDemandQualityAudit,
  JobRole,
  RoleSkillDemandItem,
  DemandQualityAuditReport,
} from "../lib/api";

export default function IndustryDemandExplorer() {
  const [roles, setRoles] = useState<JobRole[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<string>("");
  const [demandedSkills, setDemandedSkills] = useState<RoleSkillDemandItem[]>([]);
  const [loadingRoles, setLoadingRoles] = useState<boolean>(true);
  const [loadingDemand, setLoadingDemand] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [dataFreshness, setDataFreshness] = useState<string>("2026-09-01");
  const [auditReport, setAuditReport] = useState<DemandQualityAuditReport | null>(null);

  // Role aggregate stats
  const [aggregates, setAggregates] = useState<{
    totalSkills?: number;
    avgDemand?: number;
    maxDemand?: number;
    minDemand?: number;
    avgGrowth?: number;
    topSkill?: string | null;
  }>({});

  useEffect(() => {
    async function loadRolesAndAudit() {
      setLoadingRoles(true);
      setError(null);
      
      // Fetch canonical roles
      const res = await fetchRoles();
      if (res.success && res.data?.data && res.data.data.length > 0) {
        setRoles(res.data.data);
        const defaultRole =
          res.data.data.find((r) => r.slug === "backend-engineer") ||
          res.data.data[0];
        setSelectedRoleId(defaultRole.role_id);
      } else {
        setError(res.error || "Failed to load canonical job roles.");
      }

      // Fetch quality audit
      const auditRes = await fetchDemandQualityAudit();
      if (auditRes.success && auditRes.data) {
        setAuditReport(auditRes.data);
      }

      setLoadingRoles(false);
    }
    loadRolesAndAudit();
  }, []);

  useEffect(() => {
    if (!selectedRoleId) return;

    async function loadDemand() {
      setLoadingDemand(true);
      setError(null);
      const res = await fetchRoleDemand(selectedRoleId);
      if (res.success && res.data) {
        setDemandedSkills(res.data.skills);
        if (res.meta) {
          if (res.meta.data_freshness) {
            setDataFreshness(res.meta.data_freshness);
          }
          setAggregates({
            totalSkills: res.meta.total_demanded_skills ?? res.data.skills.length,
            avgDemand: res.meta.average_demand_score,
            maxDemand: res.meta.highest_demand_score,
            minDemand: res.meta.lowest_demand_score,
            avgGrowth: res.meta.average_growth_rate,
            topSkill: res.meta.top_skill,
          });
        }
      } else {
        setError(res.error || "Failed to load role demand profile.");
      }
      setLoadingDemand(false);
    }
    loadDemand();
  }, [selectedRoleId]);

  const selectedRole = roles.find((r) => r.role_id === selectedRoleId);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl text-slate-100 mb-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-white">
              Phase 4: Industry Demand Engine
            </h2>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 uppercase tracking-wider font-mono">
              Phase 4 Complete
            </span>
            <span className="px-2 py-0.5 text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-full">
              Deterministic Market Data
            </span>
            {auditReport && auditReport.status === "VALID" && (
              <span className="hidden sm:inline-flex px-2 py-0.5 text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full">
                ✓ Integrity Verified ({auditReport.total_demand_records} Records)
              </span>
            )}
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Empirical skill demand metrics derived mathematically from structured job market records.
          </p>
        </div>
        <div className="text-xs text-slate-400 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700/60 flex items-center gap-3">
          <span>Freshness: <strong className="text-slate-200 font-mono">{dataFreshness}</strong></span>
          <span>•</span>
          <span>Location: <strong className="text-slate-200 font-mono">India</strong></span>
        </div>
      </div>

      {/* Role Selection Tabs */}
      {loadingRoles ? (
        <div className="animate-pulse flex gap-2 mb-6">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-10 bg-slate-800 rounded-lg w-32"></div>
          ))}
        </div>
      ) : (
        <div className="flex flex-wrap gap-2 mb-6">
          {roles.map((r) => {
            const isSelected = r.role_id === selectedRoleId;
            return (
              <button
                key={r.role_id}
                onClick={() => setSelectedRoleId(r.role_id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 border ${
                  isSelected
                    ? "bg-indigo-600 border-indigo-500 text-white shadow-lg shadow-indigo-500/20"
                    : "bg-slate-800/60 border-slate-700/70 text-slate-300 hover:bg-slate-800 hover:text-white"
                }`}
              >
                {r.title}
              </button>
            );
          })}
        </div>
      )}

      {/* Selected Role Meta & Aggregations */}
      {selectedRole && (
        <div className="space-y-4 mb-6">
          <div className="bg-slate-800/40 border border-slate-800 rounded-lg p-4">
            <div className="flex items-center gap-3 mb-1">
              <span className="text-sm font-semibold text-white">{selectedRole.title}</span>
              <span className="text-xs px-2 py-0.5 bg-slate-700 text-slate-300 rounded">
                {selectedRole.category}
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              {selectedRole.description}
            </p>
          </div>

          {/* SQL-Derived Aggregates Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-3">
              <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Demanded Skills</div>
              <div className="text-xl font-bold font-mono text-white mt-0.5">
                {aggregates.totalSkills ?? demandedSkills.length}
              </div>
            </div>

            <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-3">
              <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Avg Demand Score</div>
              <div className="text-xl font-bold font-mono text-indigo-300 mt-0.5">
                {aggregates.avgDemand !== undefined ? `${Math.round(aggregates.avgDemand * 100)}%` : "—"}
              </div>
            </div>

            <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-3">
              <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Highest Demand</div>
              <div className="text-xl font-bold font-mono text-emerald-400 mt-0.5">
                {aggregates.maxDemand !== undefined ? `${Math.round(aggregates.maxDemand * 100)}%` : "—"}
                {aggregates.topSkill && (
                  <span className="text-xs font-normal text-slate-400 ml-1.5">({aggregates.topSkill})</span>
                )}
              </div>
            </div>

            <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-3">
              <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Avg Growth Trend</div>
              <div className="text-xl font-bold font-mono text-teal-300 mt-0.5">
                {aggregates.avgGrowth !== undefined ? `+${Math.round(aggregates.avgGrowth * 100)}% YoY` : "—"}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="p-3 mb-4 rounded-lg bg-red-900/30 border border-red-700 text-red-200 text-sm">
          {error}
        </div>
      )}

      {/* Skills Demand Breakdown */}
      {loadingDemand ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-12 bg-slate-800/60 animate-pulse rounded-lg"></div>
          ))}
        </div>
      ) : (
        <div>
          <div className="flex justify-between items-center text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 px-1">
            <span>Demanded Skill</span>
            <span className="flex items-center gap-6">
              <span>Growth Trend (YoY)</span>
              <span>Demand Score</span>
            </span>
          </div>

          <div className="space-y-2.5">
            {demandedSkills.map((s) => {
              const pct = Math.round(s.demand_score * 100);
              const growthPct = Math.round(s.growth_rate * 100);
              return (
                <div
                  key={s.skill_id}
                  className="bg-slate-800/50 hover:bg-slate-800 border border-slate-750 rounded-lg p-3 transition-colors"
                >
                  <div className="flex justify-between items-center mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm text-slate-100">
                        {s.skill_name}
                      </span>
                      {s.category && (
                        <span className="text-[11px] text-slate-400 bg-slate-700/50 px-1.5 py-0.5 rounded">
                          {s.category}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-6 text-sm">
                      <span
                        className={`text-xs font-mono font-medium ${
                          growthPct >= 10
                            ? "text-emerald-400"
                            : growthPct >= 5
                            ? "text-teal-300"
                            : "text-slate-400"
                        }`}
                      >
                        +{growthPct}% YoY
                      </span>
                      <span className="font-mono font-semibold text-indigo-300 min-w-[3.5rem] text-right">
                        {pct}%
                      </span>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="w-full bg-slate-700/50 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-indigo-500 h-1.5 rounded-full transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Architectural Guarantee Note */}
      <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-500">
        <span>
          🛡️ <strong>Integrity Guarantee</strong>: Industry demand scores are derived directly from PostgreSQL statistical aggregations. LLMs are never used to generate, modify, or infer demand scores.
        </span>
      </div>
    </div>
  );
}
