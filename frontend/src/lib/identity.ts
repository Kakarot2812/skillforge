/**
 * Candidate Identity Helper for SkillForge AI.
 *
 * Provides a minimal, persistent browser-side candidate UUID for compliance
 * with Post-MVP endpoints requiring the `X-User-Id` header.
 *
 * Invariants:
 * - Persistent in browser localStorage under key: `skillforge_candidate_user_id`.
 * - SSR-safe: Never accesses localStorage or window on the server.
 * - Deterministic retrieval after initial establishment.
 * - Validates format before reusing.
 * - NEVER generates a client-side random UUID and assumes it exists on the backend.
 * - Canonical user row in PostgreSQL must exist before user-scoped operations.
 * - Concurrency protection: Single inflight promise prevents duplicate user creation.
 * - Does not expose identity to UI components.
 * - Transmitted exclusively as `X-User-Id` by the API client.
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
 * Clears the candidate user UUID from localStorage.
 */
export function clearCandidateUserId(): void {
  if (typeof window === "undefined" || typeof localStorage === "undefined") {
    return;
  }

  try {
    localStorage.removeItem(CANDIDATE_USER_ID_STORAGE_KEY);
  } catch {
    // ignore
  }
}

let inflightIdentityPromise: Promise<string | null> | null = null;

/**
 * Asynchronously verifies or establishes a legitimate backend candidate identity.
 *
 * 1. Checks if a candidate UUID is stored locally.
 * 2. If stored, verifies with GET /api/v1/users/{id} that the user exists in PostgreSQL.
 *    - If confirmed (200 OK): returns the canonical UUID.
 *    - If not found (404): clears stale storage and proceeds to registration.
 * 3. If no candidate exists or previous was stale:
 *    Calls POST /api/v1/users to create a legitimate backend User row.
 *    Persists returned canonical UUID in localStorage.
 *    Returns canonical UUID.
 *
 * Thread-safe / concurrency-safe via singleton inflight promise.
 */
export async function ensureCandidateIdentity(): Promise<string | null> {
  if (typeof window === "undefined" || typeof localStorage === "undefined") {
    return null;
  }

  if (inflightIdentityPromise) {
    return inflightIdentityPromise;
  }

  inflightIdentityPromise = (async () => {
    try {
      const apiBase =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      const stored = localStorage.getItem(CANDIDATE_USER_ID_STORAGE_KEY);
      if (stored && isValidUUID(stored)) {
        const cleanId = stored.trim();
        try {
          const verifyRes = await fetch(`${apiBase}/api/v1/users/${cleanId}`, {
            method: "GET",
            headers: { "Content-Type": "application/json" },
          });

          if (verifyRes.ok) {
            return cleanId;
          }

          if (verifyRes.status === 404) {
            // Stale candidate UUID: clear it and proceed to create legitimate candidate
            clearCandidateUserId();
          }
        } catch {
          // If network error verifying existing, assume stored ID is valid
          return cleanId;
        }
      }

      // Explicitly register / establish candidate user on backend
      const res = await fetch(`${apiBase}/api/v1/users`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      if (res.ok) {
        const json = await res.json();
        const canonicalId = json?.id;
        if (canonicalId && isValidUUID(canonicalId)) {
          setCandidateUserId(canonicalId);
          return canonicalId;
        }
      }

      return null;
    } catch {
      return null;
    } finally {
      inflightIdentityPromise = null;
    }
  })();

  return inflightIdentityPromise;
}
