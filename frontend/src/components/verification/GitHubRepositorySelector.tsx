"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import {
  fetchGitHubRepositories,
  GitHubRepositoryItem,
} from "@/lib/api";
import {
  GitBranch,
  Star,
  ExternalLink,
  Loader2,
  AlertCircle,
  FolderGit2,
  RefreshCw,
} from "lucide-react";

export interface GitHubRepositorySelectorProps {
  selectedRepoId: string | null;
  onSelectRepo: (repoId: string, repo: GitHubRepositoryItem) => void;
  disabled?: boolean;
}

export default function GitHubRepositorySelector({
  selectedRepoId,
  onSelectRepo,
  disabled = false,
}: GitHubRepositorySelectorProps) {
  const [repositories, setRepositories] = useState<GitHubRepositoryItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const onSelectRepoRef = useRef(onSelectRepo);
  useEffect(() => {
    onSelectRepoRef.current = onSelectRepo;
  }, [onSelectRepo]);

  const loadRepositories = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchGitHubRepositories(50, 0);
      if (res.success && res.data) {
        setRepositories(res.data.data);
        // Auto-select first non-fork repo if none selected
        if (!selectedRepoId && res.data.data.length > 0) {
          const firstEligible = res.data.data.find((r) => !r.is_fork);
          if (firstEligible) {
            onSelectRepoRef.current(firstEligible.repo_id, firstEligible);
          }
        }
      } else {
        setError(res.error || "Failed to load candidate repositories.");
      }
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Unexpected error fetching repositories"
      );
    } finally {
      setIsLoading(false);
    }
  }, [selectedRepoId]);

  useEffect(() => {
    let isCancelled = false;
    Promise.resolve().then(() => {
      if (!isCancelled) {
        loadRepositories();
      }
    });
    return () => {
      isCancelled = true;
    };
  }, [loadRepositories]);

  const selectedRepo = repositories.find((r) => r.repo_id === selectedRepoId);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label
          htmlFor="github-repo-selector"
          className="text-xs font-semibold text-neutral-300 flex items-center gap-1.5"
        >
          <FolderGit2 className="h-3.5 w-3.5 text-indigo-400" />
          <span>Candidate GitHub Repository</span>
        </label>
        <button
          type="button"
          onClick={loadRepositories}
          disabled={isLoading || disabled}
          className="inline-flex items-center gap-1 text-[11px] text-neutral-400 hover:text-neutral-200 transition-colors disabled:opacity-50 cursor-pointer"
          aria-label="Refresh discovered repositories"
        >
          <RefreshCw className={`h-3 w-3 ${isLoading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {isLoading ? (
        <div className="p-4 rounded-xl bg-neutral-950/60 border border-neutral-800 flex items-center justify-center gap-2 text-xs text-neutral-400">
          <Loader2 className="h-4 w-4 animate-spin text-indigo-400" />
          <span>Discovering candidate repositories...</span>
        </div>
      ) : error ? (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-start gap-2">
          <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-medium">Repository Discovery Error</p>
            <p className="text-rose-400/90 text-[11px]">{error}</p>
          </div>
        </div>
      ) : repositories.length === 0 ? (
        <div className="p-4 rounded-xl bg-neutral-950/60 border border-neutral-800 text-center space-y-1 text-xs text-neutral-400">
          <p className="font-medium text-neutral-300">No Repositories Discovered</p>
          <p className="text-[11px] text-neutral-500">
            Connect your GitHub account or push code to populate discovered repositories.
          </p>
        </div>
      ) : (
        <div className="space-y-2.5">
          <div className="relative">
            <select
              id="github-repo-selector"
              value={selectedRepoId || ""}
              onChange={(e) => {
                const targetId = e.target.value;
                const repo = repositories.find((r) => r.repo_id === targetId);
                if (repo) {
                  onSelectRepo(targetId, repo);
                }
              }}
              disabled={disabled || isLoading}
              className="w-full px-3.5 py-2.5 rounded-xl bg-neutral-950 border border-neutral-800 text-neutral-200 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all cursor-pointer"
            >
              <option value="" disabled>
                -- Select candidate repository --
              </option>
              {repositories.map((repo) => (
                <option
                  key={repo.repo_id}
                  value={repo.repo_id}
                  disabled={repo.is_fork}
                >
                  {repo.full_name || repo.repo_name}
                  {repo.primary_language ? ` [${repo.primary_language}]` : ""}
                  {repo.is_fork ? " — Fork (Not eligible)" : ""}
                </option>
              ))}
            </select>
          </div>

          {selectedRepo && (
            <div className="p-3 rounded-xl bg-neutral-950/80 border border-neutral-800/90 flex flex-wrap items-center justify-between gap-2 text-[11px]">
              <div className="flex items-center gap-3">
                <span className="font-mono text-neutral-200 font-semibold truncate max-w-[200px] sm:max-w-xs">
                  {selectedRepo.full_name || selectedRepo.repo_name}
                </span>
                {selectedRepo.default_branch && (
                  <span className="inline-flex items-center gap-1 font-mono text-neutral-400 px-1.5 py-0.5 rounded bg-neutral-900 border border-neutral-800 text-[10px]">
                    <GitBranch className="h-3 w-3 text-neutral-500" />
                    {selectedRepo.default_branch}
                  </span>
                )}
                {selectedRepo.stars_count !== undefined && selectedRepo.stars_count > 0 && (
                  <span className="inline-flex items-center gap-1 text-amber-400/90 text-[10px]">
                    <Star className="h-3 w-3 fill-amber-400/20" />
                    {selectedRepo.stars_count}
                  </span>
                )}
              </div>

              {selectedRepo.repo_url && (
                <a
                  href={selectedRepo.repo_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  <span>View on GitHub</span>
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
