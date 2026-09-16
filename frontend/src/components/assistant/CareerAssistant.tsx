"use client";

import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  Bot,
  Send,
  Loader2,
  Sparkles,
  AlertCircle,
  RotateCcw,
  ShieldCheck,
  History,
  MessageSquare,
} from "lucide-react";
import {
  sendCareerChat,
  fetchConversations,
  createConversation,
  fetchConversationMessages,
  deleteConversation,
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
  ConversationItem,
} from "@/lib/types/chat";
import { getCandidateUserId, isValidUUID, ensureCandidateIdentity } from "@/lib/identity";
import CareerAssistantMessage, { ChatMessageItem } from "./CareerAssistantMessage";
import CareerAssistantSuggestions from "./CareerAssistantSuggestions";
import CareerAssistantHistory from "./CareerAssistantHistory";

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
  // Active conversation thread state
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [query, setQuery] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingMessages, setLoadingMessages] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Persistent Conversation History State (Checkpoint 6)
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [loadingConversations, setLoadingConversations] = useState<boolean>(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [showMobileHistory, setShowMobileHistory] = useState<boolean>(false);

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
  }, [messages, loading, loadingMessages]);

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

  // Load conversation history from PostgreSQL on mount
  const loadConversations = useCallback(async () => {
    setLoadingConversations(true);
    setHistoryError(null);
    try {
      await ensureCandidateIdentity();
      const res = await fetchConversations();
      if (res.success && res.data) {
        setConversations(res.data);
      } else if (res.error) {
        setHistoryError(res.error);
      }
    } catch {
      setHistoryError("Failed to load conversation history.");
    } finally {
      setLoadingConversations(false);
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

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
  const skillNameMap = useMemo(() => {
    const map = new Map<string, string>();
    skillsData.forEach((s) => map.set(s.skill_id, s.skill_name));
    prioritiesData.forEach((p) => map.set(p.skill_id, p.skill_name));
    demandData.forEach((d) => map.set(d.skill_id, d.skill_name));
    return map;
  }, [skillsData, prioritiesData, demandData]);

  // Current role title
  const currentRoleTitle = useMemo(() => {
    if (!selectedRoleId) return null;
    const found = roles.find((r) => r.role_id === selectedRoleId);
    return found ? found.title : null;
  }, [selectedRoleId, roles]);

  // Active conversation title
  const activeConversationTitle = useMemo(() => {
    if (!activeConversationId) return null;
    const found = conversations.find((c) => c.id === activeConversationId);
    return found?.title?.trim() || "Active Conversation";
  }, [activeConversationId, conversations]);

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

    // Lookup to enforce cross-fact consistency
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

  // Handle New Chat: Clears active thread, prepares for lazy creation
  const handleNewChat = () => {
    setActiveConversationId(null);
    setMessages([]);
    setError(null);
    setQuery("");
  };

  // Handle Opening an Existing Conversation: loads chronological messages from backend
  const handleSelectConversation = async (conversationId: string) => {
    if (conversationId === activeConversationId) return;
    setActiveConversationId(conversationId);
    setLoadingMessages(true);
    setError(null);

    try {
      const res = await fetchConversationMessages(conversationId);
      if (res.success && res.data) {
        const translated: ChatMessageItem[] = res.data.map((m) => ({
          id: m.id,
          sender: m.role === "user" ? "user" : "assistant",
          content: m.content,
          status: m.role === "assistant" ? "EXPLANATORY" : undefined,
          model: m.role === "assistant" ? "qwen3:8b" : undefined,
          timestamp: new Date(m.created_at).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
        }));
        setMessages(translated);
      } else {
        setError(res.error || "Failed to load messages for this conversation.");
      }
    } catch {
      setError("Error connecting to chat history service.");
    } finally {
      setLoadingMessages(false);
    }
  };

  // Handle Deleting a Conversation
  const handleDeleteConversation = async (conversationId: string) => {
    setDeletingId(conversationId);
    try {
      const res = await deleteConversation(conversationId);
      if (res.success) {
        setConversations((prev) => prev.filter((c) => c.id !== conversationId));
        if (activeConversationId === conversationId) {
          setActiveConversationId(null);
          setMessages([]);
        }
      } else {
        setHistoryError(res.error || "Failed to delete conversation.");
      }
    } catch {
      setHistoryError("Error deleting conversation.");
    } finally {
      setDeletingId(null);
    }
  };

  // Submit candidate query to Qwen chatbot
  const handleSend = async (queryToSend?: string) => {
    const userQuery = (queryToSend || query).trim();
    if (!userQuery || loading || loadingMessages) return;

    // Enforce max length bound (1000 characters)
    if (userQuery.length > 1000) {
      setError("Question exceeds the 1000-character maximum length limit.");
      return;
    }

    const timestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const tempUserMessage: ChatMessageItem = {
      id: `usr-${Date.now()}`,
      sender: "user",
      content: userQuery,
      timestamp,
    };

    // Optimistically show user message
    setMessages((prev) => [...prev, tempUserMessage]);
    setQuery("");
    setLoading(true);
    setError(null);

    let effectiveConvId = activeConversationId;

    // Lazy conversation creation if no conversation is currently active
    if (!effectiveConvId) {
      const fallbackTitle =
        userQuery.length > 40
          ? `${userQuery.slice(0, 38).trim()}...`
          : userQuery;

      try {
        const convRes = await createConversation(fallbackTitle);
        if (convRes.success && convRes.data) {
          effectiveConvId = convRes.data.id;
          setActiveConversationId(effectiveConvId);
          setConversations((prev) => [convRes.data!, ...prev]);
        }
      } catch {
        // If creation fails, proceed to chat; error will be caught below
      }
    }

    const verifiedContext = buildVerifiedContext();

    const requestPayload: CareerChatRequest = {
      verified_context: verifiedContext,
      user_query: userQuery,
      max_tokens: 1024,
      temperature: 0.2,
      conversation_id: effectiveConvId,
    };

    try {
      const res = await sendCareerChat(requestPayload);

      if (res.success && res.data) {
        const assistantMessage: ChatMessageItem = {
          id: res.data.message_id || `asst-${Date.now()}`,
          sender: "assistant",
          content: res.data.explanation,
          status: res.data.status,
          referencedSkillIds: res.data.referenced_skill_ids,
          model: res.data.model,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        setMessages((prev) => [...prev, assistantMessage]);

        // Move active conversation to top of history list to reflect updated_at
        if (effectiveConvId) {
          setConversations((prev) => {
            const existing = prev.find((c) => c.id === effectiveConvId);
            if (!existing) return prev;
            const updated = { ...existing, updated_at: new Date().toISOString() };
            return [updated, ...prev.filter((c) => c.id !== effectiveConvId)];
          });
        }
      } else {
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

  return (
    <div id="ai-career-assistant-section" className="scroll-mt-20 space-y-4">
      {/* Container Card */}
      <div className="bg-white/80 dark:bg-neutral-900/70 border border-slate-200/80 dark:border-neutral-800 rounded-3xl p-5 sm:p-7 backdrop-blur-md relative overflow-hidden shadow-xl dark:shadow-2xl space-y-5">
        {/* Subtle Background Glow */}
        <div className="absolute top-0 right-0 -mt-12 -mr-12 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-neutral-800 relative z-10">
          <div className="space-y-1 max-w-xl">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20 shadow-inner">
                <Bot className="h-5 w-5" />
              </div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
                AI Career Intelligence Assistant
              </h2>
            </div>
            <p className="text-xs text-slate-600 dark:text-neutral-400 leading-relaxed">
              Natural-language coaching grounded strictly in your verified SkillForge evidence with persistent session history.
            </p>
          </div>

          {/* Controls: Context Indicator + Mobile History Drawer Toggle */}
          <div className="flex items-center gap-2">
            <div className="px-3 py-1.5 rounded-xl bg-slate-50 dark:bg-neutral-950/80 border border-slate-200 dark:border-neutral-800 flex items-center gap-2 text-xs">
              <span
                className={`h-2 w-2 rounded-full ${
                  selectedRoleId ? "bg-emerald-500 dark:bg-emerald-400" : "bg-amber-500 dark:bg-amber-400"
                }`}
              />
              <span className="text-slate-700 dark:text-neutral-300 font-medium">
                {currentRoleTitle ? `Role: ${currentRoleTitle}` : "General Context"}
                {candidateReady ? " • Profile Active" : ""}
              </span>
              {contextLoading && <Loader2 className="h-3 w-3 text-slate-400 animate-spin" />}
            </div>

            {/* Toggle History on Tablet/Mobile */}
            <button
              type="button"
              onClick={() => setShowMobileHistory((prev) => !prev)}
              className="lg:hidden flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-neutral-800 hover:bg-slate-200 dark:hover:bg-neutral-700 text-slate-700 dark:text-neutral-300 text-xs font-semibold transition-colors cursor-pointer"
              title="Toggle chat history"
              aria-label="Toggle chat history"
            >
              <History className="h-3.5 w-3.5" />
              <span>History</span>
              {conversations.length > 0 && (
                <span className="ml-0.5 px-1.5 py-0.2 rounded-full bg-purple-500/20 text-purple-700 dark:text-purple-300 text-[10px] font-mono">
                  {conversations.length}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Visible AI Grounding Disclaimer */}
        <div className="p-3 rounded-xl bg-slate-50 dark:bg-neutral-950/70 border border-slate-200 dark:border-neutral-800 flex items-start sm:items-center gap-2 text-xs text-slate-600 dark:text-neutral-400">
          <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5 sm:mt-0" />
          <p className="leading-snug">
            <strong className="text-slate-800 dark:text-neutral-300 font-medium">Authoritative Boundary:</strong> AI explanations are grounded in SkillForge&apos;s verified evidence. They do not alter canonical skill records or priorities.
          </p>
        </div>

        {/* Two-Pane Workspace Layout (Desktop Sidebar + Active Thread) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 relative">
          {/* Desktop Left Pane: Persistent Chat History Sidebar */}
          <div className="hidden lg:block lg:col-span-4 xl:col-span-3 h-[520px]">
            <CareerAssistantHistory
              conversations={conversations}
              activeConversationId={activeConversationId}
              loading={loadingConversations}
              deletingId={deletingId}
              error={historyError}
              onSelectConversation={handleSelectConversation}
              onNewChat={handleNewChat}
              onDeleteConversation={handleDeleteConversation}
              onRetryLoad={loadConversations}
            />
          </div>

          {/* Mobile Collapsible History Drawer */}
          {showMobileHistory && (
            <div className="lg:hidden col-span-1 z-20 animate-in fade-in slide-in-from-top-3 duration-200">
              <CareerAssistantHistory
                conversations={conversations}
                activeConversationId={activeConversationId}
                loading={loadingConversations}
                deletingId={deletingId}
                error={historyError}
                onSelectConversation={handleSelectConversation}
                onNewChat={handleNewChat}
                onDeleteConversation={handleDeleteConversation}
                onRetryLoad={loadConversations}
                onCloseMobileDrawer={() => setShowMobileHistory(false)}
              />
            </div>
          )}

          {/* Right Pane: Active Conversation Thread */}
          <div className="col-span-1 lg:col-span-8 xl:col-span-9 flex flex-col justify-between space-y-4">
            {/* Thread Header: Shows active conversation title or New Chat indicator */}
            <div className="flex items-center justify-between px-3 py-1.5 rounded-xl bg-slate-50/80 dark:bg-neutral-950/60 border border-slate-200/80 dark:border-neutral-800/80 text-xs">
              <div className="flex items-center gap-2 min-w-0">
                <MessageSquare className="h-3.5 w-3.5 text-purple-600 dark:text-purple-400 shrink-0" />
                <span className="font-semibold text-slate-800 dark:text-neutral-200 truncate">
                  {activeConversationTitle || "New Conversation"}
                </span>
                {activeConversationId && (
                  <span className="text-[10px] font-mono text-slate-400 dark:text-neutral-500">
                    • Persistent Session
                  </span>
                )}
              </div>

              {activeConversationId && (
                <button
                  type="button"
                  onClick={handleNewChat}
                  className="flex items-center gap-1 text-[11px] font-medium text-purple-600 dark:text-purple-400 hover:underline cursor-pointer"
                >
                  <RotateCcw className="h-3 w-3" />
                  <span>Reset to New Chat</span>
                </button>
              )}
            </div>

            {/* Conversation Thread Window */}
            <div className="h-[380px] overflow-y-auto space-y-4 pr-1 rounded-2xl bg-slate-50/50 dark:bg-neutral-950/50 p-4 sm:p-5 border border-slate-200 dark:border-neutral-800/80">
              {/* Message Loading Skeleton */}
              {loadingMessages ? (
                <div className="py-16 flex flex-col items-center justify-center gap-2 text-slate-500 dark:text-neutral-400 text-xs">
                  <Loader2 className="h-5 w-5 animate-spin text-purple-500" />
                  <span>Loading conversation history...</span>
                </div>
              ) : messages.length === 0 && !loading ? (
                /* Empty Thread State */
                <div className="py-10 text-center space-y-4 max-w-md mx-auto">
                  <div className="h-11 w-11 rounded-2xl bg-purple-500/10 border border-purple-500/20 text-purple-600 dark:text-purple-400 flex items-center justify-center mx-auto shadow-inner">
                    <Sparkles className="h-5 w-5" />
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                      How can I assist your career progression?
                    </h3>
                    <p className="text-xs text-slate-600 dark:text-neutral-400 leading-relaxed">
                      Ask about your skill gaps, priority sequencing, market signals, or roadmap prerequisites. Your chat is saved automatically.
                    </p>
                  </div>

                  <div className="pt-2">
                    <CareerAssistantSuggestions
                      onSelectSuggestion={(q) => handleSend(q)}
                      disabled={loading}
                    />
                  </div>
                </div>
              ) : (
                /* Chronological Messages */
                messages.map((msg) => (
                  <CareerAssistantMessage
                    key={msg.id}
                    message={msg}
                    skillNameMap={skillNameMap}
                  />
                ))
              )}

              {/* Reasoning Loader Indicator */}
              {loading && (
                <div className="flex items-center gap-3 p-4 rounded-2xl bg-slate-100/80 dark:bg-neutral-900/60 border border-slate-200 dark:border-neutral-800/80 mr-4 sm:mr-12 animate-pulse">
                  <div className="h-8 w-8 rounded-xl bg-purple-500/20 text-purple-700 dark:text-purple-300 flex items-center justify-center">
                    <Loader2 className="h-4 w-4 animate-spin" />
                  </div>
                  <div className="space-y-0.5">
                    <span className="text-xs font-semibold text-slate-800 dark:text-neutral-200">
                      Reasoning over verified SkillForge evidence...
                    </span>
                    <p className="text-[11px] text-slate-500 dark:text-neutral-400">
                      Assembling personalized explanation grounded in your profile and verified facts.
                    </p>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Error Alert Banner */}
            {error && (
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-700 dark:text-rose-300 flex items-start gap-3 text-xs">
                <AlertCircle className="h-4 w-4 text-rose-500 dark:text-rose-400 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <strong className="text-rose-800 dark:text-rose-200 font-medium">Assistant Service Notice:</strong>
                  <p className="mt-0.5 text-slate-700 dark:text-neutral-300">{error}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setError(null)}
                  className="text-slate-400 hover:text-slate-600 dark:text-neutral-400 dark:hover:text-neutral-200 text-xs transition-colors cursor-pointer"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* Suggested Prompts Bar (when conversation is active) */}
            {messages.length > 0 && !loading && (
              <CareerAssistantSuggestions
                onSelectSuggestion={(q) => handleSend(q)}
                disabled={loading}
              />
            )}

            {/* Input Composer Area */}
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
                    disabled={loading || loadingMessages}
                    maxLength={1000}
                    className="w-full px-4 py-2.5 rounded-2xl bg-slate-50 dark:bg-neutral-950 border border-slate-200 dark:border-neutral-800 text-slate-900 dark:text-neutral-100 placeholder-slate-400 dark:placeholder-neutral-500 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-500/50 resize-none transition-all disabled:opacity-50"
                  />
                  <div className="absolute right-3 bottom-2 text-[10px] font-mono text-slate-400 dark:text-neutral-500 pointer-events-none">
                    {query.length}/1000
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading || loadingMessages || !query.trim()}
                  className="h-10 px-5 rounded-xl bg-purple-600 hover:bg-purple-500 active:bg-purple-700 text-white text-xs font-bold transition-all shadow-md dark:shadow-purple-950/40 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5 shrink-0"
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

              {/* Accurate Persistence Footer (Replacing legacy 'Zero chat persistence' banner) */}
              <div className="flex items-center justify-between text-[11px] text-slate-400 dark:text-neutral-500 px-1">
                <span>Powered by local Qwen 3 8B • Conversation history is saved securely.</span>
                <span>Deterministic facts remain authoritative</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
