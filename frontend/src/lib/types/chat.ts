/**
 * Strongly typed TypeScript contracts for Post-MVP Checkpoint P2:
 * Qwen Evidence-Grounded Career Chatbot.
 *
 * Matches backend schemas in `backend/app/ai/chatbot/models.py`
 * and `backend/app/ai/context/models.py`.
 */

export type ChatResponseStatus = "EXPLANATORY" | "INSUFFICIENT_EVIDENCE";

export type FactProvenance =
  | "RESUME"
  | "GITHUB"
  | "MARKET"
  | "DETERMINISTIC_ANALYSIS";

export type SkillClassification = "STRONG" | "PARTIAL" | "MISSING";

export type PriorityTier = "HIGH" | "MEDIUM" | "LOW";

export type GrowthClass = "RISING" | "STABLE" | "DECLINING";

export interface ChatUsageStats {
  total_duration?: number | null;
  load_duration?: number | null;
  prompt_eval_count?: number | null;
  eval_count?: number | null;
}

export interface VerifiedCandidateContext {
  candidate_id?: string | null;
  target_role_id?: string | null;
  target_role_name?: string | null;
  location: string;
  has_resume: boolean;
  has_github: boolean;
  provenance: FactProvenance;
}

export interface VerifiedSkillFact {
  skill_id: string;
  skill_name: string;
  canonical_slug: string;
  classification: SkillClassification;
  category?: string | null;
  demonstrated_score: number;
  claimed: boolean;
  claim_confidence: number;
  evidence_count: number;
  evidence_level?: string | null;
  provenance: FactProvenance;
}

export interface VerifiedEvidenceFact {
  skill_id: string;
  skill_name: string;
  source: FactProvenance;
  evidence_type: string;
  evidence_id?: string | null;
  artifact_path?: string | null;
  repo_name?: string | null;
  snippet?: string | null;
  confidence_score: number;
  evidence_tier?: string | null;
}

export interface VerifiedMarketFact {
  skill_id: string;
  skill_name: string;
  source: string;
  demand_score: number;
  demand_share?: number | null;
  growth_rate: number;
  growth_class: GrowthClass;
  sample_size?: number | null;
  snapshot_at?: string | null;
  provenance: FactProvenance;
}

export interface VerifiedPriorityFact {
  skill_id: string;
  skill_name: string;
  priority_score: number;
  priority_level: PriorityTier;
  gap_status: SkillClassification;
  demand_score: number;
  growth_rate: number;
  demonstrated_score: number;
  scoring_version: string;
  provenance: FactProvenance;
}

export interface VerifiedContext {
  candidate?: VerifiedCandidateContext | null;
  skills?: VerifiedSkillFact[];
  evidence?: VerifiedEvidenceFact[];
  market?: VerifiedMarketFact[];
  priorities?: VerifiedPriorityFact[];
  context_id?: string | null;
  created_at?: string | null;
  provenance: FactProvenance;
}

export interface CareerChatRequest {
  verified_context: VerifiedContext;
  user_query: string;
  max_tokens?: number;
  temperature?: number;
}

export interface CareerChatResponse {
  explanation: string;
  model: string;
  status: ChatResponseStatus;
  referenced_skill_ids: string[];
  retrieved_evidence: unknown[];
  usage?: ChatUsageStats | null;
}
