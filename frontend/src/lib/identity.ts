/**
 * Candidate Identity Helper for SkillForge AI.
 *
 * Post-MVP Login Phase 5:
 * The backend ownership layer uses server-issued HttpOnly session cookies
 * (skillforge_session) rather than client-selected UUID headers.
 *
 * This module preserves UUID validation and safe cleanup of legacy client
 * identity tokens. It never creates unauthenticated anonymous users.
 */

export const CANDIDATE_USER_ID_STORAGE_KEY = "skillforge_candidate_user_id";

const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/**
 * Validates whether a given string is a valid RFC 4122 UUID.
 */
export function isValidUUID(id: unknown): id is string {
  if (typeof id !== "string") return false;
  return UUID_REGEX.test(id.trim());
}

/**
 * Retrieves the stored candidate user UUID from localStorage synchronously if already established.
 * Does NOT generate a random UUID on the client.
 * Returns null if executed during SSR or if no valid candidate UUID is stored.
 */
export function getCandidateUserId(): string | null {
  if (typeof window === "undefined" || typeof localStorage === "undefined") {
    return null;
  }

  try {
    const stored = localStorage.getItem(CANDIDATE_USER_ID_STORAGE_KEY);
    if (stored && isValidUUID(stored)) {
      return stored.trim();
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Explicitly sets or updates the candidate user UUID in localStorage.
 * Returns true if valid and successfully stored, false otherwise.
 */
export function setCandidateUserId(id: string): boolean {
  if (typeof window === "undefined" || typeof localStorage === "undefined") {
    return false;
  }

  if (!isValidUUID(id)) {
    return false;
  }

  try {
    localStorage.setItem(CANDIDATE_USER_ID_STORAGE_KEY, id.trim());
    return true;
  } catch {
    return false;
  }
}

/**
 * Clears legacy candidate user UUID and keys from localStorage.
 */
export function clearCandidateUserId(): void {
  if (typeof window === "undefined" || typeof localStorage === "undefined") {
    return;
  }

  try {
    localStorage.removeItem(CANDIDATE_USER_ID_STORAGE_KEY);
    localStorage.removeItem("skillforge_candidate_id");
  } catch {
    // ignore
  }
}

/**
 * Deprecated in Phase 5: Authentication is cookie-based via HttpOnly session cookies.
 * Does not create unauthenticated users on the backend.
 * Returns null.
 */
export async function ensureCandidateIdentity(): Promise<string | null> {
  return null;
}
