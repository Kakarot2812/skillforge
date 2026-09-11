/**
 * Strongly typed TypeScript contracts for Post-MVP Checkpoint P4:
 * Personalized Roadmap + Resources.
 *
 * Matches backend schemas in `backend/app/schemas/roadmap.py`.
 */

export type DependencyType = "HARD" | "RECOMMENDED";

export type MilestoneStatus =
  | "NOT_STARTED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "VERIFIED";

export type RoadmapLifecycleStatus = "ACTIVE" | "COMPLETED" | "ARCHIVED";

export interface RoadmapPrerequisiteItem {
  skill_id: string;
  skill_name: string;
  canonical_slug: string;
  dependency_type: DependencyType;
  is_satisfied: boolean;
}

export interface RoadmapResourceItem {
  id: string;
  title: string;
  url: string;
  resource_type: string;
  provider: string;
  difficulty: string;
  estimated_minutes?: number | null;
}

export interface RoadmapProjectItem {
  id: string;
  title: string;
  description: string;
  difficulty: string;
  deliverables: string[];
  verification_criteria: string[];
  estimated_hours?: number | null;
}

export interface RoadmapMilestoneItem {
  milestone_id?: string | null;
  order_index: number;
  skill_id: string;
  skill_name: string;
  canonical_slug: string;
  category?: string | null;
  gap_status: "MISSING" | "PARTIAL" | string;
  demonstrated_score: number;
  demand_score?: number | null;
  growth_rate?: number | null;
  priority_score?: number | null;
  priority_level?: "HIGH" | "MEDIUM" | "LOW" | string | null;
  is_transitive_prerequisite: boolean;
  reason: string;
  prerequisites: RoadmapPrerequisiteItem[];
  learning_objectives: string[];
  resources: RoadmapResourceItem[];
  project?: RoadmapProjectItem | null;
  status: MilestoneStatus;
}

export interface CanonicalRoadmapData {
  id?: string | null;
  user_id?: string | null;
  role_id: string;
  target_role_title: string;
  location: string;
  status: RoadmapLifecycleStatus;
  roadmap_version: string;
  persisted: boolean;
  total_milestones: number;
  high_priority_count: number;
  medium_priority_count: number;
  low_priority_count: number;
  transitive_prerequisite_count: number;
  milestones: RoadmapMilestoneItem[];
  generated_at: string;
}

export interface RoadmapGenerateRequest {
  role_id: string;
  location?: string;
  user_id?: string | null;
  resume_id?: string | null;
  include_resume?: boolean;
  include_github?: boolean;
  github_username?: string | null;
}

export interface RoadmapResponse {
  data: CanonicalRoadmapData;
  meta?: Record<string, unknown>;
}

export interface AIRoadmapExplainRequest {
  user_query?: string | null;
  temperature?: number;
}

export interface AIRoadmapExplainResponse {
  roadmap_id?: string | null;
  target_role_title: string;
  content: string;
  model: string;
  status: "EXPLANATORY" | string;
  referenced_skill_slugs: string[];
  generated_at: string;
}

export interface ApprovedResourceListResponse {
  skill_id: string;
  skill_name: string;
  total_resources: number;
  resources: RoadmapResourceItem[];
}
