"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  X,
  Sparkles,
  Bot,
  AlertCircle,
  Loader2,
  Send,
  ShieldCheck,
  Tag,
  Info,
} from "lucide-react";
import { explainRoadmap, AIRoadmapExplainResponse } from "@/lib/api";

export interface RoadmapExplanationModalProps {
  roadmapId: string;
  roleTitle: string;
  isOpen: boolean;
  onClose: () => void;
}

export default function RoadmapExplanationModal({
  roadmapId,
  roleTitle,
  isOpen,
  onClose,
}: RoadmapExplanationModalProps) {
  const [query, setQuery] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<AIRoadmapExplainResponse | null>(null);

  const handleClose = useCallback(() => {
    setError(null);
    onClose();
  }, [onClose]);

  const fetchExplanation = useCallback(async (customQuery?: string) => {
    if (!roadmapId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await explainRoadmap(roadmapId, {
        user_query: customQuery && customQuery.trim() ? customQuery.trim() : undefined,
        temperature: 0.2,
      });

      if (res.success && res.data) {
        setExplanation(res.data);
      } else {
        setError(
          res.error ||
            "Unable to generate explanation. The local AI service may be starting or offline."
        );
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unexpected network error");
    } finally {
      setLoading(false);
    }
  }, [roadmapId]);

  useEffect(() => {
    if (!isOpen) return;
    let isCancelled = false;
    if (!explanation) {
      Promise.resolve().then(() => {
        if (!isCancelled) {
          fetchExplanation();
        }
      });
    }
    return () => {
      isCancelled = true;
    };
  }, [isOpen, explanation, fetchExplanation]);

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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;
    fetchExplanation(query);
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="explanation-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/60 dark:bg-black/85 backdrop-blur-sm animate-in fade-in duration-150"
    >
      <div
        className="w-full max-w-3xl bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-neutral-800 bg-slate-50/95 dark:bg-neutral-950/80">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 id="explanation-modal-title" className="text-base font-semibold text-slate-900 dark:text-neutral-100">
                  AI Roadmap Strategy & Reasoning
                </h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20 font-semibold">
                  Local Qwen 3 8B
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-neutral-400">
                Grounded explanation of milestones for <span className="text-purple-600 dark:text-purple-300 font-medium">{roleTitle}</span>
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="p-1.5 rounded-lg text-slate-400 dark:text-neutral-400 hover:text-slate-700 dark:hover:text-neutral-200 hover:bg-slate-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
            aria-label="Close dialog"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Informational Invariant Banner */}
          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-neutral-950/80 border border-slate-200 dark:border-neutral-800 text-xs text-slate-600 dark:text-neutral-400 flex items-start gap-2.5">
            <Info className="h-4 w-4 text-slate-500 dark:text-neutral-500 shrink-0 mt-0.5" />
            <div className="leading-relaxed">
              <strong className="text-slate-800 dark:text-neutral-300">Authoritative Ground Truth Notice:</strong> Milestone sequencing, dependency DAG resolution, and priority scores are calculated deterministically by SkillForge algorithms. AI explanations are strictly explanatory and cannot alter roadmap data.
            </div>
          </div>

          {/* Loading Indicator */}
          {loading && (
            <div className="py-12 flex flex-col items-center justify-center text-center space-y-3">
              <div className="relative">
                <Bot className="h-10 w-10 text-purple-600 dark:text-purple-400 animate-bounce" />
                <Loader2 className="h-12 w-12 text-purple-500/40 animate-spin absolute -top-1 -left-1" />
              </div>
              <p className="text-sm text-slate-800 dark:text-neutral-300 font-medium">
                Synthesizing milestone rationale and curriculum strategy...
              </p>
              <p className="text-xs text-slate-500 dark:text-neutral-500">
                Evaluating dependency topological order and verified candidate evidence
              </p>
            </div>
          )}

          {/* Error Message */}
          {error && !loading && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-700 dark:text-rose-300 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-rose-500 dark:text-rose-400 shrink-0 mt-0.5" />
              <div className="flex-1 text-xs">
                <p className="font-semibold text-rose-800 dark:text-rose-200">AI Explanation Notice</p>
                <p className="mt-1 text-slate-700 dark:text-neutral-400">{error}</p>
                <button
                  type="button"
                  onClick={() => fetchExplanation(query)}
                  className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-700 dark:text-rose-200 font-medium text-xs transition-colors cursor-pointer"
                >
                  <Sparkles className="h-3.5 w-3.5" /> Retry Explanation
                </button>
              </div>
            </div>
          )}

          {/* Explanation Content */}
          {!loading && !error && explanation && (
            <div className="space-y-4">
              <div className="p-5 rounded-xl bg-slate-50/80 dark:bg-neutral-950/70 border border-slate-200 dark:border-neutral-800 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-200 dark:border-neutral-800/80 pb-3 text-xs">
                  <div className="flex items-center gap-2">
                    <Bot className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                    <span className="font-semibold text-slate-800 dark:text-neutral-200">Study Strategy & Milestone Sequencing</span>
                  </div>
                  <span className="font-mono text-[10px] text-purple-600 dark:text-purple-400/80 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
                    Status: {explanation.status}
                  </span>
                </div>

                {/* Main Explanation Text */}
                <div className="text-slate-800 dark:text-neutral-200 text-sm leading-relaxed whitespace-pre-line font-sans">
                  {explanation.content}
                </div>

                {/* Referenced Skill Slugs */}
                {explanation.referenced_skill_slugs && explanation.referenced_skill_slugs.length > 0 && (
                  <div className="pt-3 border-t border-slate-200 dark:border-neutral-800/60">
                    <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-neutral-400 mb-2">
                      <Tag className="h-3.5 w-3.5 text-slate-400 dark:text-neutral-500" />
                      <span>Referenced Milestone Skills:</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {explanation.referenced_skill_slugs.map((slug) => (
                        <span
                          key={slug}
                          className="px-2 py-0.5 rounded-md bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-700/60 text-slate-800 dark:text-neutral-300 font-mono text-[11px]"
                        >
                          {slug}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Ask Specific Question Form */}
          <form onSubmit={handleSubmit} className="pt-2">
            <label htmlFor="custom-query-input" className="block text-xs font-medium text-slate-700 dark:text-neutral-300 mb-1.5">
              Ask a specific focus question about this roadmap:
            </label>
            <div className="flex gap-2">
              <input
                id="custom-query-input"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. Which milestone should I prioritize first if I have 10 hours a week?"
                disabled={loading}
                className="flex-1 px-3.5 py-2.5 rounded-xl bg-slate-50 dark:bg-neutral-950 border border-slate-200 dark:border-neutral-800 text-slate-800 dark:text-neutral-200 text-xs placeholder:text-slate-400 dark:placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-purple-500/50 focus:border-purple-500/50 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 active:bg-purple-700 text-white text-xs font-semibold shadow-md dark:shadow-purple-900/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                <span>Ask AI</span>
              </button>
            </div>
          </form>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-200 dark:border-neutral-800 bg-slate-50/80 dark:bg-neutral-950/70 flex items-center justify-between text-xs text-slate-500 dark:text-neutral-500">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400/80" />
            <span>Non-Authoritative Explanatory Guidance</span>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="px-4 py-1.5 rounded-lg bg-slate-200 dark:bg-neutral-800 hover:bg-slate-300 dark:hover:bg-neutral-700 text-slate-800 dark:text-neutral-300 text-xs font-medium transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
