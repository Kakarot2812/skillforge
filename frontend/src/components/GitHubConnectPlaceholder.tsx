"use client";

import React, { useState, useEffect } from "react";
import {
  GitBranch,
  Star,
  ExternalLink,
  Code2,
  AlertCircle,
  CheckCircle2,
  Loader2,
  RotateCcw,
  ShieldCheck,
  Search,
  Check,
  FileCode,
  Layers,
  ChevronDown,
  ChevronUp,
  X,
  Sparkles,
} from "lucide-react";
import {
  connectGitHub,
  disconnectGitHubAccount,
  fetchGitHubRepositories,
  analyzeGitHubRepository,
  fetchDemonstratedSkills,
  fetchDemonstratedSkillDetail,
  GitHubConnectResult,
  GitHubRepositoryItem,
  AnalyzeResult,
  DemonstratedSkillSummary,
  DemonstratedSkillDetailData,
} from "@/lib/api";
import { useCandidate } from "@/context/CandidateContext";

function GitHubLogo({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
        clipRule="evenodd"
      />
    </svg>
  );
}

export interface GitHubConnectPlaceholderProps {
  onGitHubChange?: (username: string | null) => void;
}

export default function GitHubConnectPlaceholder({
  onGitHubChange,
}: GitHubConnectPlaceholderProps = {}) {
  const [username, setUsername] = useState("");
  const [token, setToken] = useState("");
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectResult, setConnectResult] = useState<GitHubConnectResult | null>(null);
  const [repositories, setRepositories] = useState<GitHubRepositoryItem[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Analysis state
  const [analyzingRepoId, setAnalyzingRepoId] = useState<string | null>(null);
  const [analysisResults, setAnalysisResults] = useState<Record<string, AnalyzeResult>>({});

  // Demonstrated skills state
  const [demonstratedSkills, setDemonstratedSkills] = useState<DemonstratedSkillSummary[]>([]);
  const [isLoadingDemonstrated, setIsLoadingDemonstrated] = useState(false);
  const [selectedSkillDetail, setSelectedSkillDetail] = useState<DemonstratedSkillDetailData | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  // Safe ref for onGitHubChange to prevent infinite render loops
  const onGitHubChangeRef = React.useRef(onGitHubChange);
  React.useEffect(() => {
    onGitHubChangeRef.current = onGitHubChange;
  }, [onGitHubChange]);

  const { connectedGitHubUser: contextGitHubUser, handleGitHubChange } = useCandidate();

  // Refresh demonstrated skills helper strictly scoped to active GitHub username
  const reloadDemonstratedSkills = async (activeUser?: string) => {
    const userToQuery = activeUser || connectResult?.github_username || username.trim();
    setIsLoadingDemonstrated(true);
    try {
      const res = await fetchDemonstratedSkills(
        undefined,
        undefined,
        undefined,
        20,
        0,
        userToQuery || undefined
      );
      if (res.success && res.data) {
        setDemonstratedSkills(res.data.data);
      }
    } finally {
      setIsLoadingDemonstrated(false);
    }
  };

  // Sync initial state from CandidateContext (server-owned session)
  useEffect(() => {
    let isCancelled = false;
    async function syncGitHub() {
      if (!contextGitHubUser) {
        setConnectResult(null);
        setUsername("");
        setRepositories([]);
        setDemonstratedSkills([]);
        return;
      }

      const cleanUser = contextGitHubUser.trim();
      setUsername(cleanUser);
      setIsConnecting(true);
      try {
        const [repoRes, demRes] = await Promise.all([
          fetchGitHubRepositories(20, 0, cleanUser),
          fetchDemonstratedSkills(undefined, undefined, undefined, 20, 0, cleanUser),
        ]);
        if (isCancelled) return;

        let repoList: GitHubRepositoryItem[] = [];
        let totalCount = 0;

        if (repoRes.success && repoRes.data) {
          repoList = repoRes.data.data;
          totalCount = repoRes.data.meta.total;
          setRepositories(repoList);
        }

        if (demRes.success && demRes.data) {
          setDemonstratedSkills(demRes.data.data);
        }

        setConnectResult({
          github_username: cleanUser,
          connected: true,
          discovered_repositories: totalCount,
          connected_at: new Date().toISOString(),
          repositories: repoList,
        });
      } catch {
        // ignore
      } finally {
        if (!isCancelled) {
          setIsConnecting(false);
        }
      }
    }
    syncGitHub();
    return () => {
      isCancelled = true;
    };
  }, [contextGitHubUser]);

  const handleSyncRepositories = async () => {
    const cleanUser = connectResult?.github_username || username.trim();
    if (!cleanUser) return;
    setIsConnecting(true);
    setErrorMessage(null);
    try {
      const res = await connectGitHub(cleanUser, token.trim() || undefined);
      if (res.success && res.data) {
        setConnectResult(res.data);
        if (res.data.repositories && res.data.repositories.length > 0) {
          setRepositories(res.data.repositories);
        } else {
          const repoRes = await fetchGitHubRepositories(20, 0, cleanUser);
          if (repoRes.success && repoRes.data) {
            setRepositories(repoRes.data.data);
          }
        }
        await reloadDemonstratedSkills(cleanUser);
        if (typeof window !== "undefined") {
          window.dispatchEvent(
            new CustomEvent("skillforge:github-evidence-updated", {
              detail: { githubUsername: cleanUser },
            })
          );
        }
      } else {
        setErrorMessage(res.error || "Failed to sync repositories from GitHub");
      }
    } finally {
      setIsConnecting(false);
    }
  };

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanUser = username.trim();
    if (!cleanUser) return;

    setErrorMessage(null);
    setIsConnecting(true);
    // Explicitly clear previous account data to guarantee zero cross-account leakage
    setRepositories([]);
    setDemonstratedSkills([]);
    setAnalysisResults({});
    setSelectedSkillDetail(null);

    try {
      const res = await connectGitHub(cleanUser, token.trim() || undefined);
      if (res.success && res.data) {
        setConnectResult(res.data);
        onGitHubChange?.(cleanUser);
        handleGitHubChange(cleanUser);
        if (res.data.repositories && res.data.repositories.length > 0) {
          setRepositories(res.data.repositories);
        } else {
          const repoRes = await fetchGitHubRepositories(20, 0, cleanUser);
          if (repoRes.success && repoRes.data) {
            setRepositories(repoRes.data.data);
          }
        }
        await reloadDemonstratedSkills(cleanUser);
        if (typeof window !== "undefined") {
          window.dispatchEvent(
            new CustomEvent("skillforge:github-evidence-updated", {
              detail: { githubUsername: cleanUser },
            })
          );
        }
      } else {
        setErrorMessage(res.error || "Failed to connect to GitHub");
      }
    } finally {
      setIsConnecting(false);
    }
  };

  const handleAnalyze = async (repoId: string) => {
    setAnalyzingRepoId(repoId);
    setErrorMessage(null);
    try {
      const res = await analyzeGitHubRepository(repoId);
      if (res.success && res.data) {
        setAnalysisResults((prev) => ({
          ...prev,
          [repoId]: res.data!,
        }));
        const activeUser = connectResult?.github_username || username.trim();
        await reloadDemonstratedSkills(activeUser);

        // Notify dashboard and skill-gap explorer that fresh GitHub evidence was analyzed
        if (typeof window !== "undefined") {
          window.dispatchEvent(
            new CustomEvent("skillforge:github-evidence-updated", {
              detail: { repoId, githubUsername: activeUser },
            })
          );
        }
      } else {
        setErrorMessage(res.error || "Repository analysis failed");
      }
    } finally {
      setAnalyzingRepoId(null);
    }
  };

  const handleInspectSkill = async (skillId: string) => {
    setIsLoadingDetail(true);
    try {
      const res = await fetchDemonstratedSkillDetail(skillId);
      if (res.success && res.data) {
        setSelectedSkillDetail(res.data);
      }
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await disconnectGitHubAccount();
    } catch {
      // ignore
    }
    setConnectResult(null);
    setUsername("");
    setToken("");
    setRepositories([]);
    setDemonstratedSkills([]);
    setErrorMessage(null);
    setAnalysisResults({});
    setSelectedSkillDetail(null);
    onGitHubChange?.(null);
    handleGitHubChange(null);
    if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent("skillforge:github-evidence-updated", {
          detail: { githubUsername: null },
        })
      );
    }
  };

  return (
    <div id="github-intelligence-card" className="bg-white dark:bg-neutral-900/60 border border-neutral-200 dark:border-neutral-800 rounded-2xl p-6 backdrop-blur-md relative flex flex-col justify-between shadow-xs transition-colors duration-200">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-neutral-200 dark:border-neutral-800">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              <GitHubLogo className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-200">GitHub Intelligence</h3>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                Repository Evidence & Demonstrated Skills
              </p>
            </div>
          </div>
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 uppercase tracking-wider font-mono">
            {connectResult ? `@${connectResult.github_username}` : "Code Evidence"}
          </span>
        </div>

        {/* Content */}
        {connectResult ? (
          /* Connected State */
          <div className="mt-5 space-y-4">
            <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 text-neutral-800 dark:text-neutral-200 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 font-semibold text-xs">
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                  <span>Connected to GitHub (@{connectResult.github_username})</span>
                </div>
                <span className="text-[10px] font-mono text-emerald-700 dark:text-emerald-300 bg-emerald-100 dark:bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-300 dark:border-emerald-800/50">
                  {connectResult.discovered_repositories} non-forks
                </span>
              </div>

              {/* Repositories List with Evidence Analysis */}
              <div className="space-y-2 pt-2 border-t border-emerald-200 dark:border-emerald-500/20">
                <div className="flex items-center justify-between text-xs text-neutral-600 dark:text-neutral-400">
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium text-neutral-800 dark:text-neutral-200">Discovered Repositories</span>
                    <span className="text-[10px] font-mono text-emerald-700 dark:text-emerald-400">({repositories.length})</span>
                  </div>
                  <button
                    type="button"
                    onClick={handleSyncRepositories}
                    disabled={isConnecting}
                    className="text-[10px] text-emerald-700 dark:text-emerald-400 hover:text-emerald-800 dark:hover:text-emerald-300 font-mono transition-colors flex items-center gap-1 cursor-pointer disabled:opacity-50"
                    title="Sync repositories from GitHub"
                  >
                    <RotateCcw className={`h-2.5 w-2.5 ${isConnecting ? "animate-spin" : ""}`} />
                    <span>Sync</span>
                  </button>
                </div>

                {repositories.length > 0 ? (
                  <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                    {repositories.map((repo) => {
                      const analysis = analysisResults[repo.repo_id];
                      const isAnalyzing = analyzingRepoId === repo.repo_id;

                      return (
                        <div
                          key={repo.repo_id}
                          className="p-2.5 rounded-lg bg-white dark:bg-neutral-950/60 border border-neutral-200 dark:border-neutral-800 space-y-2 shadow-xs"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className="min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-medium text-neutral-900 dark:text-neutral-200 truncate">
                                  {repo.repo_name}
                                </span>
                                {repo.primary_language && (
                                  <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border border-neutral-200 dark:border-neutral-700">
                                    {repo.primary_language}
                                  </span>
                                )}
                              </div>
                              {repo.description && (
                                <p className="text-[11px] text-neutral-500 dark:text-neutral-400 truncate max-w-[240px]">
                                  {repo.description}
                                </p>
                              )}
                            </div>

                            <div className="flex items-center gap-2 shrink-0">
                              <button
                                type="button"
                                onClick={() => handleAnalyze(repo.repo_id)}
                                disabled={isAnalyzing}
                                className="px-2.5 py-1 rounded-lg bg-emerald-100 hover:bg-emerald-200 dark:bg-emerald-950/80 dark:hover:bg-emerald-900 border border-emerald-300 dark:border-emerald-700/60 text-emerald-800 dark:text-emerald-300 text-[10px] font-medium transition-all flex items-center gap-1 cursor-pointer disabled:opacity-50"
                              >
                                {isAnalyzing ? (
                                  <>
                                    <Loader2 className="h-3 w-3 animate-spin" />
                                    <span>Scanning...</span>
                                  </>
                                ) : analysis ? (
                                  <>
                                    <Check className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                                    <span>Re-scan</span>
                                  </>
                                ) : (
                                  <>
                                    <Search className="h-3 w-3" />
                                    <span>Analyze</span>
                                  </>
                                )}
                              </button>

                              <a
                                href={repo.repo_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="p-1 rounded text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
                                title="View on GitHub"
                              >
                                <ExternalLink className="h-3.5 w-3.5" />
                              </a>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="p-3 text-center rounded-lg bg-white dark:bg-neutral-950/60 border border-neutral-200 dark:border-neutral-800 text-xs text-neutral-500 dark:text-neutral-400 space-y-2">
                    <p className="text-[11px] text-neutral-500 dark:text-neutral-400">
                      No repositories currently indexed for @{connectResult.github_username}.
                    </p>
                    <button
                      type="button"
                      onClick={handleSyncRepositories}
                      disabled={isConnecting}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs transition-all inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                    >
                      {isConnecting ? (
                        <>
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          <span>Fetching...</span>
                        </>
                      ) : (
                        <>
                          <RotateCcw className="h-3.5 w-3.5" />
                          <span>Fetch Repositories from GitHub</span>
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Checkpoint 3: Aggregated Demonstrated Skills Panel */}
            <div className="p-4 rounded-xl bg-neutral-50 dark:bg-neutral-950/80 border border-neutral-200 dark:border-neutral-800 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-semibold text-neutral-900 dark:text-neutral-200">
                  <Sparkles className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  <span>Demonstrated Skills ({demonstratedSkills.length})</span>
                </div>
                <span className="text-[9px] font-mono text-neutral-500 dark:text-neutral-400 bg-white dark:bg-neutral-900 px-2 py-0.5 rounded border border-neutral-200 dark:border-neutral-800">
                  Evidence-First
                </span>
              </div>

              {demonstratedSkills.length > 0 ? (
                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {demonstratedSkills.map((skill) => {
                    const isHigh = skill.evidence_level === "HIGH";
                    const isMed = skill.evidence_level === "MEDIUM";

                    return (
                      <div
                        key={skill.skill_id}
                        className="p-2.5 rounded-lg bg-white dark:bg-neutral-900/90 border border-neutral-200 dark:border-neutral-800/80 hover:border-neutral-300 dark:hover:border-neutral-700 shadow-xs transition-all flex items-center justify-between gap-2"
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-medium text-neutral-900 dark:text-neutral-200">
                              {skill.skill_name}
                            </span>
                            <span
                              className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded border ${
                                isHigh
                                  ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/30"
                                  : isMed
                                  ? "bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-500/30"
                                  : "bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 border-neutral-200 dark:border-neutral-700"
                              }`}
                            >
                              {skill.evidence_level} • {Math.round(skill.confidence_score * 100)}%
                            </span>
                          </div>
                          <p className="text-[10px] text-neutral-500 dark:text-neutral-400 mt-0.5">
                            {skill.repository_count} {skill.repository_count === 1 ? "repo" : "repos"} •{" "}
                            {skill.evidence_count} evidence items
                          </p>
                        </div>

                        <button
                          type="button"
                          onClick={() => handleInspectSkill(skill.skill_id)}
                          className="px-2 py-1 rounded bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300 text-[10px] font-medium transition-colors border border-neutral-200 dark:border-neutral-700/80 cursor-pointer"
                        >
                          Audit Trail
                        </button>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-3 text-center rounded-lg bg-white dark:bg-neutral-900/40 border border-neutral-200 dark:border-neutral-800 text-[11px] text-neutral-500">
                  Click &quot;Analyze&quot; on a repository above to detect demonstrated skills.
                </div>
              )}
            </div>

            {/* Evidence Audit Trail Modal / Drawer */}
            {selectedSkillDetail && (
              <div className="p-4 rounded-xl bg-white dark:bg-neutral-950 border border-emerald-500/40 space-y-3 shadow-md">
                <div className="flex items-center justify-between border-b border-neutral-200 dark:border-neutral-800 pb-2">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    <span className="text-xs font-semibold text-neutral-900 dark:text-neutral-200">
                      Audit Trail: {selectedSkillDetail.skill_name}
                    </span>
                    <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30">
                      {selectedSkillDetail.evidence_level} ({Math.round(selectedSkillDetail.confidence_score * 100)}%)
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedSkillDetail(null)}
                    className="text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200 p-1 cursor-pointer"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>

                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {selectedSkillDetail.evidence.map((ev) => (
                    <div
                      key={ev.evidence_id}
                      className="p-2 rounded-lg bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 space-y-1 text-[11px]"
                    >
                      <div className="flex items-center justify-between text-neutral-800 dark:text-neutral-300">
                        <span className="font-mono text-[10px] text-emerald-700 dark:text-emerald-400">
                          {ev.artifact_name} ({ev.file_path})
                        </span>
                        <span className="text-[9px] font-mono text-neutral-500">
                          Score: {ev.confidence_score}
                        </span>
                      </div>
                      {ev.evidence_description && (
                        <p className="text-[10px] text-neutral-600 dark:text-neutral-400">{ev.evidence_description}</p>
                      )}
                      {ev.matched_content && (
                        <div className="font-mono text-[9px] text-neutral-700 dark:text-neutral-400 bg-white dark:bg-neutral-950 p-1 rounded border border-neutral-200 dark:border-neutral-800 truncate">
                          {ev.matched_content}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="p-3 rounded-xl bg-neutral-50 dark:bg-neutral-950/60 border border-neutral-200 dark:border-neutral-800 text-[11px] text-neutral-600 dark:text-neutral-400 space-y-1">
              <div className="flex items-center gap-1.5 font-medium text-emerald-700 dark:text-emerald-400">
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>Evidence-Based Analysis</span>
              </div>
              <p className="leading-relaxed">
                Demonstrated skills are verified directly from repository artifacts, dependencies, and code configuration across projects.
                <strong className="text-purple-700 dark:text-purple-300 font-medium"> Skills are evaluated strictly from verified evidence.</strong>
              </p>
            </div>

            <button
              type="button"
              onClick={handleDisconnect}
              className="w-full py-2 px-3 rounded-xl bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-200 text-xs font-medium transition-all flex items-center justify-center gap-1.5 border border-neutral-200 dark:border-neutral-700 cursor-pointer"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Connect Different Account</span>
            </button>
          </div>
        ) : (
          /* Connect Form */
          <form onSubmit={handleConnect} className="mt-5 space-y-3">
            <div className="flex items-center gap-2 p-3 rounded-xl bg-neutral-50 dark:bg-neutral-950/60 border border-neutral-200 dark:border-neutral-800/80">
              <GitHubLogo className="h-5 w-5 text-neutral-500 dark:text-neutral-400 shrink-0" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter GitHub username (e.g. octocat)"
                disabled={isConnecting}
                className="bg-transparent text-xs text-neutral-900 dark:text-neutral-200 placeholder:text-neutral-400 dark:placeholder:text-neutral-600 focus:outline-none w-full"
              />
              <button
                type="submit"
                disabled={isConnecting || !username.trim()}
                className="px-3 py-1.5 text-xs rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all shrink-0 flex items-center gap-1.5 cursor-pointer shadow-xs"
              >
                {isConnecting ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>Discovering...</span>
                  </>
                ) : (
                  <span>Connect</span>
                )}
              </button>
            </div>

            {/* Optional Personal Access Token Toggle */}
            <div className="space-y-1.5">
              <button
                type="button"
                onClick={() => setShowTokenInput(!showTokenInput)}
                className="text-[11px] text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-400 transition-colors flex items-center gap-1 cursor-pointer"
              >
                <span>{showTokenInput ? "− Hide" : "+ Add"} Personal Access Token (Optional for higher rate limits)</span>
              </button>

              {showTokenInput && (
                <input
                  type="password"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx (never logged or stored in plain text)"
                  disabled={isConnecting}
                  className="w-full p-2.5 rounded-lg bg-neutral-50 dark:bg-neutral-950/80 border border-neutral-200 dark:border-neutral-800 text-xs text-neutral-900 dark:text-neutral-200 placeholder:text-neutral-400 dark:placeholder:text-neutral-600 focus:outline-none focus:border-emerald-500/50"
                />
              )}
            </div>

            {errorMessage && (
              <div className="p-3 rounded-xl bg-rose-50 dark:bg-red-500/10 border border-rose-200 dark:border-red-500/30 text-rose-700 dark:text-red-400 text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            <div className="p-3.5 rounded-xl bg-neutral-50 dark:bg-neutral-950/40 border border-neutral-200 dark:border-neutral-800/80 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-neutral-700 dark:text-neutral-400 font-medium flex items-center gap-1.5">
                  <Code2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" /> Evidence Scopes
                </span>
                <span className="text-[10px] font-mono text-neutral-500">Read-Only</span>
              </div>
              <ul className="text-[11px] text-neutral-500 space-y-1 pl-4 list-disc">
                <li>Manifest inspection: requirements.txt, pyproject.toml, package.json, pom.xml</li>
                <li>Infrastructure assets: Dockerfile, docker-compose.yml</li>
                <li>CI/CD workflows: .github/workflows/*.yml</li>
              </ul>
            </div>
          </form>
        )}
      </div>

      {/* Footer */}
      <div className="mt-4 pt-3 border-t border-neutral-200 dark:border-neutral-800/50 flex items-center justify-between text-[11px] text-neutral-500 dark:text-neutral-400">
        <span>Evidence Source: GitHub Repositories</span>
        <span className="text-neutral-700 dark:text-neutral-400 font-medium">{connectResult ? "Account Connected" : "Not Connected"}</span>
      </div>
    </div>
  );
}
