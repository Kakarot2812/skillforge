"use client";

import React, { useState } from "react";
import {
  VerificationAuditDetails,
  DeliverableMatchItem,
  CriterionDetail,
} from "@/lib/types/verification";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  FileCode2,
  CheckCheck,
  ChevronDown,
  ChevronUp,
  FileCheck2,
  Terminal,
  Layers,
} from "lucide-react";

export interface VerificationEvidenceProps {
  details: VerificationAuditDetails;
  commitSha?: string | null;
}

export default function VerificationEvidence({
  details,
  commitSha,
}: VerificationEvidenceProps) {
  const [activeTab, setActiveTab] = useState<"deliverables" | "criteria" | "audit">("deliverables");
  const [expandedCriteria, setExpandedCriteria] = useState<Record<string, boolean>>({});

  const deliverables = details.deliverables;
  const criteria = details.criteria;

  const toggleCriterion = (key: string) => {
    setExpandedCriteria((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  return (
    <div className="space-y-4">
      {/* Evidence Sub-Navigation */}
      <div className="flex items-center gap-1 border-b border-slate-200 dark:border-neutral-800 pb-2 text-xs font-medium">
        <button
          type="button"
          onClick={() => setActiveTab("deliverables")}
          className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 ${
            activeTab === "deliverables"
              ? "bg-slate-200 dark:bg-neutral-800 text-slate-900 dark:text-white font-semibold"
              : "text-slate-600 dark:text-neutral-400 hover:text-slate-900 dark:hover:text-neutral-200"
          }`}
        >
          <FileCheck2 className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
          <span>Deliverables</span>
          {deliverables && (
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-white dark:bg-neutral-900 border border-slate-300 dark:border-neutral-700 text-slate-700 dark:text-neutral-300 font-semibold">
              {deliverables.passed_count}/{deliverables.total_required}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("criteria")}
          className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 ${
            activeTab === "criteria"
              ? "bg-slate-200 dark:bg-neutral-800 text-slate-900 dark:text-white font-semibold"
              : "text-slate-600 dark:text-neutral-400 hover:text-slate-900 dark:hover:text-neutral-200"
          }`}
        >
          <CheckCheck className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
          <span>Automated Rubric</span>
          {criteria && (
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-white dark:bg-neutral-900 border border-slate-300 dark:border-neutral-700 text-slate-700 dark:text-neutral-300 font-semibold">
              {criteria.passed_count}/{criteria.automated_count}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("audit")}
          className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 ${
            activeTab === "audit"
              ? "bg-slate-200 dark:bg-neutral-800 text-slate-900 dark:text-white font-semibold"
              : "text-slate-600 dark:text-neutral-400 hover:text-slate-900 dark:hover:text-neutral-200"
          }`}
        >
          <Terminal className="h-3.5 w-3.5 text-slate-500 dark:text-neutral-400" />
          <span>Audit Breakdown</span>
        </button>
      </div>

      {/* 1. Deliverables Tab */}
      {activeTab === "deliverables" && (
        <div className="space-y-3">
          {deliverables ? (
            <>
              {/* Deliverable Metrics Header */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
                <div className="p-2 rounded-xl bg-slate-50 dark:bg-neutral-950 border border-slate-200 dark:border-neutral-800">
                  <span className="text-[10px] text-slate-500 dark:text-neutral-500 uppercase block">Required</span>
                  <span className="font-mono font-bold text-slate-900 dark:text-neutral-200">
                    {deliverables.total_required}
                  </span>
                </div>
                <div className="p-2 rounded-xl bg-slate-50 dark:bg-neutral-950 border border-slate-200 dark:border-neutral-800">
                  <span className="text-[10px] text-slate-500 dark:text-neutral-500 uppercase block">Matched</span>
                  <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400">
                    {deliverables.passed_count}
                  </span>
                </div>
                <div className="p-2 rounded-xl bg-slate-50 dark:bg-neutral-950 border border-slate-200 dark:border-neutral-800">
                  <span className="text-[10px] text-slate-500 dark:text-neutral-500 uppercase block">Missing</span>
                  <span className="font-mono font-bold text-rose-600 dark:text-rose-400">
                    {deliverables.missing_count}
                  </span>
                </div>
                <div className="p-2 rounded-xl bg-slate-50 dark:bg-neutral-950 border border-slate-200 dark:border-neutral-800">
                  <span className="text-[10px] text-slate-500 dark:text-neutral-500 uppercase block">Deliverable Score</span>
                  <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400">
                    {Math.round(deliverables.deliverables_score * 100)}%
                  </span>
                </div>
              </div>

              {/* Deliverable Match Items */}
              <div className="space-y-2">
                {deliverables.matches && deliverables.matches.length > 0 ? (
                  deliverables.matches.map((item: DeliverableMatchItem, idx: number) => {
                    const isPassed = item.status === "PASSED";
                    const isMissing = item.status === "MISSING";
                    return (
                      <div
                        key={idx}
                        className={`p-3 rounded-xl border text-xs space-y-1.5 transition-colors ${
                          isPassed
                            ? "bg-emerald-500/10 border-emerald-500/20"
                            : isMissing
                            ? "bg-rose-500/10 border-rose-500/20"
                            : "bg-amber-500/10 border-amber-500/20"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2">
                            {isPassed ? (
                              <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                            ) : isMissing ? (
                              <XCircle className="h-4 w-4 text-rose-600 dark:text-rose-400 shrink-0" />
                            ) : (
                              <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0" />
                            )}
                            <span className="font-mono font-semibold text-slate-900 dark:text-neutral-200">
                              {item.deliverable}
                            </span>
                          </div>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider ${
                              isPassed
                                ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30"
                                : isMissing
                                ? "bg-rose-500/15 text-rose-700 dark:text-rose-400 border border-rose-500/30"
                                : "bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30"
                            }`}
                          >
                            {item.status}
                          </span>
                        </div>

                        {item.matched_path && (
                          <div className="text-[11px] font-mono text-slate-600 dark:text-neutral-400 flex items-center gap-1.5 pl-6">
                            <span className="text-slate-400 dark:text-neutral-500">Path:</span>
                            <code className="text-emerald-700 dark:text-emerald-300 bg-white dark:bg-neutral-900 px-1.5 py-0.2 rounded border border-slate-200 dark:border-neutral-800">
                              {item.matched_path}
                            </code>
                          </div>
                        )}

                        {item.detail && (
                          <p className="text-[11px] text-slate-600 dark:text-neutral-400 pl-6 leading-relaxed">
                            {item.detail}
                          </p>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <p className="text-xs text-slate-500 dark:text-neutral-500 italic p-3 text-center">
                    No deliverables required or evaluated for this project milestone.
                  </p>
                )}
              </div>
            </>
          ) : (
            <p className="text-xs text-slate-500 dark:text-neutral-500 italic p-3 text-center">
              No deliverable evidence records found.
            </p>
          )}
        </div>
      )}

      {/* 2. Criteria Tab */}
      {activeTab === "criteria" && (
        <div className="space-y-3">
          {criteria ? (
            <>
              {/* Criteria Metrics Header */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
                <div className="p-2 rounded-xl bg-slate-50 dark:bg-neutral-950 border border-slate-200 dark:border-neutral-800">
                  <span className="text-[10px] text-slate-500 dark:text-neutral-500 uppercase block">Evaluated</span>
                  <span className="font-mono font-bold text-slate-900 dark:text-neutral-200">
                    {criteria.total_criteria}
                  </span>
                </div>
                <div className="p-2 rounded-xl bg-slate-50 dark:bg-neutral-950 border border-slate-200 dark:border-neutral-800">
                  <span className="text-[10px] text-slate-500 dark:text-neutral-500 uppercase block">Passed</span>
                  <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400">
                    {criteria.passed_count}
                  </span>
                </div>
                <div className="p-2 rounded-xl bg-slate-50 dark:bg-neutral-950 border border-slate-200 dark:border-neutral-800">
                  <span className="text-[10px] text-slate-500 dark:text-neutral-500 uppercase block">Failed</span>
                  <span className="font-mono font-bold text-rose-600 dark:text-rose-400">
                    {criteria.failed_count}
                  </span>
                </div>
                <div className="p-2 rounded-xl bg-slate-50 dark:bg-neutral-950 border border-slate-200 dark:border-neutral-800">
                  <span className="text-[10px] text-slate-500 dark:text-neutral-500 uppercase block">Criteria Score</span>
                  <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400">
                    {Math.round(criteria.criteria_score * 100)}%
                  </span>
                </div>
              </div>

              {/* Criteria Result Items */}
              <div className="space-y-2">
                {criteria.results && criteria.results.length > 0 ? (
                  criteria.results.map((crit: CriterionDetail, idx: number) => {
                    const isExpanded = Boolean(expandedCriteria[crit.criterion_key]);
                    const isPassed = crit.status === "PASSED";
                    const isFailed = crit.status === "FAILED";
                    const isManual = crit.status === "MANUAL_REVIEW_ONLY";

                    return (
                      <div
                        key={idx}
                        className={`p-3 rounded-xl border text-xs space-y-2 transition-all ${
                          isPassed
                            ? "bg-emerald-500/10 border-emerald-500/20"
                            : isFailed
                            ? "bg-rose-500/10 border-rose-500/20"
                            : isManual
                            ? "bg-purple-500/10 border-purple-500/20"
                            : "bg-slate-50 dark:bg-neutral-900 border-slate-200 dark:border-neutral-800"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              {isPassed ? (
                                <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                              ) : isFailed ? (
                                <XCircle className="h-4 w-4 text-rose-600 dark:text-rose-400 shrink-0" />
                              ) : isManual ? (
                                <HelpCircle className="h-4 w-4 text-purple-600 dark:text-purple-400 shrink-0" />
                              ) : (
                                <AlertTriangle className="h-4 w-4 text-slate-400 dark:text-neutral-400 shrink-0" />
                              )}
                              <span className="font-mono font-semibold text-slate-900 dark:text-neutral-200 text-[11px]">
                                {crit.criterion_key}
                              </span>
                              {crit.is_automated && (
                                <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-white dark:bg-neutral-900 border border-slate-300 dark:border-neutral-800 text-slate-600 dark:text-neutral-400">
                                  Automated
                                </span>
                              )}
                            </div>
                            <p className="text-[11px] text-slate-700 dark:text-neutral-300 pl-6 leading-relaxed">
                              {crit.rule_description}
                            </p>
                          </div>

                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider shrink-0 ${
                              isPassed
                                ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30"
                                : isFailed
                                ? "bg-rose-500/15 text-rose-700 dark:text-rose-400 border border-rose-500/30"
                                : isManual
                                ? "bg-purple-500/15 text-purple-700 dark:text-purple-400 border border-purple-500/30"
                                : "bg-slate-200 dark:bg-neutral-800 text-slate-700 dark:text-neutral-400 border border-slate-300 dark:border-neutral-700"
                            }`}
                          >
                            {crit.status}
                          </span>
                        </div>

                        {crit.matched_file && (
                          <div className="text-[11px] font-mono text-slate-600 dark:text-neutral-400 flex items-center gap-1.5 pl-6">
                            <FileCode2 className="h-3 w-3 text-slate-400 dark:text-neutral-500" />
                            <span>Matched File:</span>
                            <code className="text-slate-800 dark:text-neutral-200 bg-white dark:bg-neutral-900 px-1.5 py-0.2 rounded border border-slate-200 dark:border-neutral-800 truncate max-w-sm">
                              {crit.matched_file}
                            </code>
                          </div>
                        )}

                        {crit.reason && (
                          <p className="text-[11px] text-slate-600 dark:text-neutral-400 pl-6 italic">
                            Reason: {crit.reason}
                          </p>
                        )}

                        {crit.matched_snippet && (
                          <div className="pl-6 pt-1">
                            <button
                              type="button"
                              onClick={() => toggleCriterion(crit.criterion_key)}
                              className="text-[10px] font-mono text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 inline-flex items-center gap-1 cursor-pointer"
                            >
                              <span>{isExpanded ? "Hide Code Snippet" : "Inspect Code Snippet"}</span>
                              {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                            </button>

                            {isExpanded && (
                              <pre className="mt-1.5 p-2.5 rounded-lg bg-slate-900 dark:bg-neutral-950 border border-slate-800 dark:border-neutral-800 text-[10px] font-mono text-slate-100 dark:text-neutral-300 overflow-x-auto max-h-36 leading-relaxed whitespace-pre-wrap">
                                {crit.matched_snippet}
                              </pre>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <p className="text-xs text-slate-500 dark:text-neutral-500 italic p-3 text-center">
                    No automated rubric criteria evaluated.
                  </p>
                )}
              </div>
            </>
          ) : (
            <p className="text-xs text-slate-500 dark:text-neutral-500 italic p-3 text-center">
              No criteria evaluation records found.
            </p>
          )}
        </div>
      )}

      {/* 3. Audit Breakdown Tab */}
      {activeTab === "audit" && (
        <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-neutral-950/60 border border-slate-200 dark:border-neutral-800 space-y-3 text-xs">
          <div className="flex items-center gap-2 text-slate-900 dark:text-neutral-300 font-semibold border-b border-slate-200 dark:border-neutral-800 pb-2">
            <Layers className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
            <span>Deterministic Scoring Audit</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[11px]">
            <div className="p-2.5 rounded-lg bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 space-y-1">
              <span className="text-slate-500 dark:text-neutral-500 block">Deliverables Score</span>
              <span className="font-mono text-sm font-bold text-slate-900 dark:text-neutral-200">
                {details.scores?.deliverables_score !== undefined
                  ? `${Math.round(details.scores!.deliverables_score! * 100)}%`
                  : "--"}
              </span>
            </div>

            <div className="p-2.5 rounded-lg bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 space-y-1">
              <span className="text-slate-500 dark:text-neutral-500 block">Criteria Pass Score</span>
              <span className="font-mono text-sm font-bold text-slate-900 dark:text-neutral-200">
                {details.scores?.criteria_score !== undefined
                  ? `${Math.round(details.scores!.criteria_score! * 100)}%`
                  : "--"}
              </span>
            </div>

            <div className="p-2.5 rounded-lg bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 space-y-1">
              <span className="text-slate-500 dark:text-neutral-500 block">Demonstrated Skill Score</span>
              <span className="font-mono text-sm font-bold text-emerald-600 dark:text-emerald-400">
                {details.scores?.demonstrated_skill_score !== null && details.scores?.demonstrated_skill_score !== undefined
                  ? `${Math.round(details.scores!.demonstrated_skill_score! * 100)}%`
                  : "N/A (Project Deliverable Evaluation)"}
              </span>
            </div>

            <div className="p-2.5 rounded-lg bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 space-y-1">
              <span className="text-slate-500 dark:text-neutral-500 block">Composite Confidence</span>
              <span className="font-mono text-sm font-bold text-indigo-600 dark:text-indigo-400">
                {details.scores?.composite_confidence !== null && details.scores?.composite_confidence !== undefined
                  ? `${Math.round(details.scores!.composite_confidence! * 100)}%`
                  : "--"}
              </span>
            </div>
          </div>

          {commitSha && (
            <div className="pt-2 border-t border-slate-200 dark:border-neutral-800 flex items-center justify-between text-[11px] font-mono text-slate-600 dark:text-neutral-400">
              <span>Verified Commit SHA:</span>
              <code className="text-slate-900 dark:text-neutral-200 bg-white dark:bg-neutral-900 px-2 py-0.5 rounded border border-slate-200 dark:border-neutral-800">
                {commitSha}
              </code>
            </div>
          )}

          {details.verified_at && (
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-600 dark:text-neutral-400">
              <span>Analyzed At:</span>
              <span className="text-slate-800 dark:text-neutral-300">
                {new Date(details.verified_at).toLocaleString()}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
