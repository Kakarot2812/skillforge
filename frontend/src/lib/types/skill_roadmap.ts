/**
 * Strongly typed TypeScript contracts for SkillForge AI: Static Skill Roadmap Rebuild.
 * Phase 5: Frontend API Client & TypeScript Contracts.
 *
 * Strictly matches backend Pydantic schemas in `backend/app/schemas/skill_roadmap.py`
 * and REST endpoints in `backend/app/api/v1/roadmaps.py`.
 *
 * Decoupled from P4 Personalized Career Roadmap contracts (`roadmap.ts`).
 */

// -----------------------------------------------------------------------------
// Core Literal & Enum Types
// -----------------------------------------------------------------------------

/**
 * Valid static roadmap skill learning statuses.
 * Matches backend UserRoadmapProgress and RoadmapSkillItem.user_status.
 */
export type RoadmapSkillStatus = "NOT_STARTED" | "LEARNING" | "DONE" | "SKIPPED";

/**
 * Valid practice problem completion statuses.
 * Matches backend UserPracticeProgress and PracticeProblemItem.user_status.
 */
export type PracticeProblemStatus = "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED";

/**
 * Static roadmap view ordering mode:
 * - curated: canonical stage-by-stage pedagogy
 * - recommended: deterministic Kahn topological sort obeying prerequisite DAG
 */
export type RoadmapOrdering = "curated" | "recommended";

/**
 * Resource media types supported by static roadmap learning resources.
 */
export type LearningResourceType = "DOCUMENTATION" | "YOUTUBE";

/**
 * Difficulty tiers for practice problems.
 */
export type PracticeProblemDifficulty = "BEGINNER" | "INTERMEDIATE" | "ADVANCED";

// -----------------------------------------------------------------------------
// Learning Resource Schemas
// -----------------------------------------------------------------------------

export interface LearningResourceItem {
  id: string;
  resource_type: LearningResourceType | string;
  title: string;
  url: string;
  description: string;
}

// -----------------------------------------------------------------------------
// Prerequisite Schemas
// -----------------------------------------------------------------------------

export interface RoadmapPrerequisiteItem {
  skill_id: string;
  skill_name: string;
  skill_slug: string;
  difficulty: string;
}

export type StaticRoadmapPrerequisiteItem = RoadmapPrerequisiteItem;

// -----------------------------------------------------------------------------
// Practice Problem Schemas
// -----------------------------------------------------------------------------

export interface PracticeProblemItem {
  problem_id: string;
  title: string;
  difficulty: PracticeProblemDifficulty | string;
  order: number;
  objective: string;
  problem_statement: string;
  requirements: string[];
  concepts_tested: string[];
  expected_outcome: string;
  optional_hints: string[];
  user_status?: PracticeProblemStatus | string;

  // Optional convenience aliases for UI consumers
  description?: string;
  hints?: string[];
  starter_code?: string | null;
  test_cases?: unknown[];
}

// -----------------------------------------------------------------------------
// Roadmap Skill Schemas
// -----------------------------------------------------------------------------

export interface RoadmapSkillItem {
  id: string;
  stage_id: string;
  roadmap_id: string;
  canonical_skill_id?: string | null;
  name: string;
  slug: string;
  description: string;
  difficulty: string;
  skill_order: number;
  key_topics: string[];
  practice_project?: string | null;
  practice_problems: PracticeProblemItem[];
  role_relevance?: string | null;
  user_status?: RoadmapSkillStatus | string;
  prerequisites: RoadmapPrerequisiteItem[];
  resources: LearningResourceItem[];
}

// -----------------------------------------------------------------------------
// Roadmap Stage Schemas
// -----------------------------------------------------------------------------

export interface RoadmapStageItem {
  id: string;
  roadmap_id: string;
  name: string;
  description?: string | null;
  stage_order: number;
  total_skills: number;
  completed_skills: number;
  skills: RoadmapSkillItem[];
}

// -----------------------------------------------------------------------------
// Roadmap Catalog List Schemas
// -----------------------------------------------------------------------------

export interface RoadmapListItem {
  id: string;
  role_id?: string | null;
  slug: string;
  title: string;
  domain: string;
  category: string;
  description: string;
  version: string;
  has_market_data: boolean;
  total_stages: number;
  total_skills: number;
  last_reviewed: string;
}

export interface RoadmapListResponse {
  data: RoadmapListItem[];
  total: number;
}

// -----------------------------------------------------------------------------
// Roadmap Detail & Summary Schemas
// -----------------------------------------------------------------------------

export interface RoadmapSummary {
  total_skills: number;
  completed_skills: number;
  learning_skills: number;
  skipped_skills: number;
  not_started_skills: number;
  progress_percentage: number;
}

export interface RoadmapDetailData {
  roadmap: RoadmapListItem;
  ordering: RoadmapOrdering | string;
  summary: RoadmapSummary;
  stages: RoadmapStageItem[];
  recommended_skills?: RoadmapSkillItem[] | null;
}

export interface RoadmapDetailResponse {
  data: RoadmapDetailData;
}

// -----------------------------------------------------------------------------
// User Progress Update & Response Schemas
// -----------------------------------------------------------------------------

export interface UserProgressUpdateRequest {
  status: RoadmapSkillStatus;
}

export interface UserProgressItem {
  id: string;
  user_id: string;
  roadmap_skill_id: string;
  status: RoadmapSkillStatus | string;
  created_at: string;
  updated_at: string;
}

export interface UserProgressResponse {
  success: boolean;
  data: UserProgressItem;
}

// -----------------------------------------------------------------------------
// User Practice Progress Update & Response Schemas
// -----------------------------------------------------------------------------

export interface UserPracticeProgressUpdateRequest {
  status: PracticeProblemStatus;
}

export interface UserPracticeProgressItem {
  id: string;
  user_id: string;
  roadmap_skill_id: string;
  problem_id: string;
  status: PracticeProblemStatus | string;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserPracticeProgressResponse {
  success: boolean;
  data: UserPracticeProgressItem;
}

// -----------------------------------------------------------------------------
// User Roadmap Progress Summary & Map Read Models
// -----------------------------------------------------------------------------

export interface UserRoadmapProgressSummary {
  roadmap_id: string;
  total_skills: number;
  completed_skills: number;
  learning_skills: number;
  skipped_skills: number;
  not_started_skills: number;
  progress_percentage: number;
  total_practice_problems: number;
  completed_practice_problems: number;
}

/**
 * Key-value mapping of roadmap_skill_id to current status.
 * Returned by GET /api/v1/users/me/roadmap-progress when summary=false.
 */
export type UserRoadmapProgressMap = Record<string, RoadmapSkillStatus | string>;
