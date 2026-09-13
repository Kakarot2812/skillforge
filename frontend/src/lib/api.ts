import { clearCandidateUserId } from "./identity";

export interface HealthResponse {
  status: "ok" | "error";
  raw?: unknown;
}

export interface DbHealthResponse {
  status: "ok" | "error";
  database: "connected" | "disconnected";
  pgvector_installed: boolean;
  database_version?: string;
  error?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Resolves candidate identity headers for client requests.
 * Post-MVP Login Phase 5: Authentication is handled automatically via HttpOnly session cookies (skillforge_session).
 * No X-User-Id header is transmitted by authenticated frontend requests.
 */
async function resolveCandidateHeaders(_userId?: string): Promise<Record<string, string>> {
  return {};
}


/**
 * Check backend application health via GET /health.
 */
export async function checkBackendHealth(): Promise<{
  connected: boolean;
  status: string;
  latencyMs: number;
}> {
  const start = performance.now();
  try {
    const res = await fetch(`${API_BASE_URL}/health`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    const latencyMs = Math.round(performance.now() - start);

    if (!res.ok) {
      return {
        connected: false,
        status: `Error (${res.status})`,
        latencyMs,
      };
    }

    const data: HealthResponse = await res.json();
    return {
      connected: data.status === "ok",
      status: data.status === "ok" ? "Connected" : "Degraded",
      latencyMs,
    };
  } catch (err: unknown) {
    const latencyMs = Math.round(performance.now() - start);
    const message = err instanceof Error ? err.message : "Connection failed";
    return {
      connected: false,
      status: message.includes("Failed to fetch") ? "Disconnected" : "Unreachable",
      latencyMs,
    };
  }
}

/**
 * Check PostgreSQL and pgvector extension health via GET /health/db.
 */
export async function checkDatabaseHealth(): Promise<DbHealthResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/health/db`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    if (!res.ok) {
      return {
        status: "error",
        database: "disconnected",
        pgvector_installed: false,
        error: `HTTP ${res.status}: ${res.statusText}`,
      };
    }

    return await res.json();
  } catch (err: unknown) {
    return {
      status: "error",
      database: "disconnected",
      pgvector_installed: false,
      error: err instanceof Error ? err.message : "Database check failed",
    };
  }
}

export interface ClaimedSkillItem {
  id: string;
  skill_id: string;
  skill_name: string;
  canonical_slug: string;
  category?: string;
  source: string;
  raw_mention?: string;
  confidence_score: number;
  evidence_tier: string;
  resume_id?: string;
  created_at?: string;
}

export interface ClaimedSkillsResponse {
  data: ClaimedSkillItem[];
  meta: {
    total: number;
    limit: number;
    offset: number;
  };
}

export interface ResumeListItem {
  resume_id: string;
  user_id?: string | null;
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
  detected_sections: string[];
  claimed_skills_count: number;
  created_at: string;
}

export interface ResumeListResponse {
  data: ResumeListItem[];
  meta: {
    total: number;
    limit: number;
    offset: number;
  };
}

export interface ResumeDetailResponse {
  resume_id: string;
  user_id?: string | null;
  filename: string;
  file_type: string;
  file_size: number;
  has_raw_text: boolean;
  raw_text?: string;
  detected_sections: string[];
  contact_info: {
    email?: string | null;
    phone?: string | null;
    github_handle?: string | null;
    linkedin_url?: string | null;
  };
  claimed_skills_count: number;
  claimed_skills: Array<{
    skill_id: string;
    skill_name: string;
    canonical_slug: string;
    category?: string;
    raw_mention?: string;
    confidence_score: number;
  }>;
  parsed_data: Record<string, unknown>;
  created_at: string;
}

export interface ResumeUploadResult {
  resume_id: string;
  user_id?: string | null;
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
  message: string;
  extracted_sections?: string[];
  claimed_skills_count?: number;
  claimed_skills?: Array<{
    skill_id: string;
    skill_name: string;
    canonical_slug: string;
    category?: string;
    raw_mention?: string;
    confidence_score: number;
  }>;
  created_at: string;
}

/**
 * Upload a candidate resume file (PDF or DOCX) to the backend.
 * Automatically attaches session credentials via HttpOnly cookie.
 */
export async function uploadResume(
  file: File,
  userId?: string
): Promise<{
  success: boolean;
  data?: ResumeUploadResult;
  error?: string;
}> {
  const formData = new FormData();
  formData.append("file", file);
  const headers = await resolveCandidateHeaders(userId);

  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/resumes/upload`, {
      method: "POST",
      headers,
      credentials: "include",
      body: formData,
    });

    if (!res.ok) {
      let errorMessage = `Upload failed (HTTP ${res.status})`;
      try {
        const errorData = await res.json();
        if (errorData?.detail) {
          errorMessage = errorData.detail;
        }
      } catch {
        // fallback to standard status message
      }
      return { success: false, error: errorMessage };
    }

    const data: ResumeUploadResult = await res.json();
    return { success: true, data };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Network error during upload",
    };
  }
}

/**
 * Fetch candidate claimed skills from the database.
 */
export async function fetchClaimedSkills(
  resumeId?: string,
  userId?: string
): Promise<{
  success: boolean;
  data?: ClaimedSkillsResponse;
  error?: string;
}> {
  try {
    const url = resumeId
      ? `${API_BASE_URL}/api/v1/skills/claimed?resume_id=${encodeURIComponent(resumeId)}`
      : `${API_BASE_URL}/api/v1/skills/claimed`;
    const headers = await resolveCandidateHeaders(userId);
    const res = await fetch(url, { headers, credentials: "include" });
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const data: ClaimedSkillsResponse = await res.json();
    return { success: true, data };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch claimed skills",
    };
  }
}

/**
 * List stored resumes with pagination, scoped to candidate user.
 */
export async function fetchResumes(
  limit: number = 20,
  offset: number = 0,
  userId?: string
): Promise<{
  success: boolean;
  data?: ResumeListResponse;
  error?: string;
}> {
  try {
    const url = `${API_BASE_URL}/api/v1/resumes?limit=${limit}&offset=${offset}`;
    const headers = await resolveCandidateHeaders(userId);
    const res = await fetch(url, { headers, credentials: "include" });
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const data: ResumeListResponse = await res.json();
    return { success: true, data };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch resumes",
    };
  }
}

/**
 * Retrieve detailed resume metadata and parsed sections by ID.
 * Returns HTTP status for precise error and mismatch detection.
 */
export async function fetchResumeDetail(
  resumeId: string,
  userId?: string
): Promise<{
  success: boolean;
  data?: ResumeDetailResponse;
  error?: string;
  status?: number;
}> {
  try {
    const url = `${API_BASE_URL}/api/v1/resumes/${encodeURIComponent(resumeId)}`;
    const headers = await resolveCandidateHeaders(userId);
    const res = await fetch(url, { headers, credentials: "include" });
    if (!res.ok) {
      let errorMessage = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errorData = await res.json();
        if (errorData?.detail) {
          errorMessage = errorData.detail;
        } else if (errorData?.error?.message) {
          errorMessage = errorData.error.message;
        }
      } catch {
        // fallback
      }
      return { success: false, error: errorMessage, status: res.status };
    }
    const data: ResumeDetailResponse = await res.json();
    return { success: true, data, status: res.status };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch resume details",
      status: 0,
    };
  }
}

/**
 * Delete a resume document and its associated claimed skills.
 */
export async function deleteResume(
  resumeId: string,
  userId?: string
): Promise<{
  success: boolean;
  error?: string;
}> {
  try {
    const url = `${API_BASE_URL}/api/v1/resumes/${encodeURIComponent(resumeId)}`;
    const headers = await resolveCandidateHeaders(userId);
    const res = await fetch(url, { method: "DELETE", headers, credentials: "include" });
    if (res.status === 204 || res.ok) {
      return { success: true };
    }
    return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to delete resume",
    };
  }
}

export interface ActiveResumeResult {
  message: string;
  active_resume_id: string;
  filename: string;
}

/**
 * Set active resume for the authenticated user via PUT /api/v1/resumes/{resume_id}/activate.
 */
export async function activateResume(
  resumeId: string
): Promise<{
  success: boolean;
  data?: ActiveResumeResult;
  error?: string;
  status?: number;
}> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/resumes/${encodeURIComponent(resumeId)}/activate`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => null);
      const errorMessage =
        errJson?.error?.message || errJson?.detail || `HTTP ${res.status}: ${res.statusText}`;
      return { success: false, error: errorMessage, status: res.status };
    }

    const data: ActiveResumeResult = await res.json();
    return { success: true, data, status: res.status };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to activate resume",
      status: 0,
    };
  }
}

export interface GitHubRepositoryItem {
  repo_id: string;
  github_repository_id?: number | null;
  repo_name: string;
  full_name?: string | null;
  repo_url: string;
  description?: string | null;
  default_branch?: string | null;
  visibility?: string | null;
  primary_language?: string | null;
  is_fork: boolean;
  stars_count: number;
  forks_count: number;
  last_pushed_at?: string | null;
  synced_at?: string | null;
}

export interface GitHubRepositoryListResponse {
  data: GitHubRepositoryItem[];
  meta: {
    total: number;
    limit: number;
    offset: number;
  };
}

export interface GitHubConnectResult {
  github_username: string;
  connected: boolean;
  discovered_repositories: number;
  connected_at: string;
  repositories?: GitHubRepositoryItem[];
}

/**
 * Connect GitHub account and discover non-fork repositories.
 */
export async function connectGitHub(
  username: string,
  accessToken?: string,
  userId?: string
): Promise<{
  success: boolean;
  data?: GitHubConnectResult;
  error?: string;
}> {
  try {
    const candidateHeaders = await resolveCandidateHeaders(userId);
    const res = await fetch(`${API_BASE_URL}/api/v1/github/connect`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...candidateHeaders },
      credentials: "include",
      body: JSON.stringify({
        github_username: username,
        access_token: accessToken || undefined,
      }),
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => null);
      const errorMessage =
        errJson?.error?.message || errJson?.detail || `HTTP ${res.status}: ${res.statusText}`;
      return { success: false, error: errorMessage };
    }

    const json = await res.json();
    return { success: true, data: json.data };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Network error during GitHub connection",
    };
  }
}

/**
 * Disconnects the connected GitHub account from the authenticated candidate via POST /api/v1/github/disconnect.
 */
export async function disconnectGitHubAccount(): Promise<{
  success: boolean;
  error?: string;
  status?: number;
}> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/github/disconnect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => null);
      const errorMessage =
        errJson?.error?.message || errJson?.detail || `HTTP ${res.status}: ${res.statusText}`;
      return { success: false, error: errorMessage, status: res.status };
    }

    return { success: true, status: res.status };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to disconnect GitHub account",
      status: 0,
    };
  }
}

/**
 * Fetch discovered repositories.
 */
export async function fetchGitHubRepositories(
  limit: number = 20,
  offset: number = 0,
  username?: string,
  userId?: string
): Promise<{
  success: boolean;
  data?: GitHubRepositoryListResponse;
  error?: string;
}> {
  try {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    if (username) params.append("username", username);

    const candidateHeaders = await resolveCandidateHeaders(userId);
    const res = await fetch(
      `${API_BASE_URL}/api/v1/github/repositories?${params.toString()}`,
      { headers: candidateHeaders, credentials: "include" }
    );
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const data: GitHubRepositoryListResponse = await res.json();
    return { success: true, data };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch repositories",
    };
  }
}

/**
 * Fetch repository details by ID.
 */
export async function fetchGitHubRepositoryDetail(repoId: string): Promise<{
  success: boolean;
  data?: GitHubRepositoryItem;
  error?: string;
}> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/github/repositories/${encodeURIComponent(repoId)}`, {
      credentials: "include",
    });
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const json = await res.json();
    return { success: true, data: json.data };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch repository details",
    };
  }
}

export interface DemonstratedSkill {
  skill_id: string;
  skill_name: string;
  name: string;
  canonical_slug: string;
  confidence_score: number;
  evidence_type: string;
  evidence_tier: string;
}

export interface AnalyzeResult {
  repository_id?: string;
  repository_name?: string;
  analyzed: boolean;
  repositories_analyzed: number;
  evidence_count: number;
  evidence_items_detected: number;
  demonstrated_skills: DemonstratedSkill[];
}

export interface ProjectEvidenceItem {
  evidence_id: string;
  repository_id?: string;
  repo_name?: string;
  skill_id: string;
  skill_name: string;
  canonical_slug: string;
  evidence_type: string;
  artifact_path?: string;
  file_path?: string;
  artifact_name?: string;
  evidence_description?: string;
  matched_content?: string;
  confidence_score: number;
  evidence_metadata: Record<string, unknown>;
  detected_at: string;
  created_at: string;
}

export interface ProjectEvidenceListResponse {
  data: ProjectEvidenceItem[];
  meta: {
    total: number;
    limit: number;
    offset: number;
  };
}

/**
 * Trigger artifact inspection and evidence extraction for a repository.
 */
export async function analyzeGitHubRepository(
  repositoryId: string,
  userId?: string
): Promise<{
  success: boolean;
  data?: AnalyzeResult;
  error?: string;
}> {
  try {
    const candidateHeaders = await resolveCandidateHeaders(userId);
    const res = await fetch(`${API_BASE_URL}/api/v1/github/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...candidateHeaders,
      },
      credentials: "include",
      body: JSON.stringify({ repository_id: repositoryId }),
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => null);
      const errorMessage =
        errJson?.error?.message || errJson?.detail || `HTTP ${res.status}: ${res.statusText}`;
      return { success: false, error: errorMessage };
    }

    const json = await res.json();
    return { success: true, data: json.data };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Network error during repository analysis",
    };
  }
}

/**
 * Fetch verified project evidence items.
 */
export async function fetchEvidence(
  repositoryId?: string,
  skillId?: string,
  evidenceType?: string,
  limit: number = 20,
  offset: number = 0
): Promise<{
  success: boolean;
  data?: ProjectEvidenceListResponse;
  error?: string;
}> {
  try {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    if (repositoryId) params.append("repository_id", repositoryId);
    if (skillId) params.append("skill_id", skillId);
    if (evidenceType) params.append("evidence_type", evidenceType);

    const res = await fetch(`${API_BASE_URL}/api/v1/evidence?${params.toString()}`, {
      credentials: "include",
    });
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const json: ProjectEvidenceListResponse = await res.json();
    return { success: true, data: json };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch evidence",
    };
  }
}

/**
 * Fetch details of a specific evidence item.
 */
export async function fetchEvidenceDetail(evidenceId: string): Promise<{
  success: boolean;
  data?: ProjectEvidenceItem;
  error?: string;
}> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/evidence/${encodeURIComponent(evidenceId)}`, {
      credentials: "include",
    });
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const json = await res.json();
    return { success: true, data: json.data };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch evidence detail",
    };
  }
}

export interface SupportingRepository {
  repository_id?: string;
  repo_name: string;
  repo_url?: string;
  max_confidence: number;
  evidence_count: number;
}

export interface DemonstratedSkillSummary {
  skill_id: string;
  skill_name: string;
  slug: string;
  category?: string;
  confidence_score: number;
  evidence_level: "HIGH" | "MEDIUM" | "LOW";
  evidence_count: number;
  repository_count: number;
  last_verified_at?: string;
  repositories: SupportingRepository[];
  evidence_types: string[];
}

export interface DemonstratedSkillListResponse {
  data: DemonstratedSkillSummary[];
  meta: {
    total: number;
    limit: number;
    offset: number;
  };
}

export interface DemonstratedSkillDetailData extends DemonstratedSkillSummary {
  description?: string;
  evidence: ProjectEvidenceItem[];
}

/**
 * Fetch aggregated demonstrated skills.
 */
export async function fetchDemonstratedSkills(
  repositoryId?: string,
  skillId?: string,
  evidenceLevel?: string,
  limit: number = 20,
  offset: number = 0,
  username?: string,
  userId?: string
): Promise<{
  success: boolean;
  data?: DemonstratedSkillListResponse;
  error?: string;
}> {
  try {
    const candidateHeaders = await resolveCandidateHeaders(userId);
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    if (repositoryId) params.append("repository_id", repositoryId);
    if (skillId) params.append("skill_id", skillId);
    if (evidenceLevel) params.append("evidence_level", evidenceLevel);
    if (username && username.trim()) params.append("username", username.trim());

    const res = await fetch(`${API_BASE_URL}/api/v1/skills/demonstrated?${params.toString()}`, {
      headers: candidateHeaders,
      credentials: "include",
    });
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const json: DemonstratedSkillListResponse = await res.json();
    return { success: true, data: json };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch demonstrated skills",
    };
  }
}

/**
 * Fetch detailed demonstrated skill with auditable evidence trail.
 */
export async function fetchDemonstratedSkillDetail(
  skillId: string,
  userId?: string
): Promise<{
  success: boolean;
  data?: DemonstratedSkillDetailData;
  error?: string;
}> {
  try {
    const candidateHeaders = await resolveCandidateHeaders(userId);
    const res = await fetch(`${API_BASE_URL}/api/v1/skills/demonstrated/${encodeURIComponent(skillId)}`, {
      headers: candidateHeaders,
      credentials: "include",
    });
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const json = await res.json();
    return { success: true, data: json.data };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch demonstrated skill detail",
    };
  }
}

// -----------------------------------------------------------------------------
// Phase 4 Checkpoint 1: Job Roles & Industry Demand Interfaces & API Methods
// -----------------------------------------------------------------------------

export interface JobRole {
  role_id: string;
  title: string;
  slug: string;
  category: string;
  description?: string;
}

export interface JobRoleListResponse {
  data: JobRole[];
  meta: {
    total: number;
    limit: number;
    offset: number;
  };
}

export interface SkillDemandItem {
  skill_id: string;
  skill_name: string;
  canonical_slug: string;
  category?: string;
  role_id?: string;
  role_title?: string;
  location: string;
  sample_size: number;
  demand_score: number;
  growth_rate: number;
  data_updated_at: string;
}

export interface SkillDemandListResponse {
  data: SkillDemandItem[];
  meta: {
    total: number;
    limit: number;
    offset: number;
    role_id?: string;
    location?: string;
    data_freshness?: string;
  };
}

export interface RoleSkillDemandItem {
  skill_id: string;
  skill_name: string;
  canonical_slug: string;
  category?: string;
  demand_score: number;
  growth_rate: number;
  sample_size: number;
  location: string;
  data_updated_at: string;
}

export interface RoleDemandDetailData {
  role: JobRole;
  skills: RoleSkillDemandItem[];
}

export interface RoleDemandDetailResponse {
  data: RoleDemandDetailData;
  meta: {
    total: number;
    location: string;
    data_freshness: string;
    total_demanded_skills?: number;
    average_demand_score?: number;
    highest_demand_score?: number;
    lowest_demand_score?: number;
    average_growth_rate?: number;
    top_skill?: string | null;
  };
}

export interface DemandQualityAuditReport {
  status: "VALID" | "CORRUPTED";
  total_roles: number;
  total_demand_records: number;
  roles_with_demand: number;
  orphaned_roles: number;
  orphaned_demand_records: number;
  out_of_bounds_scores: number;
  non_positive_sample_sizes: number;
  duplicate_records: number;
  data_freshness: string;
  audit_timestamp: string;
}

/**
 * Fetch demand quality audit report from GET /api/v1/demand/audit/quality.
 */
export async function fetchDemandQualityAudit(): Promise<{
  success: boolean;
  data?: DemandQualityAuditReport;
  error?: string;
}> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/demand/audit/quality`);
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const json = await res.json();
    return { success: true, data: json.data };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch quality audit",
    };
  }
}

/**
 * Fetch canonical job roles from GET /api/v1/roles.
 */
export async function fetchRoles(
  category?: string,
  limit: number = 20,
  offset: number = 0
): Promise<{
  success: boolean;
  data?: JobRoleListResponse;
  error?: string;
}> {
  try {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    if (category) params.append("category", category);

    const res = await fetch(`${API_BASE_URL}/api/v1/roles?${params.toString()}`);
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const json: JobRoleListResponse = await res.json();
    return { success: true, data: json };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch job roles",
    };
  }
}

/**
 * Fetch a specific canonical job role from GET /api/v1/roles/{role_id}.
 */
export async function fetchRoleDetail(roleId: string): Promise<{
  success: boolean;
  data?: JobRole;
  error?: string;
}> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/roles/${encodeURIComponent(roleId)}`);
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const json = await res.json();
    return { success: true, data: json.data };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch role detail",
    };
  }
}

/**
 * Fetch industry skill demand list from GET /api/v1/demand.
 */
export async function fetchDemand(
  roleId?: string,
  skillId?: string,
  location: string = "India",
  limit: number = 20,
  offset: number = 0
): Promise<{
  success: boolean;
  data?: SkillDemandListResponse;
  error?: string;
}> {
  try {
    const params = new URLSearchParams({
      location,
      limit: String(limit),
      offset: String(offset),
    });
    if (roleId) params.append("role_id", roleId);
    if (skillId) params.append("skill_id", skillId);

    const res = await fetch(`${API_BASE_URL}/api/v1/demand?${params.toString()}`);
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const json: SkillDemandListResponse = await res.json();
    return { success: true, data: json };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch industry demand",
    };
  }
}

/**
 * Fetch complete role demand profile breakdown from GET /api/v1/demand/{role_id}.
 */
export async function fetchRoleDemand(
  roleId: string,
  location: string = "India"
): Promise<{
  success: boolean;
  data?: RoleDemandDetailData;
  meta?: RoleDemandDetailResponse["meta"];
  error?: string;
}> {
  try {
    const params = new URLSearchParams({ location });
    const res = await fetch(
      `${API_BASE_URL}/api/v1/demand/${encodeURIComponent(roleId)}?${params.toString()}`
    );
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const json: RoleDemandDetailResponse = await res.json();
    return { success: true, data: json.data, meta: json.meta };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch role demand profile",
    };
  }
}

// -----------------------------------------------------------------------------
// Phase 4 Checkpoint 3: Demand Intelligence Interfaces & API Methods
// -----------------------------------------------------------------------------

export interface SkillDemandRankingItem {
  skill_id: string;
  skill_name: string;
  canonical_slug: string;
  category?: string;
  demand_score: number;
  average_growth_rate: number;
  role_count: number;
  total_sample_size: number;
  trend: "RISING" | "STABLE" | "DECLINING";
}

export interface SkillDemandRankingResponse {
  data: SkillDemandRankingItem[];
  meta: {
    total: number;
    limit: number;
    offset: number;
    location: string;
    role_id?: string;
    data_freshness: string;
  };
}

export interface SkillAcrossRolesResponse {
  data: {
    skill: {
      id: string;
      name: string;
      slug: string;
      category?: string;
      description?: string;
    };
    roles: Array<{
      role_id: string;
      role_title: string;
      role_slug: string;
      demand_score: number;
      growth_rate: number;
      sample_size: number;
      trend: "RISING" | "STABLE" | "DECLINING";
      location: string;
    }>;
    average_demand_score: number;
    total_roles_demanding: number;
  };
  meta: {
    location: string;
    data_freshness: string;
  };
}

export interface RoleCompareResponse {
  data: {
    roles: Array<{
      role_id: string;
      title: string;
      slug: string;
      category: string;
      total_demanded_skills: number;
      average_demand_score: number;
      top_skill?: string | null;
    }>;
    shared_skills: Array<{
      skill_id: string;
      skill_name: string;
      canonical_slug: string;
      category?: string;
      average_demand_score: number;
      demand_score_diff: number;
      average_growth_rate: number;
      demands_by_role: Record<
        string,
        {
          role_id: string;
          role_title: string;
          demand_score: number;
          growth_rate: number;
          trend: "RISING" | "STABLE" | "DECLINING";
        }
      >;
    }>;
    role_specific_skills: Record<
      string,
      Array<{
        skill_id: string;
        skill_name: string;
        canonical_slug: string;
        category?: string;
        demand_score: number;
        growth_rate: number;
        trend: "RISING" | "STABLE" | "DECLINING";
      }>
    >;
    comparison_summary: {
      compared_roles_count: number;
      total_unique_skills: number;
      shared_skills_count: number;
      role_specific_counts: Record<string, number>;
    };
  };
  meta: {
    location: string;
    data_freshness: string;
  };
}

export interface RoleMarketSignalsResponse {
  data: {
    role: JobRole;
    metrics: {
      total_demanded_skills: number;
      average_demand_score: number;
      highest_demand_score: number;
      lowest_demand_score: number;
      average_growth_rate: number;
      rising_skill_count: number;
      stable_skill_count: number;
      declining_skill_count: number;
    };
    top_demanded_skills: Array<{
      skill_id: string;
      skill_name: string;
      canonical_slug: string;
      category?: string;
      demand_score: number;
      growth_rate: number;
      trend: "RISING" | "STABLE" | "DECLINING";
    }>;
    fastest_growing_skills: Array<{
      skill_id: string;
      skill_name: string;
      canonical_slug: string;
      category?: string;
      demand_score: number;
      growth_rate: number;
      trend: "RISING" | "STABLE" | "DECLINING";
    }>;
  };
  meta: {
    location: string;
    data_freshness: string;
  };
}

export interface DemandTrendsResponse {
  data: Array<{
    skill_id: string;
    skill_name: string;
    canonical_slug: string;
    category?: string;
    role_id: string;
    role_title: string;
    demand_score: number;
    growth_rate: number;
    trend: "RISING" | "STABLE" | "DECLINING";
    location: string;
    sample_size: number;
  }>;
  meta: {
    total: number;
    limit: number;
    offset: number;
    role_id?: string;
    location?: string;
    data_freshness?: string;
  };
}

/**
 * Fetch global or role-filtered skill rankings from GET /api/v1/intelligence/skills/ranking.
 */
export async function fetchSkillDemandRanking(
  location: string = "India",
  roleId?: string,
  limit: number = 50,
  offset: number = 0
): Promise<{
  success: boolean;
  data?: SkillDemandRankingResponse;
  error?: string;
}> {
  try {
    const params = new URLSearchParams({
      location,
      limit: String(limit),
      offset: String(offset),
    });
    if (roleId) params.append("role_id", roleId);

    const res = await fetch(`${API_BASE_URL}/api/v1/intelligence/skills/ranking?${params.toString()}`);
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const json = await res.json();
    return { success: true, data: json };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch skill ranking",
    };
  }
}

/**
 * Fetch skill demand profile across all job roles from GET /api/v1/intelligence/skills/{skill_id}/roles.
 */
export async function fetchSkillRoleDemand(
  skillId: string,
  location: string = "India"
): Promise<{
  success: boolean;
  data?: SkillAcrossRolesResponse["data"];
  error?: string;
}> {
  try {
    const params = new URLSearchParams({ location });
    const res = await fetch(
      `${API_BASE_URL}/api/v1/intelligence/skills/${encodeURIComponent(skillId)}/roles?${params.toString()}`
    );
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const json = await res.json();
    return { success: true, data: json.data };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch skill role demand",
    };
  }
}

/**
 * Compare 2 to 5 canonical job roles via POST /api/v1/intelligence/roles/compare.
 */
export async function compareRoles(
  roleIds: string[],
  location: string = "India"
): Promise<{
  success: boolean;
  data?: RoleCompareResponse["data"];
  error?: string;
}> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/intelligence/roles/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role_ids: roleIds, location }),
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => null);
      return {
        success: false,
        error: errJson?.error?.message || `HTTP ${res.status}: ${res.statusText}`,
      };
    }
    const json = await res.json();
    return { success: true, data: json.data };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to compare roles",
    };
  }
}

/**
 * Fetch role market signals from GET /api/v1/intelligence/roles/{role_id}/signals.
 */
export async function fetchRoleMarketSignals(
  roleId: string,
  location: string = "India"
): Promise<{
  success: boolean;
  data?: RoleMarketSignalsResponse["data"];
  error?: string;
}> {
  try {
    const params = new URLSearchParams({ location });
    const res = await fetch(
      `${API_BASE_URL}/api/v1/intelligence/roles/${encodeURIComponent(roleId)}/signals?${params.toString()}`
    );
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const json = await res.json();
    return { success: true, data: json.data };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch market signals",
    };
  }
}

/**
 * Fetch demand trends from GET /api/v1/intelligence/trends.
 */
export async function fetchDemandTrends(
  location: string = "India",
  roleId?: string,
  limit: number = 20,
  offset: number = 0
): Promise<{
  success: boolean;
  data?: DemandTrendsResponse;
  error?: string;
}> {
  try {
    const params = new URLSearchParams({
      location,
      limit: String(limit),
      offset: String(offset),
    });
    if (roleId) params.append("role_id", roleId);

    const res = await fetch(`${API_BASE_URL}/api/v1/intelligence/trends?${params.toString()}`);
    if (!res.ok) {
      return { success: false, error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const json = await res.json();
    return { success: true, data: json };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch demand trends",
    };
  }
}

// -----------------------------------------------------------------------------
// Phase 5 Checkpoint 1: Skill Gap Foundation Interfaces & API Methods
// -----------------------------------------------------------------------------

export interface SkillGapItem {
  id: string;
  skill_id: string;
  skill_name: string;
  canonical_slug: string;
  category?: string;
  status: "STRONG" | "PARTIAL" | "MISSING";
  demand_score: number;
  growth_rate: number;
  claimed: boolean;
  claim_confidence: number;
  demonstrated: boolean;
  demonstrated_score: number;
  evidence_level?: "HIGH" | "MEDIUM" | "LOW" | null;
  evidence_count: number;
}

export interface SkillGapSummary {
  total_required_skills: number;
  strong_count: number;
  partial_count: number;
  missing_count: number;
}

export interface SkillGapResponse {
  data: {
    role: JobRole;
    location: string;
    summary: SkillGapSummary;
    skills: SkillGapItem[];
  };
  meta: {
    user_id?: string | null;
    location: string;
    calculated_at: string;
    data_freshness: string;
  };
}

/**
 * Fetch candidate skill gaps for a canonical job role from GET /api/v1/gaps/{role_id}.
 */
export async function fetchSkillGaps(
  roleId: string,
  location: string = "India",
  userId?: string,
  includeResume: boolean = true,
  includeGitHub: boolean = true,
  username?: string | null,
  resumeId?: string | null
): Promise<{
  success: boolean;
  data?: SkillGapResponse["data"];
  meta?: SkillGapResponse["meta"];
  error?: string;
}> {
  try {
    const params = new URLSearchParams({ location });
    params.append("include_resume", String(includeResume));
    params.append("include_github", String(includeGitHub));
    if (username) params.append("username", username);
    if (resumeId) params.append("resume_id", resumeId);

    const headers = await resolveCandidateHeaders(userId);
    const res = await fetch(
      `${API_BASE_URL}/api/v1/gaps/${encodeURIComponent(roleId)}?${params.toString()}`,
      { headers, credentials: "include" }
    );
    if (!res.ok) {
      const errJson = await res.json().catch(() => null);
      return {
        success: false,
        error: errJson?.error?.message || `HTTP ${res.status}: ${res.statusText}`,
      };
    }
    const json: SkillGapResponse = await res.json();
    return { success: true, data: json.data, meta: json.meta };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch skill gaps",
    };
  }
}

/**
 * Execute skill gap analysis via POST /api/v1/gaps/analyze.
 */
export async function analyzeSkillGaps(
  targetRoleId: string,
  location: string = "India",
  userId?: string
): Promise<{
  success: boolean;
  data?: SkillGapResponse["data"];
  meta?: SkillGapResponse["meta"];
  error?: string;
}> {
  try {
    const candidateHeaders = await resolveCandidateHeaders(userId);
    const res = await fetch(`${API_BASE_URL}/api/v1/gaps/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...candidateHeaders },
      credentials: "include",
      body: JSON.stringify({
        target_role_id: targetRoleId,
        location,
      }),
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => null);
      return {
        success: false,
        error: errJson?.error?.message || `HTTP ${res.status}: ${res.statusText}`,
      };
    }
    const json: SkillGapResponse = await res.json();
    return { success: true, data: json.data, meta: json.meta };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to execute skill gap analysis",
    };
  }
}

// -----------------------------------------------------------------------------
// Phase 5 Checkpoint 2: Prioritization Interfaces & API Methods
// -----------------------------------------------------------------------------

export interface PrioritizedGapItem {
  skill_id: string;
  skill_name: string;
  canonical_slug: string;
  category?: string;
  status: "MISSING" | "PARTIAL";
  priority_score: number;
  priority_level: "HIGH" | "MEDIUM" | "LOW";
  demand_score: number;
  growth_rate: number;
  claimed: boolean;
  claim_confidence: number;
  demonstrated: boolean;
  demonstrated_score: number;
  evidence_level?: "HIGH" | "MEDIUM" | "LOW" | null;
  evidence_count: number;
  location: string;
  explanation: string;
}

export interface PrioritizedGapsSummary {
  total_actionable_gaps: number;
  high_priority_count: number;
  medium_priority_count: number;
  low_priority_count: number;
  missing_count: number;
  partial_count: number;
}

export interface PrioritizedGapsResponse {
  data: {
    role: JobRole;
    location: string;
    summary: PrioritizedGapsSummary;
    gaps: PrioritizedGapItem[];
  };
  meta: {
    user_id?: string | null;
    location: string;
    calculated_at: string;
    data_freshness: string;
    scoring_version: string;
  };
}

/**
 * Fetch candidate prioritized actionable gaps from GET /api/v1/gaps/{role_id}/priorities.
 */
export async function fetchPrioritizedGaps(
  roleId: string,
  location: string = "India",
  userId?: string,
  includeResume: boolean = true,
  includeGitHub: boolean = true,
  username?: string | null,
  resumeId?: string | null
): Promise<{
  success: boolean;
  data?: PrioritizedGapsResponse["data"];
  meta?: PrioritizedGapsResponse["meta"];
  error?: string;
}> {
  try {
    const params = new URLSearchParams({ location });
    params.append("include_resume", String(includeResume));
    params.append("include_github", String(includeGitHub));
    if (username) params.append("username", username);
    if (resumeId) params.append("resume_id", resumeId);

    const headers = await resolveCandidateHeaders(userId);
    const res = await fetch(
      `${API_BASE_URL}/api/v1/gaps/${encodeURIComponent(roleId)}/priorities?${params.toString()}`,
      { headers, credentials: "include" }
    );
    if (!res.ok) {
      const errJson = await res.json().catch(() => null);
      return {
        success: false,
        error: errJson?.error?.message || `HTTP ${res.status}: ${res.statusText}`,
      };
    }
    const json: PrioritizedGapsResponse = await res.json();
    return { success: true, data: json.data, meta: json.meta };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch prioritized skill gaps",
    };
  }
}

// -----------------------------------------------------------------------------
// Phase 5 Checkpoint 3: Gap Evidence & Explainability Interfaces & API Methods
// -----------------------------------------------------------------------------

export interface ResumeEvidenceItem {
  id: string;
  raw_mention?: string | null;
  confidence_score: number;
  source: string;
  resume_id?: string | null;
  resume_file_name?: string | null;
  created_at?: string | null;
}

export interface GitHubEvidenceItem {
  id: string;
  repo_id?: string | null;
  repo_name: string;
  repo_full_name?: string | null;
  repo_url?: string | null;
  evidence_type: string;
  file_path?: string | null;
  artifact_name?: string | null;
  matched_content?: string | null;
  confidence_score: number;
  detected_at?: string | null;
}

export interface GapDemonstratedSummary {
  confidence_score: number;
  evidence_level: "HIGH" | "MEDIUM" | "LOW" | string;
  evidence_count: number;
  repository_count: number;
  last_verified_at?: string | null;
}

export interface CandidateEvidenceData {
  has_evidence: boolean;
  resume_claims: ResumeEvidenceItem[];
  github_demonstrated?: GapDemonstratedSummary | null;
  github_artifacts: GitHubEvidenceItem[];
}

export interface MarketEvidenceData {
  role_id: string;
  role_title: string;
  role_slug: string;
  location: string;
  demand_score: number;
  growth_rate: number;
  sample_size: number;
  data_updated_at?: string | null;
}

export interface DeterministicReasoningData {
  classification_reason: string;
  priority_reason: string;
  scoring_version: string;
}

export interface SkillGapEvidenceResponseData {
  skill_id: string;
  skill_name: string;
  canonical_slug: string;
  category?: string | null;
  status: "STRONG" | "PARTIAL" | "MISSING";
  priority_score?: number | null;
  priority_level?: string | null;
  candidate_evidence: CandidateEvidenceData;
  market_evidence: MarketEvidenceData;
  reasoning: DeterministicReasoningData;
}

export interface SkillGapEvidenceResponse {
  data: SkillGapEvidenceResponseData;
  meta: {
    user_id?: string | null;
    location: string;
    calculated_at: string;
    data_freshness: string;
    scoring_version: string;
  };
}

/**
 * Fetch complete audit evidence chain for a specific skill gap from GET /api/v1/gaps/{role_id}/skills/{skill_id}/evidence.
 */
export async function fetchSkillGapEvidence(
  roleId: string,
  skillId: string,
  location: string = "India",
  userId?: string,
  includeResume: boolean = true,
  includeGitHub: boolean = true,
  username?: string | null,
  resumeId?: string | null
): Promise<{
  success: boolean;
  data?: SkillGapEvidenceResponseData;
  meta?: SkillGapEvidenceResponse["meta"];
  error?: string;
}> {
  try {
    const params = new URLSearchParams({ location });
    params.append("include_resume", String(includeResume));
    params.append("include_github", String(includeGitHub));
    if (username) params.append("username", username);
    if (resumeId) params.append("resume_id", resumeId);

    const headers = await resolveCandidateHeaders(userId);
    const res = await fetch(
      `${API_BASE_URL}/api/v1/gaps/${encodeURIComponent(roleId)}/skills/${encodeURIComponent(skillId)}/evidence?${params.toString()}`,
      { headers, credentials: "include" }
    );
    if (!res.ok) {
      const errJson = await res.json().catch(() => null);
      return {
        success: false,
        error: errJson?.error?.message || `HTTP ${res.status}: ${res.statusText}`,
      };
    }
    const json: SkillGapEvidenceResponse = await res.json();
    return { success: true, data: json.data, meta: json.meta };
  } catch (err: unknown) {
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to fetch skill gap evidence",
    };
  }
}

// =============================================================================
// Post-MVP Phase 2, Phase 4 & Phase 5 Foundations
// =============================================================================

export * from "./types/roadmap";
export * from "./types/verification";
export * from "./types/chat";
export * from "./identity";

import type {
  CanonicalRoadmapData,
  RoadmapGenerateRequest,
  AIRoadmapExplainRequest,
  AIRoadmapExplainResponse,
  ApprovedResourceListResponse,
} from "./types/roadmap";

import type {
  MilestoneVerifyRequest,
  MilestoneVerificationResponse,
  RoadmapBatchVerifyRequest,
  RoadmapBatchVerificationResponse,
} from "./types/verification";

import type {
  CareerChatRequest,
  CareerChatResponse,
} from "./types/chat";


interface PostMvpRequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
  userId?: string;
  patToken?: string;
  includeAuth?: boolean;
}

/**
 * Lightweight internal fetch wrapper for Post-MVP endpoints requiring candidate identity.
 * Transmits session credentials via HttpOnly cookie and optional `Authorization: Bearer <token>` header.
 * Ensures tokens are NEVER sent via body, URL, or query parameters.
 */
async function postMvpFetch<T>(
  endpoint: string,
  options: PostMvpRequestOptions = {}
): Promise<{
  success: boolean;
  data?: T;
  meta?: Record<string, unknown>;
  error?: string;
  status?: number;
}> {
  const {
    method = "GET",
    body,
    headers: customHeaders = {},
    userId,
    patToken,
    includeAuth = true,
  } = options;

  const headers: Record<string, string> = { ...customHeaders };

  if (body !== undefined && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  // Personal Access Token: ONLY transmitted via Authorization Bearer header
  if (patToken && patToken.trim()) {
    headers["Authorization"] = `Bearer ${patToken.trim()}`;
  }

  try {
    const res = await fetch(`${API_BASE_URL}${endpoint}`, {
      method,
      headers,
      credentials: "include",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    if (!res.ok) {
      let errorMessage = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errJson = await res.json();
        errorMessage =
          errJson?.error?.message ||
          errJson?.detail ||
          errorMessage;
      } catch {
        // fallback to default status message
      }

      // If backend reports candidate user not found, invalidate stale local identity
      if (
        res.status === 404 &&
        typeof errorMessage === "string" &&
        errorMessage.includes("User with id")
      ) {
        clearCandidateUserId();
      }

      // If backend reports target resume ownership mismatch, clear stale active resume reference
      // while keeping candidate identity stable
      if (
        res.status === 403 &&
        typeof errorMessage === "string" &&
        errorMessage.includes("Cross-user access denied: target resume")
      ) {
        if (typeof window !== "undefined") {
          try {
            localStorage.removeItem("skillforge_active_resume_id");
            localStorage.removeItem("skillforge_active_resume_filename");
          } catch {
            // ignore
          }
        }
      }

      return {
        success: false,
        error: errorMessage,
        status: res.status,
      };
    }

    if (res.status === 204) {
      return { success: true, status: 204 };
    }

    const json = await res.json();
    return {
      success: true,
      data: (json?.data !== undefined ? json.data : json) as T,
      meta: json?.meta,
      status: res.status,
    };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Network error";
    return {
      success: false,
      error: message,
      status: 0,
    };
  }
}

// -----------------------------------------------------------------------------
// Post-MVP Phase 4: Personalized Career Roadmap API Methods
// -----------------------------------------------------------------------------

/**
 * Generate canonical career roadmap from POST /api/v1/roadmap/generate.
 * In-memory if unauthenticated, persisted if session-authenticated.
 */
export async function generateRoadmap(
  request: RoadmapGenerateRequest,
  userId?: string
): Promise<{
  success: boolean;
  data?: CanonicalRoadmapData;
  meta?: Record<string, unknown>;
  error?: string;
  status?: number;
}> {
  return postMvpFetch<CanonicalRoadmapData>("/api/v1/roadmap/generate", {
    method: "POST",
    body: request,
    userId,
    includeAuth: true,
  });
}

/**
 * Retrieve candidate's active roadmap for a target role from GET /api/v1/roadmap/active.
 */
export async function fetchActiveRoadmap(
  roleId?: string,
  userId?: string
): Promise<{
  success: boolean;
  data?: CanonicalRoadmapData;
  meta?: Record<string, unknown>;
  error?: string;
  status?: number;
}> {
  const query = roleId ? `?role_id=${encodeURIComponent(roleId)}` : "";
  return postMvpFetch<CanonicalRoadmapData>(`/api/v1/roadmap/active${query}`, {
    method: "GET",
    userId,
    includeAuth: true,
  });
}

/**
 * Retrieve a persisted roadmap by ID from GET /api/v1/roadmap/{roadmap_id}.
 */
export async function fetchRoadmap(
  roadmapId: string,
  userId?: string
): Promise<{
  success: boolean;
  data?: CanonicalRoadmapData;
  meta?: Record<string, unknown>;
  error?: string;
  status?: number;
}> {
  return postMvpFetch<CanonicalRoadmapData>(
    `/api/v1/roadmap/${encodeURIComponent(roadmapId)}`,
    {
      method: "GET",
      userId,
      includeAuth: true,
    }
  );
}

/**
 * Query approved curated learning resources for a canonical skill from GET /api/v1/roadmap/resources/{skill_id}.
 */
export async function fetchApprovedResources(
  skillId: string
): Promise<{
  success: boolean;
  data?: ApprovedResourceListResponse;
  error?: string;
  status?: number;
}> {
  return postMvpFetch<ApprovedResourceListResponse>(
    `/api/v1/roadmap/resources/${encodeURIComponent(skillId)}`,
    {
      method: "GET",
      includeAuth: false,
    }
  );
}

/**
 * Request non-authoritative Qwen explanation of a canonical roadmap from POST /api/v1/roadmap/{roadmap_id}/explain.
 */
export async function explainRoadmap(
  roadmapId: string,
  request: AIRoadmapExplainRequest = {},
  userId?: string
): Promise<{
  success: boolean;
  data?: AIRoadmapExplainResponse;
  error?: string;
  status?: number;
}> {
  return postMvpFetch<AIRoadmapExplainResponse>(
    `/api/v1/roadmap/${encodeURIComponent(roadmapId)}/explain`,
    {
      method: "POST",
      body: request,
      userId,
      includeAuth: true,
    }
  );
}

// -----------------------------------------------------------------------------
// Post-MVP Phase 5: GitHub Skill Verification API Methods
// -----------------------------------------------------------------------------

/**
 * Deterministically verify a roadmap milestone from POST /api/v1/roadmap/{roadmap_id}/milestones/{milestone_id}/verify.
 * Accepts volatile GitHub PAT exclusively via Authorization Bearer header.
 */
export async function verifyMilestone(
  roadmapId: string,
  milestoneId: string,
  payload?: MilestoneVerifyRequest,
  patToken?: string,
  userId?: string
): Promise<{
  success: boolean;
  data?: MilestoneVerificationResponse;
  error?: string;
  status?: number;
}> {
  return postMvpFetch<MilestoneVerificationResponse>(
    `/api/v1/roadmap/${encodeURIComponent(roadmapId)}/milestones/${encodeURIComponent(milestoneId)}/verify`,
    {
      method: "POST",
      body: payload,
      userId,
      patToken,
      includeAuth: true,
    }
  );
}

/**
 * Retrieve latest milestone verification audit record from GET /api/v1/roadmap/{roadmap_id}/milestones/{milestone_id}/verification.
 */
export async function fetchMilestoneVerification(
  roadmapId: string,
  milestoneId: string,
  userId?: string
): Promise<{
  success: boolean;
  data?: MilestoneVerificationResponse;
  error?: string;
  status?: number;
}> {
  return postMvpFetch<MilestoneVerificationResponse>(
    `/api/v1/roadmap/${encodeURIComponent(roadmapId)}/milestones/${encodeURIComponent(milestoneId)}/verification`,
    {
      method: "GET",
      userId,
      includeAuth: true,
    }
  );
}

/**
 * Batch verify all milestones sequentially for a roadmap from POST /api/v1/roadmap/{roadmap_id}/verify.
 */
export async function batchVerifyRoadmap(
  roadmapId: string,
  payload?: RoadmapBatchVerifyRequest,
  patToken?: string,
  userId?: string
): Promise<{
  success: boolean;
  data?: RoadmapBatchVerificationResponse;
  error?: string;
  status?: number;
}> {
  return postMvpFetch<RoadmapBatchVerificationResponse>(
    `/api/v1/roadmap/${encodeURIComponent(roadmapId)}/verify`,
    {
      method: "POST",
      body: payload,
      userId,
      patToken,
      includeAuth: true,
    }
  );
}

// -----------------------------------------------------------------------------
// Post-MVP Phase 2: Evidence-Grounded Career Chatbot API Method
// -----------------------------------------------------------------------------

/**
 * Execute evidence-grounded career chatbot reasoning from POST /api/v1/ai/chat.
 * Consumes pre-constructed VerifiedContext. Never sends credentials or chat history.
 */
export async function sendCareerChat(
  request: CareerChatRequest
): Promise<{
  success: boolean;
  data?: CareerChatResponse;
  error?: string;
  status?: number;
}> {
  return postMvpFetch<CareerChatResponse>("/api/v1/ai/chat", {
    method: "POST",
    body: request,
    includeAuth: false,
  });
}
