/**
 * Strongly typed TypeScript contracts for Post-MVP Checkpoint P5:
 * GitHub Project Verification.
 *
 * Matches backend schemas in `backend/app/schemas/verification.py`
 * and API contracts in `backend/app/api/v1/roadmap.py`.
 */

export type DeliverableMatchStatus = "PASSED" | "MISSING" | "AMBIGUOUS";

export type CriterionEvaluationStatus =
  | "PASSED"
  | "FAILED"
  | "MANUAL_REVIEW_ONLY"
  | "UNSUPPORTED";

export type VerificationStatus =
  | "VERIFIED"
  | "PARTIAL"
  | "UNVERIFIED"
  | "FAILED";

export interface DeliverableMatchItem {
  deliverable: string;
  status: DeliverableMatchStatus;
  matched_path?: string | null;
  candidate_paths?: string[];
  detail: string;
}

export interface DeliverableCheckDetail {
  total_required: number;
  passed_count: number;
  missing_count: number;
  ambiguous_count: number;
  deliverables_score: number;
  required_deliverables: string[];
  passed_deliverables: string[];
  missing_deliverables: string[];
  ambiguous_deliverables: string[];
  matches: DeliverableMatchItem[];
}

export interface CriterionDetail {
  criterion_key: string;
  status: CriterionEvaluationStatus;
  is_automated: boolean;
  rule_description: string;
  matched_file?: string | null;
  matched_snippet?: string | null;
  reason?: string | null;
}

export interface CriteriaCheckDetail {
  total_criteria: number;
  automated_count: number;
  passed_count: number;
  failed_count: number;
  manual_review_count: number;
  unsupported_count: number;
  criteria_score: number;
  results: CriterionDetail[];
  unsupported_criteria: string[];
  manual_review_criteria: string[];
}

export interface VerificationAuditDetails {
  deliverables?: DeliverableCheckDetail;
  criteria?: CriteriaCheckDetail;
  deliverables_score?: number;
  criteria_score?: number;
  demonstrated_skill_score?: number | null;
  composite_confidence?: number | null;
  commit_sha?: string;
  tree_sha?: string;
  analyzed_at?: string;
  error?: string;
  [key: string]: unknown;
}

export interface MilestoneVerifyRequest {
  repository_id?: string | null;
  branch?: string | null;
}

export interface MilestoneVerificationResponse {
  id: string;
  milestone_id: string;
  roadmap_id: string;
  user_id: string;
  repository_id: string;
  commit_sha: string;
  status: VerificationStatus;
  confidence?: number | null;
  details: VerificationAuditDetails;
  milestone_status: string;
  created_at: string;
}

export interface RoadmapBatchVerifyRequest {
  repository_id?: string | null;
}

export interface RoadmapBatchVerificationResponse {
  roadmap_id: string;
  total_milestones: number;
  verified_count: number;
  partial_count: number;
  unverified_count: number;
  failed_count: number;
  results: MilestoneVerificationResponse[];
}
