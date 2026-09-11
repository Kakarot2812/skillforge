"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  X,
  BookOpen,
  ExternalLink,
  Clock,
  AlertCircle,
  Loader2,
  RefreshCw,
  GraduationCap,
} from "lucide-react";
import { fetchApprovedResources, ApprovedResourceListResponse, RoadmapResourceItem } from "@/lib/api";

export interface RoadmapResourcesModalProps {
  skillId: string;
  skillName: string;
  isOpen: boolean;
  onClose: () => void;
}

const DIFFICULTY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  BEGINNER: {
    bg: "bg-emerald-500/10",
    text: "text-emerald-400",
    border: "border-emerald-500/20",
  },
  INTERMEDIATE: {
    bg: "bg-blue-500/10",
    text: "text-blue-400",
    border: "border-blue-500/20",
  },
  ADVANCED: {
    bg: "bg-purple-500/10",
    text: "text-purple-400",
    border: "border-purple-500/20",
  },
};

export default function RoadmapResourcesModal({
  skillId,
  skillName,
  isOpen,
  onClose,
}: RoadmapResourcesModalProps) {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ApprovedResourceListResponse | null>(null);

  const handleClose = useCallback(() => {
    setData(null);
    setError(null);
    onClose();
  }, [onClose]);

  const loadResources = useCallback(async () => {
    if (!skillId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchApprovedResources(skillId);
      if (res.success && res.data) {
        setData(res.data);
      } else {
        setError(res.error || "Failed to load approved learning resources.");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unexpected network error");
    } finally {
      setLoading(false);
    }
  }, [skillId]);

  useEffect(() => {
    if (!isOpen) return;
    let isCancelled = false;
    Promise.resolve().then(() => {
      if (!isCancelled) {
        loadResources();
      }
    });
    return () => {
      isCancelled = true;
    };
  }, [isOpen, loadResources]);

  // Handle ESC key to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        handleClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="resources-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150"
    >
      <div
        className="w-full max-w-2xl bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-800 bg-neutral-950/70">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <BookOpen className="h-5 w-5" />
            </div>
            <div>
              <h2 id="resources-modal-title" className="text-base font-semibold text-neutral-100">
                Curated Learning Resources
              </h2>
              <p className="text-xs text-neutral-400">
                Approved curriculum for <span className="text-blue-400 font-medium">{skillName}</span>
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800 transition-colors cursor-pointer"
            aria-label="Close dialog"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {loading && (
            <div className="py-12 flex flex-col items-center justify-center text-center space-y-3">
              <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />
              <p className="text-sm text-neutral-400 font-medium">
                Fetching vetted learning materials...
              </p>
            </div>
          )}

          {error && !loading && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
              <div className="flex-1 text-xs">
                <p className="font-semibold text-rose-200">Unable to retrieve resources</p>
                <p className="mt-1 text-neutral-400">{error}</p>
                <button
                  type="button"
                  onClick={loadResources}
                  className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 font-medium text-xs transition-colors cursor-pointer"
                >
                  <RefreshCw className="h-3.5 w-3.5" /> Retry
                </button>
              </div>
            </div>
          )}

          {!loading && !error && data && (
            <>
              {data.resources.length === 0 ? (
                <div className="py-10 text-center space-y-2">
                  <GraduationCap className="h-10 w-10 text-neutral-600 mx-auto" />
                  <p className="text-sm font-medium text-neutral-300">
                    No approved learning resources found
                  </p>
                  <p className="text-xs text-neutral-500 max-w-sm mx-auto">
                    No curated materials are cataloged for this specific skill yet.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs text-neutral-400 pb-1">
                    <span>
                      Total Approved Resources: <strong className="text-neutral-200">{data.total_resources}</strong>
                    </span>
                    <span className="text-[11px] font-mono text-emerald-400/80">Vetted Provider Catalog</span>
                  </div>

                  {data.resources.map((item: RoadmapResourceItem) => {
                    const diffBadge = DIFFICULTY_COLORS[item.difficulty] || {
                      bg: "bg-neutral-800",
                      text: "text-neutral-400",
                      border: "border-neutral-700",
                    };
                    return (
                      <div
                        key={item.id}
                        className="p-4 rounded-xl bg-neutral-950/60 border border-neutral-800 hover:border-neutral-700/80 transition-all flex flex-col justify-between gap-3 group"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="text-xs font-mono px-2 py-0.5 rounded bg-neutral-800 text-neutral-300 border border-neutral-700/80 font-semibold">
                                {item.resource_type.replace(/_/g, " ")}
                              </span>
                              <span
                                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${diffBadge.bg} ${diffBadge.text} ${diffBadge.border}`}
                              >
                                {item.difficulty}
                              </span>
                              {item.estimated_minutes && (
                                <span className="flex items-center gap-1 text-[11px] text-neutral-400 font-mono">
                                  <Clock className="h-3 w-3 text-neutral-500" />
                                  ~{item.estimated_minutes} min
                                </span>
                              )}
                            </div>
                            <h3 className="text-sm font-semibold text-neutral-100 pt-1 group-hover:text-blue-400 transition-colors">
                              {item.title}
                            </h3>
                            <p className="text-xs text-neutral-400">
                              Provider: <span className="text-neutral-300 font-medium">{item.provider}</span>
                            </p>
                          </div>
                        </div>

                        <div className="pt-2 border-t border-neutral-850 flex items-center justify-between text-xs">
                          <span className="text-[11px] font-mono text-neutral-500 truncate max-w-xs">
                            {item.url}
                          </span>
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/20 text-xs font-medium transition-colors"
                          >
                            <span>Open Resource</span>
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-neutral-800 bg-neutral-950/60 flex items-center justify-between text-xs text-neutral-500">
          <span>Sole Authority: SkillForge Curated Catalog</span>
          <button
            type="button"
            onClick={handleClose}
            className="px-4 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs font-medium transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
