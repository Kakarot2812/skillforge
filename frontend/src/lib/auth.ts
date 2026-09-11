/**
 * Authentication and Candidate Session Manager for SkillForge AI.
 *
 * Reuses the existing backend user identity and API endpoints (/api/v1/users)
 * while managing browser session persistence, "Remember Me" preferences,
 * and cross-component identity synchronization.
 */

import {
  getCandidateUserId,
  setCandidateUserId,
  clearCandidateUserId,
  isValidUUID,
} from "./identity";

export interface UserProfile {
  id: string;
  email: string;
  full_name?: string | null;
  target_role?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface AuthResponse {
  success: boolean;
  user?: UserProfile;
  error?: string;
  statusCode?: number;
}

export const REMEMBER_ME_STORAGE_KEY = "skillforge_remember_me";
export const REMEMBER_EMAIL_STORAGE_KEY = "skillforge_remembered_email";
export const USER_PROFILE_STORAGE_KEY = "skillforge_user_profile";

/**
 * Retrieves remembered email from localStorage if user opted into Remember Me.
 */
export function getRememberedEmail(): string {
  if (typeof window === "undefined" || typeof localStorage === "undefined") {
    return "";
  }
  try {
    const isRemembered = localStorage.getItem(REMEMBER_ME_STORAGE_KEY) === "true";
    if (isRemembered) {
      return localStorage.getItem(REMEMBER_EMAIL_STORAGE_KEY) || "";
    }
    return "";
  } catch {
    return "";
  }
}

/**
 * Checks if "Remember Me" preference is active.
 */
export function isRememberMeActive(): boolean {
  if (typeof window === "undefined" || typeof localStorage === "undefined") {
    return false;
  }
  try {
    return localStorage.getItem(REMEMBER_ME_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

/**
 * Retrieves cached user profile from localStorage.
 */
export function getStoredUserProfile(): UserProfile | null {
  if (typeof window === "undefined" || typeof localStorage === "undefined") {
    return null;
  }
  try {
    const raw = localStorage.getItem(USER_PROFILE_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed.id === "string" && isValidUUID(parsed.id)) {
      return parsed as UserProfile;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Authenticates or registers a candidate with the backend POST /api/v1/users.
 * If user exists, backend returns the existing canonical user record.
 * Persists the canonical user UUID into localStorage as the active candidate.
 */
export async function authenticateCandidate(params: {
  email: string;
  fullName?: string;
  targetRole?: string;
  rememberMe?: boolean;
}): Promise<AuthResponse> {
  const { email, fullName, targetRole, rememberMe = false } = params;

  if (!email || !email.trim()) {
    return {
      success: false,
      error: "Please enter a valid email address.",
    };
  }

  const cleanEmail = email.trim().toLowerCase();
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  try {
    const response = await fetch(`${apiBase}/api/v1/users`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: cleanEmail,
        full_name: fullName?.trim() || null,
        target_role: targetRole?.trim() || null,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      const message =
        errorData?.error?.message ||
        errorData?.detail ||
        `Authentication failed with status ${response.status}.`;
      return {
        success: false,
        error: typeof message === "string" ? message : "Authentication failed.",
        statusCode: response.status,
      };
    }

    const userData: UserProfile = await response.json();

    if (!userData || !isValidUUID(userData.id)) {
      return {
        success: false,
        error: "Invalid user data returned from authentication service.",
      };
    }

    // Persist canonical candidate ID
    setCandidateUserId(userData.id);

    // Save profile cache
    if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
      try {
        localStorage.setItem(USER_PROFILE_STORAGE_KEY, JSON.stringify(userData));

        if (rememberMe) {
          localStorage.setItem(REMEMBER_ME_STORAGE_KEY, "true");
          localStorage.setItem(REMEMBER_EMAIL_STORAGE_KEY, cleanEmail);
        } else {
          localStorage.removeItem(REMEMBER_ME_STORAGE_KEY);
          localStorage.removeItem(REMEMBER_EMAIL_STORAGE_KEY);
        }
      } catch {
        // ignore quota errors
      }

      // Notify other components/windows
      window.dispatchEvent(
        new CustomEvent("skillforge:identity-updated", {
          detail: { userId: userData.id, user: userData },
        })
      );
    }

    return {
      success: true,
      user: userData,
    };
  } catch (err: unknown) {
    const message =
      err instanceof Error
        ? err.message
        : "Network error occurred while connecting to authentication service.";
    return {
      success: false,
      error: message,
    };
  }
}

/**
 * Fetches the currently authenticated candidate's profile from the backend.
 */
export async function fetchCurrentCandidate(): Promise<UserProfile | null> {
  const userId = getCandidateUserId();
  if (!userId) return null;

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  try {
    const res = await fetch(`${apiBase}/api/v1/users/me`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": userId,
      },
    });

    if (res.ok) {
      const user: UserProfile = await res.json();
      if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
        localStorage.setItem(USER_PROFILE_STORAGE_KEY, JSON.stringify(user));
      }
      return user;
    }

    // If /me returned 404 or 401, try direct /users/{id}
    const fallbackRes = await fetch(`${apiBase}/api/v1/users/${userId}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (fallbackRes.ok) {
      const user: UserProfile = await fallbackRes.json();
      if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
        localStorage.setItem(USER_PROFILE_STORAGE_KEY, JSON.stringify(user));
      }
      return user;
    }

    return null;
  } catch {
    return getStoredUserProfile();
  }
}

/**
 * Clears current session and logs out candidate.
 */
export function logoutCandidate(): void {
  clearCandidateUserId();
  if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
    try {
      localStorage.removeItem(USER_PROFILE_STORAGE_KEY);
      localStorage.removeItem("skillforge_active_resume_id");
      localStorage.removeItem("skillforge_active_resume_filename");
      localStorage.removeItem("skillforge_connected_github_user");
    } catch {
      // ignore
    }

    window.dispatchEvent(
      new CustomEvent("skillforge:identity-updated", {
        detail: { userId: null, user: null },
      })
    );
  }
}
