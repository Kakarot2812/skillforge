"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Bot,
  Send,
  Loader2,
  Sparkles,
  AlertCircle,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";
import {
  sendCareerChat,
  fetchSkillGaps,
  fetchPrioritizedGaps,
  fetchRoleDemand,
  fetchRoles,
  JobRole,
  SkillGapItem,
  PrioritizedGapItem,
  RoleSkillDemandItem,
} from "@/lib/api";
import {
  CareerChatRequest,
  VerifiedContext,
  VerifiedCandidateContext,
  VerifiedSkillFact,
  VerifiedPriorityFact,
  VerifiedMarketFact,
  SkillClassification,
  PriorityTier,
  GrowthClass,
} from "@/lib/types/chat";
import { getCandidateUserId, isValidUUID } from "@/lib/identity";
import CareerAssistantMessage, { ChatMessageItem } from "./CareerAssistantMessage";
import CareerAssistantSuggestions from "./CareerAssistantSuggestions";

export interface CareerAssistantProps {
  selectedRoleId?: string;
  candidateReady?: boolean;
  hasResume?: boolean;
  resumeId?: string | null;
  connectedGitHubUsername?: string | null;
}

export default function CareerAssistant({
  selectedRoleId,
  candidateReady = false,
  hasResume = false,
  resumeId = null,
  connectedGitHubUsername = null,
}: CareerAssistantProps) {
  // Conversation state stored ONLY in React state (no local storage, no DB)
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [query, setQuery] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Deterministic context data from backend APIs
  const [roles, setRoles] = useState<JobRole[]>([]);
  const [skillsData, setSkillsData] = useState<SkillGapItem[]>([]);
  const [prioritiesData, setPrioritiesData] = useState<PrioritizedGapItem[]>([]);
  const [demandData, setDemandData] = useState<RoleSkillDemandItem[]>([]);
  const [contextLoading, setContextLoading] = useState<boolean>(false);

  // Auto-scroll ref
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Load available roles on mount for title resolution
  useEffect(() => {
    let isCancelled = false;
    Promise.resolve().then(() => {
      fetchRoles().then((res) => {
        if (!isCancelled && res.success && res.data && Array.isArray(res.data.data)) {
          setRoles(res.data.data);
        }
      });
    });
    return () => {
      isCancelled = true;
    };
  }, []);

  // Fetch deterministic ground-truth data when role or candidate evidence changes
  const loadDeterministicContext = useCallback(async (roleId: string) => {
    if (!roleId) {
      setSkillsData([]);
      setPrioritiesData([]);
      setDemandData([]);
      return;
    }

    setContextLoading(true);
    const effectiveUserId = getCandidateUserId() || undefined;

    try {
      const [gapsRes, prioRes, demandRes] = await Promise.allSettled([
        fetchSkillGaps(
          roleId,
          "India",
          effectiveUserId,
          hasResume,
          Boolean(connectedGitHubUsername),
          connectedGitHubUsername,
          resumeId
        ),
        fetchPrioritizedGaps(
          roleId,
          "India",
          effectiveUserId,
          hasResume,
          Boolean(connectedGitHubUsername),
          connectedGitHubUsername,
          resumeId
        ),
        fetchRoleDemand(roleId, "India"),
      ]);

      if (gapsRes.status === "fulfilled" && gapsRes.value.success && gapsRes.value.data) {
        setSkillsData(gapsRes.value.data.skills || []);
      } else {
        setSkillsData([]);
      }

      if (prioRes.status === "fulfilled" && prioRes.value.success && prioRes.value.data) {
        setPrioritiesData(prioRes.value.data.gaps || []);
      } else {
        setPrioritiesData([]);
      }

      if (demandRes.status === "fulfilled" && demandRes.value.success && demandRes.value.data) {
        setDemandData(demandRes.value.data.skills || []);
      } else {
        setDemandData([]);
      }
    } catch {
      // Deterministic failure falls back gracefully
    } finally {
      setContextLoading(false);
    }
  }, [hasResume, connectedGitHubUsername, resumeId]);

  useEffect(() => {
    let isCancelled = false;
    Promise.resolve().then(() => {
      if (isCancelled) return;
      if (selectedRoleId) {
        loadDeterministicContext(selectedRoleId);
      } else {
        setSkillsData([]);
        setPrioritiesData([]);
        setDemandData([]);
      }
    });
    return () => {
      isCancelled = true;
    };
  }, [selectedRoleId, loadDeterministicContext]);

  // Map of skill UUID -> display name for rendering referenced skill chips
  const skillNameMap = React.useMemo(() => {
    const map = new Map<string, string>();
    skillsData.forEach((s) => map.set(s.skill_id, s.skill_name));
    prioritiesData.forEach((p) => map.set(p.skill_id, p.skill_name));
    demandData.forEach((d) => map.set(d.skill_id, d.skill_name));
    return map;
  }, [skillsData, prioritiesData, demandData]);

  // Current role title
  const currentRoleTitle = React.useMemo(() => {
    if (!selectedRoleId) return null;
    const found = roles.find((r) => r.role_id === selectedRoleId);
    return found ? found.title : null;
  }, [selectedRoleId, roles]);

  // Construct VerifiedContext conforming strictly to backend contract
  const buildVerifiedContext = useCallback((): VerifiedContext => {
    const userId = getCandidateUserId();
    const candidate: VerifiedCandidateContext = {
      candidate_id: userId && isValidUUID(userId) ? userId : null,
      target_role_id: selectedRoleId && isValidUUID(selectedRoleId) ? selectedRoleId : null,
      target_role_name: currentRoleTitle || null,
      location: "India",
      has_resume: hasResume,
      has_github: Boolean(connectedGitHubUsername),
      provenance: "DETERMINISTIC_ANALYSIS",
    };

    // 1. Skill facts (capped at 50, strictly typed)
    const skills: VerifiedSkillFact[] = skillsData.slice(0, 50).map((s) => ({
      skill_id: s.skill_id,
      skill_name: s.skill_name,
      canonical_slug: s.canonical_slug,
      classification: s.status as SkillClassification,
      category: s.category || null,
      demonstrated_score: Math.max(0, Math.min(1, s.demonstrated_score || 0)),
      claimed: Boolean(s.claimed),
      claim_confidence: Math.max(0, Math.min(1, s.claim_confidence || 0)),
      evidence_count: s.evidence_count || 0,
      evidence_level: s.evidence_level || null,
      provenance: "DETERMINISTIC_ANALYSIS",
    }));

    // Lookup to enforce cross-fact consistency required by validation.py
    const skillClassificationMap = new Map<string, SkillClassification>();
    skills.forEach((s) => skillClassificationMap.set(s.skill_id, s.classification));

    // 2. Priority facts (capped at 50)
    const priorities: VerifiedPriorityFact[] = prioritiesData.slice(0, 50).map((p) => {
      const consistentStatus =
        skillClassificationMap.get(p.skill_id) ||
        ((p.status === "MISSING" ? "MISSING" : "PARTIAL") as SkillClassification);

      return {
        skill_id: p.skill_id,
        skill_name: p.skill_name,
        priority_score: Math.max(0, Math.min(1, p.priority_score || 0)),
        priority_level: p.priority_level as PriorityTier,
        gap_status: consistentStatus,
        demand_score: Math.max(0, Math.min(1, p.demand_score || 0)),
        growth_rate: p.growth_rate || 0,
        demonstrated_score: Math.max(0, Math.min(1, p.demonstrated_score || 0)),
        scoring_version: "v1",
        provenance: "DETERMINISTIC_ANALYSIS",
      };
    });

    const priorityDemandMap = new Map<string, number>();
    priorities.forEach((p) => priorityDemandMap.set(p.skill_id, p.demand_score));

    // 3. Market facts (capped at 50)
    const market: VerifiedMarketFact[] = demandData.slice(0, 50).map((m) => {
      // Must match priority demand_score within 1e-4 if present in both
      const consistentDemand = priorityDemandMap.has(m.skill_id)
        ? priorityDemandMap.get(m.skill_id)!
        : Math.max(0, Math.min(1, m.demand_score || 0));

      const growthRate = m.growth_rate || 0;
      const growthClass: GrowthClass =
        growthRate > 0.05 ? "RISING" : growthRate < -0.05 ? "DECLINING" : "STABLE";

      return {
        skill_id: m.skill_id,
        skill_name: m.skill_name,
        source: "adzuna",
        demand_score: consistentDemand,
        demand_share: null,
        growth_rate: growthRate,
        growth_class: growthClass,
        sample_size: m.sample_size || null,
        snapshot_at: m.data_updated_at || null,
        provenance: "MARKET",
      };
    });

    return {
      candidate,
      skills,
      evidence: [],
      market,
      priorities,
      context_id: null,
      created_at: new Date().toISOString(),
      provenance: "DETERMINISTIC_ANALYSIS",
    };
  }, [
    selectedRoleId,
    currentRoleTitle,
    hasResume,
    connectedGitHubUsername,
    skillsData,
    prioritiesData,
    demandData,
  ]);

  // Submit candidate query to Qwen chatbot
  const handleSend = async (queryToSend?: string) => {
    const userQuery = (queryToSend || query).trim();
    if (!userQuery || loading) return;

    // Enforce max length bound (1000 characters)
    if (userQuery.length > 1000) {
      setError("Question exceeds the 1000-character maximum length limit.");
      return;
    }

    const timestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userMessage: ChatMessageItem = {
      id: `usr-${Date.now()}`,
      sender: "user",
      content: userQuery,
      timestamp,
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuery("");
    setLoading(true);
    setError(null);

    const verifiedContext = buildVerifiedContext();

    const requestPayload: CareerChatRequest = {
      verified_context: verifiedContext,
      user_query: userQuery,
      max_tokens: 1024,
      temperature: 0.2,
    };

    try {
      const res = await sendCareerChat(requestPayload);

      if (res.success && res.data) {
        const assistantMessage: ChatMessageItem = {
          id: `asst-${Date.now()}`,
          sender: "assistant",
          content: res.data.explanation,
          status: res.data.status,
          referencedSkillIds: res.data.referenced_skill_ids,
          model: res.data.model,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        // Handle specific error codes gracefully without exposing stack traces
        let userErrorMessage = "AI coaching is temporarily unavailable. Your deterministic SkillForge analysis is still available.";

        if (res.status === 422) {
          userErrorMessage = res.error || "The submitted query or context could not be processed.";
        } else if (res.status === 429) {
          userErrorMessage = "Rate limit reached. Please wait a moment before asking another question.";
        } else if (res.status === 400 || res.status === 401 || res.status === 403) {
          userErrorMessage = res.error || "Request could not be authorized.";
        } else if (res.status === 502 || res.status === 503 || res.status === 504 || res.status === 0) {
          userErrorMessage = "AI coaching is temporarily unavailable. Your deterministic SkillForge analysis is still available.";
        } else if (res.error) {
          userErrorMessage = res.error;
        }

        setError(userErrorMessage);
      }
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "AI coaching is temporarily unavailable. Your deterministic SkillForge analysis is still available."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClear = () => {
    setMessages([]);
    setError(null);
  };

  return (
    <div id="ai-career-assistant-section" className="scroll-mt-20 space-y-4">
      {/* Container Card */}
      <div className="bg-neutral-900/70 border border-neutral-800 rounded-3xl p-6 sm:p-8 backdrop-blur-md relative overflow-hidden shadow-2xl space-y-6">
        {/* Subtle Background Glow */}
        <div className="absolute top-0 right-0 -mt-12 -mr-12 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

        {/* Section Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-6 border-b border-neutral-800 relative z-10">
          <div className="space-y-1.5 max-w-2xl">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20 shadow-inner">
                <Bot className="h-5 w-5" />
              </div>
              <h2 className="text-xl font-bold text-white tracking-tight">
                AI Career Intelligence Assistant
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/20 font-semibold uppercase">
                Qwen 3 8B Explanatory Layer
              </span>
            </div>
            <p className="text-xs sm:text-sm text-neutral-400 leading-relaxed">
              Natural-language coaching grounded strictly in your verified SkillForge evidence. Ask questions regarding your skill gaps, priority sequencing, market signals, or roadmap prerequisites.
            </p>
          </div>

          {/* Context Scope Indicator & Clear Button */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="px-3 py-1.5 rounded-xl bg-neutral-950/80 border border-neutral-800 flex items-center gap-2 text-xs">
              <span className={`h-2 w-2 rounded-full ${selectedRoleId ? "bg-emerald-400" : "bg-amber-400"}`} />
              <span className="text-neutral-300 font-medium">
                {currentRoleTitle ? `Role: ${currentRoleTitle}` : "General Context"}
                {candidateReady ? " • Profile Active" : ""}
              </span>
              {contextLoading && <Loader2 className="h-3 w-3 text-neutral-400 animate-spin" />}
            </div>

            {messages.length > 0 && (
              <button
                type="button"
                onClick={handleClear}
                disabled={loading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-neutral-800/80 hover:bg-neutral-700 text-neutral-300 hover:text-white text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
                title="Reset conversation state"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Clear</span>
              </button>
            )}
          </div>
        </div>

        {/* Visible AI Disclaimer (Strict Requirement 7) */}
        <div className="p-3 rounded-xl bg-neutral-950/70 border border-neutral-800 flex items-start sm:items-center gap-2 text-xs text-neutral-400">
          <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5 sm:mt-0" />
          <p className="leading-snug">
            <strong className="text-neutral-300 font-medium">Authoritative Boundary:</strong> AI explanations are grounded in SkillForge&apos;s verified evidence. They do not change your skill status, market scores, priorities, or roadmap.
          </p>
        </div>

        {/* Conversation Thread Window */}
        <div className="min-h-[260px] max-h-[500px] overflow-y-auto space-y-4 pr-1 rounded-2xl bg-neutral-950/50 p-4 sm:p-6 border border-neutral-800/80">
          {/* Empty State */}
          {messages.length === 0 && !loading && (
            <div className="py-10 text-center space-y-4 max-w-md mx-auto">
              <div className="h-12 w-12 rounded-2xl bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center mx-auto shadow-inner">
                <Sparkles className="h-6 w-6" />
              </div>
              <div className="space-y-1.5">
                <h3 className="text-sm font-bold text-white">How can I assist your career progression?</h3>
                <p className="text-xs text-neutral-400 leading-relaxed">
                  I can analyze your verified resume claims, GitHub repositories, and market demand to explain why specific skills are prioritized or how to tackle your roadmap milestones.
                </p>
              </div>

              <div className="pt-2">
                <CareerAssistantSuggestions
                  onSelectSuggestion={(q) => handleSend(q)}
                  disabled={loading}
                />
              </div>
            </div>
          )}

          {/* Render Chronological Messages */}
          {messages.map((msg) => (
            <CareerAssistantMessage
              key={msg.id}
              message={msg}
              skillNameMap={skillNameMap}
            />
          ))}

          {/* Loading Indicator */}
          {loading && (
            <div className="flex items-center gap-3 p-4 rounded-2xl bg-neutral-900/60 border border-neutral-800/80 mr-4 sm:mr-12 animate-pulse">
              <div className="h-8 w-8 rounded-xl bg-purple-500/20 text-purple-300 flex items-center justify-center">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
              <div className="space-y-1">
                <span className="text-xs font-semibold text-neutral-200">
                  Reasoning over verified SkillForge evidence...
                </span>
                <p className="text-[11px] text-neutral-400">
                  Checking deterministic sufficiency and assembling grounded explanation.
                </p>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Error Alert Banner */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 flex items-start gap-3 text-xs">
            <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <strong className="text-rose-200 font-medium">Assistant Service Notice:</strong>
              <p className="mt-0.5 text-neutral-300">{error}</p>
            </div>
            <button
              type="button"
              onClick={() => setError(null)}
              className="text-neutral-400 hover:text-neutral-200 text-xs transition-colors cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Suggested Prompts Bar (when conversation is active) */}
        {messages.length > 0 && (
          <CareerAssistantSuggestions
            onSelectSuggestion={(q) => handleSend(q)}
            disabled={loading}
          />
        )}

        {/* Input Area */}
        <div className="space-y-2">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex gap-2 items-end"
          >
            <div className="flex-1 relative">
              <label htmlFor="assistant-query-input" className="sr-only">
                Ask a career question
              </label>
              <textarea
                id="assistant-query-input"
                rows={2}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your skill gaps, priority rationale, or roadmap prerequisites... (Enter to send, Shift+Enter for new line)"
                disabled={loading}
                maxLength={1000}
                className="w-full px-4 py-3 rounded-2xl bg-neutral-950 border border-neutral-800 text-neutral-100 placeholder-neutral-500 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-500/50 resize-none transition-all disabled:opacity-50"
              />
              <div className="absolute right-3 bottom-2 text-[10px] font-mono text-neutral-500 pointer-events-none">
                {query.length}/1000
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="h-11 px-5 rounded-xl bg-purple-600 hover:bg-purple-500 active:bg-purple-700 text-white text-xs font-bold transition-all shadow-lg shadow-purple-950/40 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5 shrink-0"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <span>Send</span>
                  <Send className="h-3.5 w-3.5" />
                </>
              )}
            </button>
          </form>

          <div className="flex items-center justify-between text-[11px] text-neutral-500 px-1">
            <span>Powered by local Qwen 3 8B • Zero chat persistence</span>
            <span>Deterministic facts remain authoritative</span>
          </div>
        </div>
      </div>
    </div>
  );
}
