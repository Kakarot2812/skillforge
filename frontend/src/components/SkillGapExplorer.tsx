"use client";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import {
  fetchRoles,
  fetchSkillGaps,
  fetchPrioritizedGaps,
  fetchSkillGapEvidence,
  fetchRoleDemand,
  JobRole,
  SkillGapItem,
  SkillGapSummary,
  PrioritizedGapItem,
  PrioritizedGapsSummary,
  SkillGapEvidenceResponseData,
  RoleSkillDemandItem,
  RoleDemandDetailResponse,
} from "../lib/api";
import {
  Briefcase,
  Layers,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  TrendingUp,
  ShieldCheck,
  Filter,
  Flame,
  Search,
  FileText,
  GitBranch,
  X,
  Info,
  Compass,
  RotateCcw,
  Sparkles,
  ExternalLink,
  ChevronRight,
  AlertCircle,
} from "lucide-react";

export interface SkillGapExplorerProps {
  selectedRoleId?: string;
  onSelectRole?: (roleId: string) => void;
  candidateReady?: boolean;
  hasResume?: boolean;
  hasGitHub?: boolean;
  connectedGitHubUsername?: string | null;
  resumeFileName?: string | null;
  resumeId?: string | null;
}

export default function SkillGapExplorer({
  selectedRoleId: controlledRoleId,
  onSelectRole,
  candidateReady,
  hasResume,
  hasGitHub,
  connectedGitHubUsername,
  resumeFileName,
  resumeId,
}: SkillGapExplorerProps = {}) {
  // Determine effective candidate profile readiness (supporting direct props or localStorage fallback)
  const effectiveResumeId =
    resumeId ??
    (typeof window !== "undefined"
      ? localStorage.getItem("skillforge_active_resume_id")
      : null);

  const effectiveHasResume =
    hasResume ?? Boolean(effectiveResumeId);

  const effectiveConnectedGitHub =
    connectedGitHubUsername ??
    (typeof window !== "undefined"
      ? localStorage.getItem("skillforge_connected_github_user")
      : null);

  const effectiveHasGitHub =
    hasGitHub ?? Boolean(effectiveConnectedGitHub);

  const isCandidateReady =
    candidateReady ?? Boolean(effectiveHasResume || effectiveHasGitHub);

  const [roles, setRoles] = useState<JobRole[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<string>(controlledRoleId || "");
  const [loadingRoles, setLoadingRoles] = useState<boolean>(true);
  const [loadingGaps, setLoadingGaps] = useState<boolean>(false);
  const [loadingMarket, setLoadingMarket] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Active view tab: "PRIORITIES" (CP2 default) or "INVENTORY" (CP1)
  const [activeTab, setActiveTab] = useState<"PRIORITIES" | "INVENTORY">("PRIORITIES");

  // Search filter query
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Market Requirements Benchmark State (for CASE A: No Candidate Profile)
  const [marketSkills, setMarketSkills] = useState<RoleSkillDemandItem[]>([]);
  const [marketMeta, setMarketMeta] = useState<RoleDemandDetailResponse["meta"] | null>(null);

  // CP1 State (Candidate Analysis)
  const [selectedRole, setSelectedRole] = useState<JobRole | null>(null);
  const [summary, setSummary] = useState<SkillGapSummary | null>(null);
  const [skills, setSkills] = useState<SkillGapItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<"ALL" | "STRONG" | "PARTIAL" | "MISSING">("ALL");

  // CP2 State (Candidate Priorities)
  const [prioritizedGaps, setPrioritizedGaps] = useState<PrioritizedGapItem[]>([]);
  const [prioSummary, setPrioSummary] = useState<PrioritizedGapsSummary | null>(null);
  const [prioFilter, setPrioFilter] = useState<"ALL" | "HIGH" | "MEDIUM" | "LOW">("ALL");
  const [severityFilter, setSeverityFilter] = useState<"ALL" | "MISSING" | "PARTIAL">("ALL");

  // CP3 Evidence Modal State
  const [selectedEvidenceSkillId, setSelectedEvidenceSkillId] = useState<string | null>(null);
  const [evidenceData, setEvidenceData] = useState<SkillGapEvidenceResponseData | null>(null);
  const [loadingEvidence, setLoadingEvidence] = useState<boolean>(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  // Synchronize when parent passes a new selectedRoleId
  useEffect(() => {
    if (controlledRoleId && controlledRoleId !== selectedRoleId) {
      setSelectedRoleId(controlledRoleId);
    }
  }, [controlledRoleId, selectedRoleId]);

  // Load canonical roles on mount
  useEffect(() => {
    async function loadRoles() {
      setLoadingRoles(true);
      setError(null);
      const res = await fetchRoles();
      if (res.success && res.data?.data && res.data.data.length > 0) {
        const roleList = res.data.data;
        setRoles(roleList);
        const initialRoleId = controlledRoleId || roleList[0].role_id;
        setSelectedRoleId(initialRoleId);
        if (!controlledRoleId && onSelectRole) {
          onSelectRole(initialRoleId);
        }
      } else {
        setError(res.error || "Failed to load canonical job roles.");
      }
      setLoadingRoles(false);
    }
    loadRoles();
  }, []);

  // Fetch either market demand benchmark (when no profile) OR candidate-specific skill gaps
  const loadRoleData = useCallback(async (roleId: string, ready: boolean) => {
    if (!roleId) return;
    setError(null);

    if (!ready) {
      // CASE A: Pure market requirements benchmark (No candidate profile)
      // Purge candidate analysis data to guarantee zero leakage
      setSummary(null);
      setSkills([]);
      setPrioSummary(null);
      setPrioritizedGaps([]);
      setEvidenceData(null);
      setSelectedEvidenceSkillId(null);
      setLoadingMarket(true);

      const demandRes = await fetchRoleDemand(roleId, "India");
      if (demandRes.success && demandRes.data) {
        setSelectedRole(demandRes.data.role);
        setMarketSkills(demandRes.data.skills);
        setMarketMeta(demandRes.meta || null);
      } else {
        setError(demandRes.error || "Failed to fetch role market requirements.");
      }
      setLoadingMarket(false);
      return;
    }

    // CASE B, C, D: Candidate profile is active (Resume, GitHub, or both)
    setLoadingGaps(true);
    const incResume = Boolean(effectiveHasResume);
    const incGitHub = Boolean(effectiveHasGitHub);
    const ghUser = effectiveConnectedGitHub || undefined;
    const resResumeId = effectiveResumeId || undefined;

    const [gapRes, prioRes] = await Promise.all([
      fetchSkillGaps(roleId, "India", undefined, incResume, incGitHub, ghUser, resResumeId),
      fetchPrioritizedGaps(roleId, "India", undefined, incResume, incGitHub, ghUser, resResumeId),
    ]);

    if (gapRes.success && gapRes.data) {
      setSelectedRole(gapRes.data.role);
      setSummary(gapRes.data.summary);
      setSkills(gapRes.data.skills);
    } else {
      setError(gapRes.error || "Failed to fetch skill gap analysis.");
    }

    if (prioRes.success && prioRes.data) {
      setPrioSummary(prioRes.data.summary);
      setPrioritizedGaps(prioRes.data.gaps);
    } else if (!gapRes.error) {
      setError(prioRes.error || "Failed to fetch prioritized gaps.");
    }

    setLoadingGaps(false);
  }, [effectiveHasResume, effectiveHasGitHub, effectiveConnectedGitHub, effectiveResumeId]);

  // Invalidate any open evidence modal when resume identity changes
  useEffect(() => {
    setSelectedEvidenceSkillId(null);
    setEvidenceData(null);
    setEvidenceError(null);
  }, [effectiveResumeId]);

  useEffect(() => {
    if (selectedRoleId) {
      loadRoleData(selectedRoleId, isCandidateReady);
    }
  }, [selectedRoleId, isCandidateReady, effectiveResumeId, loadRoleData]);

  // Handle ESC key to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && selectedEvidenceSkillId) {
        handleCloseEvidence();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedEvidenceSkillId]);

  // Open evidence audit modal
  const handleOpenEvidence = async (skillId: string) => {
    setSelectedEvidenceSkillId(skillId);
    setLoadingEvidence(true);
    setEvidenceError(null);
    setEvidenceData(null);

    const incResume = Boolean(effectiveHasResume);
    const incGitHub = Boolean(effectiveHasGitHub);
    const ghUser = effectiveConnectedGitHub || undefined;
    const resResumeId = effectiveResumeId || undefined;

    const res = await fetchSkillGapEvidence(
      selectedRoleId,
      skillId,
      "India",
      undefined,
      incResume,
      incGitHub,
      ghUser,
      resResumeId
    );
    if (res.success && res.data) {
      setEvidenceData(res.data);
    } else {
      setEvidenceError(res.error || "Failed to load evidence audit.");
    }
    setLoadingEvidence(false);
  };

  const handleCloseEvidence = () => {
    setSelectedEvidenceSkillId(null);
    setEvidenceData(null);
    setEvidenceError(null);
  };

  // Filtered skills for Inventory tab
  const filteredSkills = useMemo(() => {
    return skills.filter((s) => {
      const matchesStatus = statusFilter === "ALL" || s.status === statusFilter;
      const matchesSearch =
        !searchQuery ||
        s.skill_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (s.category && s.category.toLowerCase().includes(searchQuery.toLowerCase()));
      return matchesStatus && matchesSearch;
    });
  }, [skills, statusFilter, searchQuery]);

  // Filtered priorities for Actionable Priorities tab
  const filteredPriorities = useMemo(() => {
    return prioritizedGaps.filter((g) => {
      const matchesTier = prioFilter === "ALL" || g.priority_level === prioFilter;
      const matchesSeverity = severityFilter === "ALL" || g.status === severityFilter;
      const matchesSearch =
        !searchQuery ||
        g.skill_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (g.category && g.category.toLowerCase().includes(searchQuery.toLowerCase()));
      return matchesTier && matchesSeverity && matchesSearch;
    });
  }, [prioritizedGaps, prioFilter, severityFilter, searchQuery]);

  // Filtered market benchmark skills for CASE A (No Candidate Profile)
  const filteredMarketSkills = useMemo(() => {
    return marketSkills.filter((s) => {
      const matchesSearch =
        !searchQuery ||
        s.skill_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (s.category && s.category.toLowerCase().includes(searchQuery.toLowerCase()));
      return matchesSearch;
    });
  }, [marketSkills, searchQuery]);

  // Skill Coverage Percentage
  const coveragePercent = useMemo(() => {
    if (!summary || summary.total_required_skills === 0) return 0;
    return Math.round((summary.strong_count / summary.total_required_skills) * 100);
  }, [summary]);

  const getStatusBadge = (status: "STRONG" | "PARTIAL" | "MISSING") => {
    if (status === "STRONG") {
      return (
        <span
          className="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-[11px] font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 rounded-full"
          title="Verified repository evidence (Confidence >= 85%)"
        >
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          STRONG
        </span>
      );
    } else if (status === "PARTIAL") {
      return (
        <span
          className="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-[11px] font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30 rounded-full"
          title="Claimed in resume or partial code artifacts"
        >
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          PARTIAL
        </span>
      );
    }
    return (
      <span
        className="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-[11px] font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/30 rounded-full"
        title="Neither resume claim nor GitHub code evidence found"
      >
        <XCircle className="w-3.5 h-3.5 text-rose-400" />
        MISSING
      </span>
    );
  };

  const getPriorityBadge = (level: "HIGH" | "MEDIUM" | "LOW") => {
    if (level === "HIGH") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[11px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 rounded-full">
          <Flame className="w-3 h-3 text-rose-400" />
          HIGH
        </span>
      );
    } else if (level === "MEDIUM") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[11px] font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30 rounded-full">
          <AlertTriangle className="w-3 h-3 text-amber-400" />
          MEDIUM
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[11px] font-medium bg-blue-500/15 text-blue-300 border border-blue-500/30 rounded-full">
        <Compass className="w-3 h-3 text-blue-400" />
        LOW
      </span>
    );
  };

  return (
    <div className="bg-neutral-900/70 border border-neutral-800/90 rounded-3xl p-5 sm:p-7 backdrop-blur-md shadow-2xl text-neutral-100 space-y-6">
      {/* --------------------------------------------------------------------- */}
      {/* 1. Header & Canonical Role Selector Bar                                */}
      {/* --------------------------------------------------------------------- */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 pb-5 border-b border-neutral-800">
        <div className="flex items-start gap-3.5">
          <div className="p-3 rounded-2xl bg-gradient-to-br from-amber-500/20 via-rose-500/20 to-indigo-500/10 text-amber-400 border border-amber-500/30 shadow-inner">
            <Flame className="h-6 w-6" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-bold text-white tracking-tight">
                Skill Gap & Priorities
              </h2>
              <span className="px-2.5 py-0.5 text-[10px] font-mono text-neutral-400 bg-neutral-800/80 rounded border border-neutral-700/60">
                Location: India
              </span>
            </div>
            <p className="text-xs text-neutral-400 mt-1 max-w-2xl leading-relaxed">
              Synthesizes candidate resume claims and verified GitHub repository code artifacts against canonical industry demand to prioritize actionable career growth areas.
            </p>
          </div>
        </div>

        {/* Canonical Role Selector Dropdown & Refresh */}
        <div className="flex items-center gap-2 w-full lg:w-auto">
          <div className="relative w-full lg:w-64">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-neutral-400">
              <Briefcase className="h-3.5 w-3.5" />
            </div>
            <select
              value={selectedRoleId}
              onChange={(e) => {
                const newId = e.target.value;
                setSelectedRoleId(newId);
                onSelectRole?.(newId);
              }}
              disabled={loadingRoles || loadingGaps}
              aria-label="Select Target Career Role"
              className="w-full bg-neutral-950/80 text-neutral-100 text-xs pl-8 pr-8 py-2.5 rounded-xl border border-neutral-700/80 focus:outline-none focus:border-amber-500 cursor-pointer transition-colors shadow-inner"
            >
              {loadingRoles ? (
                <option>Loading career tracks...</option>
              ) : (
                roles.map((r) => (
                  <option key={r.role_id} value={r.role_id}>
                    {r.title} ({r.category})
                  </option>
                ))
              )}
            </select>
          </div>

          <button
            onClick={() => loadRoleData(selectedRoleId, isCandidateReady)}
            disabled={loadingGaps || loadingMarket}
            aria-label="Refresh Skill Gap Analysis"
            title="Refresh Analysis"
            className="p-2.5 rounded-xl bg-neutral-800/80 hover:bg-neutral-700 text-neutral-300 hover:text-white border border-neutral-700 transition-colors disabled:opacity-50 cursor-pointer shrink-0"
          >
            <RotateCcw className={`h-4 w-4 ${(loadingGaps || loadingMarket) ? "animate-spin text-amber-400" : ""}`} />
          </button>
        </div>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* 2. CASE A: Candidate Profile Required (No Resume & No GitHub)         */}
      {/* --------------------------------------------------------------------- */}
      {!isCandidateReady ? (
        <div className="space-y-6">
          {/* Candidate Profile Required Call-to-Action Banner */}
          <div className="rounded-3xl bg-gradient-to-br from-neutral-950/90 via-neutral-900/60 to-neutral-950/90 border border-neutral-800/90 p-6 sm:p-8 text-center space-y-4 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 right-1/4 w-64 h-32 bg-amber-500/5 rounded-full blur-3xl pointer-events-none" />
            <div className="inline-flex p-3 rounded-2xl bg-amber-500/10 text-amber-400 border border-amber-500/20 shadow-inner">
              <AlertCircle className="h-6 w-6" />
            </div>

            <div className="space-y-1.5 max-w-xl mx-auto">
              <div className="flex items-center justify-center gap-2">
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/25 uppercase tracking-wider">
                  Profile Incomplete
                </span>
                <span className="text-xs text-neutral-400">
                  Target Role: <strong className="text-white">{selectedRole?.title || "Selected Role"}</strong>
                </span>
              </div>
              <h3 className="text-lg font-bold text-white tracking-tight">
                Candidate Profile Required
              </h3>
              <p className="text-xs text-neutral-400 leading-relaxed">
                Upload a resume or connect GitHub to generate candidate-specific skill gaps.
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
              <button
                type="button"
                onClick={() => {
                  document.getElementById("resume-intelligence-card")?.scrollIntoView({ behavior: "smooth" });
                }}
                className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-purple-950/40 transition-all flex items-center gap-2 cursor-pointer"
              >
                <FileText className="h-3.5 w-3.5" />
                <span>Upload Resume</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  document.getElementById("github-intelligence-card")?.scrollIntoView({ behavior: "smooth" });
                }}
                className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold shadow-lg shadow-emerald-950/40 transition-all flex items-center gap-2 cursor-pointer"
              >
                <GitBranch className="h-3.5 w-3.5" />
                <span>Connect GitHub</span>
              </button>
            </div>
          </div>

          {/* Market Requirements Benchmark Section */}
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-neutral-800">
              <div className="flex items-center gap-2">
                <Briefcase className="h-4 w-4 text-neutral-400" />
                <div>
                  <h3 className="text-sm font-semibold text-neutral-200">
                    Market / Role Preview • {selectedRole?.title || "Selected Role"}
                  </h3>
                  <p className="text-[11px] text-neutral-500">
                    Standard industry competencies demanded (Location: India) • Pure Market Data
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-[11px] font-mono">
                <span className="px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 font-medium">
                  Market / Role Preview
                </span>
                <span className="text-neutral-500">Candidate Evidence Pending</span>
              </div>
            </div>

            {/* 4 Market Overview Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-neutral-950/60 border border-neutral-800/90 p-4 rounded-2xl">
                <div className="text-[11px] text-neutral-400 font-medium flex items-center gap-1.5">
                  <Briefcase className="h-3.5 w-3.5 text-neutral-400" />
                  <span>Market Requirements</span>
                </div>
                <div className="text-2xl font-black font-mono text-white mt-1">
                  {marketMeta?.total_demanded_skills ?? marketSkills.length}
                </div>
                <div className="text-[10px] text-neutral-500 mt-1">
                  Skills demanded
                </div>
              </div>

              <div className="bg-neutral-950/60 border border-neutral-800/90 p-4 rounded-2xl">
                <div className="text-[11px] text-blue-400 font-medium flex items-center gap-1.5">
                  <TrendingUp className="h-3.5 w-3.5" />
                  <span>Top Market Skill</span>
                </div>
                <div className="text-2xl font-black font-mono text-blue-300 mt-1 truncate">
                  {marketMeta?.top_skill ?? "—"}
                </div>
                <div className="text-[10px] text-neutral-500 mt-1">
                  Highest industry demand
                </div>
              </div>

              <div className="bg-neutral-950/60 border border-neutral-800/90 p-4 rounded-2xl">
                <div className="text-[11px] text-neutral-400 font-medium flex items-center gap-1.5">
                  <Compass className="h-3.5 w-3.5" />
                  <span>Average Demand</span>
                </div>
                <div className="text-2xl font-black font-mono text-white mt-1">
                  {typeof marketMeta?.average_demand_score === "number"
                    ? Math.round(marketMeta.average_demand_score * 100)
                    : 0}%
                </div>
                <div className="text-[10px] text-neutral-500 mt-1">
                  Across market requirements
                </div>
              </div>

              <div className="bg-neutral-950/60 border border-amber-900/30 p-4 rounded-2xl">
                <div className="text-[11px] text-amber-400 font-medium flex items-center gap-1.5">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  <span>Candidate Analysis</span>
                </div>
                <div className="text-xl font-bold font-mono text-amber-300 mt-1">
                  Not Available
                </div>
                <div className="text-[10px] text-neutral-500 mt-1">
                  Profile required
                </div>
              </div>
            </div>

            {/* Search Filter for Market Skills */}
            <div className="flex items-center justify-between gap-3 pt-1">
              <div className="relative w-full sm:w-72">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-neutral-500">
                  <Search className="h-3.5 w-3.5" />
                </div>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search market skills or categories..."
                  className="w-full bg-neutral-950/60 text-neutral-200 text-xs pl-8 pr-7 py-2 rounded-xl border border-neutral-800 focus:outline-none focus:border-neutral-600 transition-colors"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-neutral-500 hover:text-neutral-300 cursor-pointer"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </div>
              <span className="text-xs text-neutral-500 font-mono">
                Showing {filteredMarketSkills.length} of {marketSkills.length} requirements
              </span>
            </div>

            {/* Market Skills Table */}
            <div className="bg-neutral-950/60 border border-neutral-800/80 rounded-2xl overflow-hidden shadow-inner">
              <div className="px-4 py-3 bg-neutral-900/50 border-b border-neutral-800 flex items-center justify-between text-xs text-neutral-400 font-medium">
                <span>Demanded Market Competency</span>
                <span>Market Demand & Growth</span>
              </div>
              <div className="divide-y divide-neutral-850">
                {filteredMarketSkills.length === 0 ? (
                  <div className="p-8 text-center text-xs text-neutral-500">
                    No market requirements matched your search query.
                  </div>
                ) : (
                  filteredMarketSkills.map((s) => (
                    <div
                      key={s.skill_id}
                      className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-neutral-900/30 transition-colors"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-sm text-neutral-100">{s.skill_name}</span>
                          {s.category && (
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-neutral-800 text-neutral-400 border border-neutral-700/50">
                              {s.category}
                            </span>
                          )}
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-300 border border-blue-500/20 font-mono">
                            MARKET PREVIEW
                          </span>
                        </div>
                        <p className="text-[11px] text-neutral-500">
                          Industry benchmark requirement for {selectedRole?.title || "target role"}. Candidate evaluation pending profile upload.
                        </p>
                      </div>

                      <div className="flex items-center gap-4 text-xs font-mono shrink-0">
                        <div className="w-28 sm:w-36">
                          <div className="flex justify-between text-[10px] mb-1">
                            <span className="text-neutral-400">Demand</span>
                            <span className="text-white font-bold">{Math.round(s.demand_score * 100)}%</span>
                          </div>
                          <div className="w-full bg-neutral-800 h-1.5 rounded-full overflow-hidden">
                            <div
                              className="bg-blue-500 h-full rounded-full"
                              style={{ width: `${Math.round(s.demand_score * 100)}%` }}
                            />
                          </div>
                        </div>

                        <div className="text-right min-w-[65px]">
                          <div className="text-[10px] text-neutral-500">YoY Growth</div>
                          <div className={`font-semibold ${s.growth_rate >= 0 ? "text-emerald-400" : "text-neutral-400"}`}>
                            {s.growth_rate >= 0 ? `+${Math.round(s.growth_rate * 100)}%` : `${Math.round(s.growth_rate * 100)}%`}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* CASE B, C, D: Candidate Profile Active */
        <div className="space-y-6">
          {/* Candidate Profile Active Status Banner */}
          <div className="px-4 py-3 rounded-2xl bg-neutral-950/70 border border-neutral-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
              {effectiveHasResume && effectiveHasGitHub ? (
                <>
                  <span className="font-semibold text-neutral-200">Multi-Source Profile</span>
                  <span className="text-neutral-500">•</span>
                  <span className="text-neutral-400">
                    Resume: <strong className="text-neutral-300 font-medium">{resumeFileName || "Active"}</strong>
                  </span>
                  <span className="text-neutral-500">•</span>
                  <span className="text-neutral-400">
                    GitHub: <strong className="text-neutral-300 font-medium">@{effectiveConnectedGitHub}</strong>
                  </span>
                </>
              ) : effectiveHasResume ? (
                <>
                  <span className="font-semibold text-neutral-200">Resume-Based Analysis</span>
                  <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 font-mono text-[10px]">
                    GitHub not connected
                  </span>
                  <span className="text-neutral-400">
                    (Resume: <strong className="text-neutral-300 font-medium">{resumeFileName || "Active"}</strong>)
                  </span>
                </>
              ) : (
                <>
                  <span className="font-semibold text-neutral-200">GitHub-Based Analysis</span>
                  <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 font-mono text-[10px]">
                    Resume not uploaded
                  </span>
                  <span className="text-neutral-400">
                    (GitHub: <strong className="text-neutral-300 font-medium">@{effectiveConnectedGitHub}</strong>)
                  </span>
                </>
              )}
            </div>
            <div className="flex items-center gap-1.5 text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20 shrink-0">
              <ShieldCheck className="h-3 w-3" />
              <span>Candidate Intelligence Active</span>
            </div>
          </div>

          {/* --------------------------------------------------------------------- */}
          {/* 2. Executive Overview Dashboard & Skill Coverage Meter                */}
          {/* --------------------------------------------------------------------- */}
          {summary && selectedRole && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {/* Metric 1: Total Demanded */}
                <div className="bg-neutral-950/60 border border-neutral-800/90 p-4 rounded-2xl relative overflow-hidden">
                  <div className="text-[11px] text-neutral-400 font-medium flex items-center gap-1.5">
                    <Briefcase className="h-3.5 w-3.5 text-neutral-400" />
                    <span>Target Role Skills</span>
                  </div>
                  <div className="text-2xl font-black font-mono text-white mt-1">
                    {summary.total_required_skills}
                  </div>
                  <div className="text-[10px] text-neutral-500 mt-1 truncate">
                    Demanded for {selectedRole.title}
                  </div>
                </div>

                {/* Metric 2: Strong Verified */}
                <div className="bg-neutral-950/60 border border-emerald-900/30 p-4 rounded-2xl relative overflow-hidden">
                  <div className="text-[11px] text-emerald-400 font-medium flex items-center gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Strongly Verified</span>
                  </div>
                  <div className="text-2xl font-black font-mono text-emerald-300 mt-1">
                    {summary.strong_count}
                  </div>
                  <div className="text-[10px] text-neutral-500 mt-1">
                    Verified repository evidence (&ge;85%)
                  </div>
                </div>

                {/* Metric 3: Actionable Gaps */}
                <div className="bg-neutral-950/60 border border-amber-900/30 p-4 rounded-2xl relative overflow-hidden">
                  <div className="text-[11px] text-amber-400 font-medium flex items-center gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    <span>Actionable Gaps</span>
                  </div>
                  <div className="text-2xl font-black font-mono text-amber-300 mt-1">
                    {prioSummary?.total_actionable_gaps ?? summary.missing_count + summary.partial_count}
                  </div>
                  <div className="text-[10px] text-neutral-500 mt-1">
                    {summary.missing_count} Missing, {summary.partial_count} Partial
                  </div>
                </div>

                {/* Metric 4: High Priority Focus */}
                <div className="bg-neutral-950/60 border border-rose-900/40 p-4 rounded-2xl relative overflow-hidden">
                  <div className="text-[11px] text-rose-400 font-medium flex items-center gap-1.5">
                    <Flame className="h-3.5 w-3.5" />
                    <span>High Priority Focus</span>
                  </div>
                  <div className="text-2xl font-black font-mono text-rose-300 mt-1">
                    {prioSummary?.high_priority_count ?? 0}
                  </div>
                  <div className="text-[10px] text-neutral-500 mt-1">
                    Immediate focus (Score &ge; 0.67)
                  </div>
                </div>
              </div>

              {/* Coverage Bar */}
              <div className="p-3.5 rounded-2xl bg-neutral-950/40 border border-neutral-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-neutral-400 font-medium">Role Skill Coverage:</span>
                  <span className="font-mono font-bold text-white text-sm">{coveragePercent}%</span>
                  <span className="text-[11px] text-neutral-500">
                    ({summary.strong_count} of {summary.total_required_skills} competencies verified)
                  </span>
                </div>

                {/* Tri-color progress segment */}
                <div className="w-full sm:w-64 h-2 rounded-full bg-neutral-800 overflow-hidden flex">
                  <div
                    style={{ width: `${(summary.strong_count / summary.total_required_skills) * 100}%` }}
                    className="bg-emerald-500 h-full transition-all duration-500"
                    title={`Strong: ${summary.strong_count}`}
                  />
                  <div
                    style={{ width: `${(summary.partial_count / summary.total_required_skills) * 100}%` }}
                    className="bg-amber-500 h-full transition-all duration-500"
                    title={`Partial: ${summary.partial_count}`}
                  />
                  <div
                    style={{ width: `${(summary.missing_count / summary.total_required_skills) * 100}%` }}
                    className="bg-rose-500/80 h-full transition-all duration-500"
                    title={`Missing: ${summary.missing_count}`}
                  />
                </div>
              </div>
            </div>
          )}

      {/* --------------------------------------------------------------------- */}
      {/* 3. Navigation View Switcher & Search Bar                              */}
      {/* --------------------------------------------------------------------- */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pt-2">
        {/* Tabs */}
        <div className="flex items-center gap-1.5 p-1 bg-neutral-950/80 rounded-2xl border border-neutral-800">
          <button
            onClick={() => setActiveTab("PRIORITIES")}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === "PRIORITIES"
                ? "bg-gradient-to-r from-rose-600/30 to-rose-500/20 text-rose-200 border border-rose-500/40 shadow-sm"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <Flame className="h-3.5 w-3.5 text-rose-400" />
            <span>Actionable Priorities ({prioSummary?.total_actionable_gaps ?? 0})</span>
          </button>
          <button
            onClick={() => setActiveTab("INVENTORY")}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === "INVENTORY"
                ? "bg-gradient-to-r from-amber-600/30 to-amber-500/20 text-amber-200 border border-amber-500/40 shadow-sm"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <Layers className="h-3.5 w-3.5 text-amber-400" />
            <span>All Role Skills ({summary?.total_required_skills ?? 0})</span>
          </button>
        </div>

        {/* Live Search Box */}
        <div className="relative w-full sm:w-60">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-neutral-500">
            <Search className="h-3.5 w-3.5" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search skill or category..."
            className="w-full bg-neutral-950/60 text-neutral-200 text-xs pl-8 pr-7 py-2 rounded-xl border border-neutral-800 focus:outline-none focus:border-neutral-600 transition-colors"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-neutral-500 hover:text-neutral-300"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-800/80 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => loadRoleData(selectedRoleId, isCandidateReady)}
            className="px-3 py-1 bg-rose-900/60 hover:bg-rose-800 rounded-lg text-[11px] font-semibold transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* 4. VIEW 1: ACTIONABLE PRIORITIES (CP2 / CP5 Polish)                   */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === "PRIORITIES" && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-2xl bg-neutral-950/40 border border-neutral-800/80 text-xs">
            {/* Priority Tier Filters */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-neutral-400 font-medium mr-1 flex items-center gap-1">
                <Filter className="h-3 w-3" /> Tier:
              </span>
              {(["ALL", "HIGH", "MEDIUM", "LOW"] as const).map((tier) => (
                <button
                  key={tier}
                  onClick={() => setPrioFilter(tier)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    prioFilter === tier
                      ? "bg-rose-600 text-white shadow-sm"
                      : "bg-neutral-800/60 text-neutral-400 hover:text-white hover:bg-neutral-800"
                  }`}
                >
                  {tier === "ALL" && `All (${prioritizedGaps.length})`}
                  {tier === "HIGH" && `High (${prioSummary?.high_priority_count ?? 0})`}
                  {tier === "MEDIUM" && `Medium (${prioSummary?.medium_priority_count ?? 0})`}
                  {tier === "LOW" && `Low (${prioSummary?.low_priority_count ?? 0})`}
                </button>
              ))}
            </div>

            {/* Severity Filters */}
            <div className="flex items-center gap-1.5">
              <span className="text-neutral-400 font-medium mr-1">Severity:</span>
              {(["ALL", "MISSING", "PARTIAL"] as const).map((sev) => (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                    severityFilter === sev
                      ? "bg-neutral-700 text-white shadow-sm"
                      : "bg-neutral-800/40 text-neutral-400 hover:text-white hover:bg-neutral-800"
                  }`}
                >
                  {sev === "ALL" && "All"}
                  {sev === "MISSING" && `Missing (${prioSummary?.missing_count ?? 0})`}
                  {sev === "PARTIAL" && `Partial (${prioSummary?.partial_count ?? 0})`}
                </button>
              ))}

              {(prioFilter !== "ALL" || severityFilter !== "ALL" || searchQuery) && (
                <button
                  onClick={() => {
                    setPrioFilter("ALL");
                    setSeverityFilter("ALL");
                    setSearchQuery("");
                  }}
                  className="ml-2 text-rose-400 hover:text-rose-300 text-[11px] flex items-center gap-1 cursor-pointer"
                >
                  <RotateCcw className="h-3 w-3" /> Reset
                </button>
              )}
            </div>
          </div>

          {/* Loading Skeleton */}
          {loadingGaps ? (
            <div className="space-y-2.5 py-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-14 bg-neutral-950/40 border border-neutral-800/40 animate-pulse rounded-2xl" />
              ))}
            </div>
          ) : filteredPriorities.length === 0 ? (
            <div className="p-10 text-center bg-neutral-950/40 rounded-2xl border border-neutral-800/80 text-neutral-400 text-xs space-y-2">
              <CheckCircle2 className="h-8 w-8 text-emerald-400 mx-auto" />
              <p className="font-bold text-neutral-200 text-sm">No Actionable Gaps Found In Selection</p>
              <p className="text-neutral-500 max-w-md mx-auto leading-relaxed">
                All skills matching the active filter criteria are either demonstrated or classified into another tier.
              </p>
              {(prioFilter !== "ALL" || severityFilter !== "ALL" || searchQuery) && (
                <button
                  onClick={() => {
                    setPrioFilter("ALL");
                    setSeverityFilter("ALL");
                    setSearchQuery("");
                  }}
                  className="mt-2 inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs font-semibold transition-colors"
                >
                  <RotateCcw className="h-3 w-3" /> Clear Filters
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto rounded-2xl border border-neutral-800/80 bg-neutral-950/30">
              <table className="w-full text-left text-xs text-neutral-300">
                <thead className="bg-neutral-950/80 text-neutral-400 uppercase text-[10px] tracking-wider border-b border-neutral-800">
                  <tr>
                    <th className="py-3 px-4">Priority Rank</th>
                    <th className="py-3 px-3 text-center">Score</th>
                    <th className="py-3 px-4">Skill & Domain</th>
                    <th className="py-3 px-3 text-center">Gap Status</th>
                    <th className="py-3 px-3 text-right">Market Demand</th>
                    <th className="py-3 px-3 text-right">YoY Growth</th>
                    <th className="py-3 px-4">Priority Explanation</th>
                    <th className="py-3 px-4 text-center">Audit Evidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800/60">
                  {filteredPriorities.map((item, idx) => (
                    <tr key={item.skill_id} className="hover:bg-neutral-900/50 transition-colors group">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-neutral-500 text-xs w-5 font-bold">
                            #{idx + 1}
                          </span>
                          {getPriorityBadge(item.priority_level)}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-center font-mono font-bold text-white text-xs">
                        <span className="bg-neutral-900 px-2 py-0.5 rounded border border-neutral-800">
                          {item.priority_score.toFixed(2)}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-bold text-white text-sm">{item.skill_name}</div>
                        <div className="text-[10px] text-neutral-400 font-mono mt-0.5">
                          {item.category || "—"}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-center">
                        {getStatusBadge(item.status)}
                      </td>
                      <td className="py-3 px-3 text-right font-mono font-bold text-cyan-300">
                        {Math.round(item.demand_score * 100)}%
                      </td>
                      <td className="py-3 px-3 text-right font-mono text-emerald-400 font-semibold">
                        +{Math.round(item.growth_rate * 100)}%
                      </td>
                      <td className="py-3 px-4 text-neutral-300 text-[11px] max-w-sm leading-relaxed">
                        {item.explanation}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <button
                          onClick={() => handleOpenEvidence(item.skill_id)}
                          aria-label={`Inspect audit evidence for ${item.skill_name}`}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-neutral-800/90 hover:bg-neutral-700 text-cyan-300 hover:text-cyan-200 rounded-xl border border-neutral-700 transition-colors cursor-pointer shadow-sm group-hover:border-cyan-500/40"
                        >
                          <Search className="h-3.5 w-3.5" />
                          <span>Audit</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* 5. VIEW 2: ALL ROLE SKILLS INVENTORY (CP1 / CP5 Polish)               */}
      {/* --------------------------------------------------------------------- */}
      {activeTab === "INVENTORY" && (
        <div className="space-y-4">
          {/* Status Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-2xl bg-neutral-950/40 border border-neutral-800/80 text-xs">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-neutral-400 font-medium mr-1 flex items-center gap-1">
                <Filter className="h-3 w-3" /> Status:
              </span>
              {(["ALL", "MISSING", "PARTIAL", "STRONG"] as const).map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    statusFilter === st
                      ? "bg-amber-600 text-white shadow-sm"
                      : "bg-neutral-800/60 text-neutral-400 hover:text-white hover:bg-neutral-800"
                  }`}
                >
                  {st === "ALL" && `All (${skills.length})`}
                  {st === "MISSING" && `Missing (${summary?.missing_count ?? 0})`}
                  {st === "PARTIAL" && `Partial (${summary?.partial_count ?? 0})`}
                  {st === "STRONG" && `Strong (${summary?.strong_count ?? 0})`}
                </button>
              ))}

              {(statusFilter !== "ALL" || searchQuery) && (
                <button
                  onClick={() => {
                    setStatusFilter("ALL");
                    setSearchQuery("");
                  }}
                  className="ml-2 text-amber-400 hover:text-amber-300 text-[11px] flex items-center gap-1 cursor-pointer"
                >
                  <RotateCcw className="h-3 w-3" /> Reset
                </button>
              )}
            </div>
          </div>

          {/* Table */}
          {loadingGaps ? (
            <div className="space-y-2.5 py-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-14 bg-neutral-950/40 border border-neutral-800/40 animate-pulse rounded-2xl" />
              ))}
            </div>
          ) : filteredSkills.length === 0 ? (
            <div className="p-10 text-center bg-neutral-950/40 rounded-2xl border border-neutral-800/80 text-neutral-400 text-xs space-y-2">
              <Info className="h-8 w-8 text-neutral-500 mx-auto" />
              <p className="font-bold text-neutral-200 text-sm">No Skills Match Selection</p>
              <p className="text-neutral-500">Try adjusting your status filter or search query.</p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-2xl border border-neutral-800/80 bg-neutral-950/30">
              <table className="w-full text-left text-xs text-neutral-300">
                <thead className="bg-neutral-950/80 text-neutral-400 uppercase text-[10px] tracking-wider border-b border-neutral-800">
                  <tr>
                    <th className="py-3 px-4">Skill</th>
                    <th className="py-3 px-3">Domain</th>
                    <th className="py-3 px-3 text-center">Gap Status</th>
                    <th className="py-3 px-3 text-right">Market Demand</th>
                    <th className="py-3 px-3 text-right">YoY Growth</th>
                    <th className="py-3 px-4 text-center">Candidate Evidence</th>
                    <th className="py-3 px-4 text-center">Audit Chain</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800/60">
                  {filteredSkills.map((item) => (
                    <tr key={item.skill_id} className="hover:bg-neutral-900/50 transition-colors group">
                      <td className="py-3 px-4 font-bold text-white text-sm">
                        {item.skill_name}
                      </td>
                      <td className="py-3 px-3 text-neutral-400 font-mono text-[11px]">
                        {item.category || "—"}
                      </td>
                      <td className="py-3 px-3 text-center">
                        {getStatusBadge(item.status)}
                      </td>
                      <td className="py-3 px-3 text-right font-mono font-bold text-cyan-300">
                        {Math.round(item.demand_score * 100)}%
                      </td>
                      <td className="py-3 px-3 text-right font-mono text-emerald-400 font-semibold">
                        +{Math.round(item.growth_rate * 100)}%
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="inline-flex flex-wrap items-center justify-center gap-1.5 text-[11px] font-mono">
                          {item.claimed ? (
                            <span className="px-2 py-0.5 rounded bg-blue-500/15 text-blue-300 border border-blue-500/30" title="Claimed in Candidate Resume">
                              Resume
                            </span>
                          ) : null}
                          {item.demonstrated ? (
                            <span
                              className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold"
                              title={`Verified in GitHub (${item.evidence_count} evidence items)`}
                            >
                              GitHub ({Math.round(item.demonstrated_score * 100)}%)
                            </span>
                          ) : null}
                          {!item.claimed && !item.demonstrated && (
                            <span className="text-neutral-500 italic">No Evidence</span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <button
                          onClick={() => handleOpenEvidence(item.skill_id)}
                          aria-label={`Inspect audit chain for ${item.skill_name}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold bg-neutral-800/90 hover:bg-neutral-700 text-cyan-300 hover:text-cyan-200 rounded-xl border border-neutral-700 transition-colors cursor-pointer group-hover:border-cyan-500/40"
                        >
                          <Search className="h-3 w-3" />
                          <span>Audit</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* 6. EVIDENCE AUDIT MODAL (CP3 / CP5 Accessible & Responsive Dialog)   */}
      {/* --------------------------------------------------------------------- */}
      {selectedEvidenceSkillId && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="audit-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-black/80 backdrop-blur-md animate-in fade-in duration-150"
          onClick={(e) => {
            if (e.target === e.currentTarget) handleCloseEvidence();
          }}
        >
          <div className="bg-neutral-900 border border-neutral-700/80 rounded-3xl w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-2xl flex flex-col text-neutral-200 animate-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="sticky top-0 z-10 flex items-center justify-between p-5 border-b border-neutral-800 bg-neutral-900/95 backdrop-blur-md">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-2xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/25">
                  <Search className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 id="audit-modal-title" className="text-base sm:text-lg font-bold text-white">
                      {evidenceData?.skill_name || "Audit Evidence Chain"}
                    </h3>
                    {evidenceData && (
                      <>
                        {getStatusBadge(evidenceData.status)}
                        {evidenceData.priority_level && getPriorityBadge(evidenceData.priority_level as any)}
                      </>
                    )}
                  </div>
                  <p className="text-[11px] text-neutral-400 mt-0.5 font-mono">
                    Evidence Audit Trail &bull; Model {evidenceData?.reasoning.scoring_version || "v1"}
                  </p>
                </div>
              </div>

              <button
                onClick={handleCloseEvidence}
                aria-label="Close audit evidence modal"
                className="p-2 rounded-xl text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 sm:p-7 space-y-6">
              {loadingEvidence ? (
                <div className="space-y-4 py-8">
                  <div className="h-6 bg-neutral-800/60 rounded-xl animate-pulse w-1/3" />
                  <div className="h-24 bg-neutral-800/40 rounded-2xl animate-pulse" />
                  <div className="h-24 bg-neutral-800/40 rounded-2xl animate-pulse" />
                </div>
              ) : evidenceError ? (
                <div className="p-5 rounded-2xl bg-rose-950/40 border border-rose-800 text-rose-300 text-xs flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    <span>{evidenceError}</span>
                  </div>
                  <button
                    onClick={() => handleOpenEvidence(selectedEvidenceSkillId)}
                    className="px-3 py-1 bg-rose-900/60 hover:bg-rose-800 rounded-lg text-xs font-semibold"
                  >
                    Retry
                  </button>
                </div>
              ) : evidenceData ? (
                <>
                  {/* Card 1: Grounded Classification Reason */}
                  <div className="p-4 sm:p-5 rounded-2xl bg-neutral-950/70 border border-neutral-800">
                    <div className="flex items-center gap-2 text-xs font-bold text-neutral-200 mb-2">
                      <Info className="h-4 w-4 text-cyan-400" />
                      <span>Why This Is A Gap (Classification Reason):</span>
                    </div>
                    <p className="text-xs text-neutral-300 leading-relaxed font-mono">
                      {evidenceData.reasoning.classification_reason}
                    </p>
                  </div>

                  {/* Card 2: Candidate Evidence Section (Strictly Candidate Data) */}
                  <div className="space-y-3.5">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300 flex items-center gap-2">
                        <FileText className="h-4 w-4 text-blue-400" />
                        <span>Candidate Evidence (Your Verified Profile)</span>
                      </h4>
                      <span className="text-[11px] font-mono text-neutral-500">
                        Strictly user-scoped data
                      </span>
                    </div>

                    {/* Resume Claims */}
                    <div className="p-4 rounded-2xl bg-neutral-950/50 border border-neutral-800/90 space-y-2.5">
                      <div className="text-xs font-semibold text-neutral-300 flex items-center justify-between">
                        <span>Resume Mentions:</span>
                        <span className="text-[11px] font-mono text-neutral-500">
                          {evidenceData.candidate_evidence.resume_claims.length} claim(s) found
                        </span>
                      </div>

                      {evidenceData.candidate_evidence.resume_claims.length === 0 ? (
                        <p className="text-xs text-neutral-500 italic py-1">No resume claims recorded for this skill.</p>
                      ) : (
                        <div className="space-y-2">
                          {evidenceData.candidate_evidence.resume_claims.map((claim) => (
                            <div
                              key={claim.id}
                              className="p-3 rounded-xl bg-neutral-900/90 border border-neutral-800 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-1"
                            >
                              <div>
                                <span className="font-semibold text-white">{claim.raw_mention || evidenceData.skill_name}</span>
                                {claim.resume_file_name && (
                                  <span className="text-[11px] text-neutral-400 ml-2 font-mono">
                                    in {claim.resume_file_name}
                                  </span>
                                )}
                              </div>
                              <span className="font-mono text-blue-400 font-semibold text-[11px] shrink-0">
                                {Math.round(claim.confidence_score * 100)}% claim confidence
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* GitHub Code Artifacts */}
                    <div className="p-4 rounded-2xl bg-neutral-950/50 border border-neutral-800/90 space-y-3">
                      <div className="flex items-center justify-between text-xs font-semibold text-neutral-300">
                        <span className="flex items-center gap-1.5">
                          <GitBranch className="h-4 w-4 text-emerald-400" />
                          <span>GitHub Code Demonstration:</span>
                        </span>
                        {evidenceData.candidate_evidence.github_demonstrated && (
                          <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/25">
                            {evidenceData.candidate_evidence.github_demonstrated.evidence_level} tier ({Math.round(evidenceData.candidate_evidence.github_demonstrated.confidence_score * 100)}%)
                          </span>
                        )}
                      </div>

                      {evidenceData.candidate_evidence.github_artifacts.length === 0 ? (
                        <p className="text-xs text-neutral-500 italic py-1">
                          No verified repository manifests, Dockerfiles, or code artifacts detected for this skill.
                        </p>
                      ) : (
                        <div className="space-y-2">
                          {evidenceData.candidate_evidence.github_artifacts.map((art) => (
                            <div
                              key={art.id}
                              className="p-3 rounded-xl bg-neutral-900/90 border border-neutral-800 text-xs space-y-1.5"
                            >
                              <div className="flex flex-wrap justify-between items-center gap-1">
                                <span className="font-bold text-white flex items-center gap-1.5">
                                  <span className="text-neutral-500 font-normal">repo:</span>
                                  {art.repo_name}
                                </span>
                                <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-neutral-800 text-cyan-300 border border-neutral-700">
                                  {art.evidence_type}
                                </span>
                              </div>
                              <div className="flex flex-wrap justify-between items-center text-[11px] text-neutral-400 font-mono gap-1">
                                <span>{art.file_path || "Root manifest"}</span>
                                {art.matched_content && (
                                  <span className="text-neutral-200 bg-neutral-950 px-2 py-0.5 rounded border border-neutral-800">
                                    {art.matched_content}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Card 3: Market Evidence Section (Strictly Market Data) */}
                  <div className="space-y-3 pt-1">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300 flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-cyan-400" />
                        <span>Market Evidence (Target Role Requirements)</span>
                      </h4>
                      <span className="text-[11px] font-mono text-neutral-500">
                        Industry demand benchmark
                      </span>
                    </div>

                    <div className="p-4 rounded-2xl bg-neutral-950/50 border border-neutral-800/90 space-y-3">
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                        <div className="p-3 rounded-xl bg-neutral-900 border border-neutral-800">
                          <div className="text-[10px] text-neutral-500 uppercase font-mono">Target Role</div>
                          <div className="font-bold text-white mt-1">{evidenceData.market_evidence.role_title}</div>
                        </div>
                        <div className="p-3 rounded-xl bg-neutral-900 border border-neutral-800">
                          <div className="text-[10px] text-neutral-500 uppercase font-mono">Market Demand</div>
                          <div className="font-black font-mono text-cyan-300 text-sm mt-1">
                            {Math.round(evidenceData.market_evidence.demand_score * 100)}%
                          </div>
                        </div>
                        <div className="p-3 rounded-xl bg-neutral-900 border border-neutral-800">
                          <div className="text-[10px] text-neutral-500 uppercase font-mono">YoY Growth</div>
                          <div className="font-black font-mono text-emerald-400 text-sm mt-1">
                            +{Math.round(evidenceData.market_evidence.growth_rate * 100)}%
                          </div>
                        </div>
                        <div className="p-3 rounded-xl bg-neutral-900 border border-neutral-800">
                          <div className="text-[10px] text-neutral-500 uppercase font-mono">Sample Size</div>
                          <div className="font-mono text-neutral-200 mt-1">
                            {evidenceData.market_evidence.sample_size.toLocaleString()} postings
                          </div>
                        </div>
                      </div>

                      <div className="p-3 rounded-xl bg-neutral-900/60 border border-neutral-800 text-[11px] text-neutral-400 flex items-start gap-2">
                        <Info className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                        <span className="leading-relaxed">
                          <strong>Market Separation Notice:</strong> Market demand reflects empirical employer requirements across national job postings. It illustrates how critical this skill is for the selected job role and does <em>not</em> imply candidate proficiency.
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Card 4: Prioritization Audit Reason */}
                  {evidenceData.status !== "STRONG" && (
                    <div className="p-4 sm:p-5 rounded-2xl bg-neutral-950/70 border border-rose-900/40 space-y-2">
                      <div className="flex items-center gap-2 text-xs font-bold text-rose-300">
                        <Flame className="h-4 w-4 text-rose-400" />
                        <span>Why It Is Prioritized:</span>
                      </div>
                      <p className="text-xs text-neutral-200 leading-relaxed font-mono">
                        {evidenceData.reasoning.priority_reason}
                      </p>
                      <div className="text-[10px] text-neutral-400 font-mono pt-1">
                        Priority Calculation: Skill gap severity &times; (70% Market Demand + 30% Growth Trend)
                      </div>
                    </div>
                  )}
                </>
              ) : null}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-neutral-800 bg-neutral-900/95 flex items-center justify-between">
              <div className="text-[11px] text-neutral-400 font-mono hidden sm:flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                <span>Audited via Multi-Source Evidence Chain</span>
              </div>
              <button
                onClick={handleCloseEvidence}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-neutral-800 hover:bg-neutral-700 text-white transition-colors cursor-pointer ml-auto"
              >
                Close Audit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* 7. Data Integrity Footer Guarantee                                    */}
      {/* --------------------------------------------------------------------- */}
      <div className="pt-4 border-t border-neutral-800/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-[11px] text-neutral-500">
        <span className="flex items-center gap-1.5">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
          <span>
            <strong>Evidence-Based Prioritization:</strong> Priority is calculated from skill-gap severity, market demand (70%), and industry growth signals (30%).
          </span>
        </span>
        <span className="font-mono text-[10px] text-neutral-500">
          Evaluated deterministically from verified resume, repository, and job market records.
        </span>
      </div>
    </div>
  );
}
