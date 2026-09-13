/**
 * Authentication and Candidate Session Manager for SkillForge AI.
 *
 * Post-MVP Login Phase 5:
 * Integrates with backend session endpoints (/api/v1/auth) using secure
 * HttpOnly session cookies (skillforge_session). Never stores session tokens
 * in browser storage.
 */

import {
  clearCandidateUserId,
  isValidUUID,
} from "./identity";

export interface UserProfile {
  id: string;
  email: string;
  full_name?: string | null;
  target_role?: string | null;
  auth_provider?: string;
  is_active?: boolean;
  active_resume_id?: string | null;
  connected_github_username?: string | null;
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
 * Safely purges legacy candidate UUID and unauthenticated storage keys.
 * Ensures old anonymous data is never silently merged into an authenticated account.
 */
export function clearLegacyStorage(): void {
  if (typeof window === "undefined" || typeof localStorage === "undefined") {
    return;
  }
  try {
    localStorage.removeItem("skillforge_candidate_id");
    localStorage.removeItem("skillforge_candidate_user_id");
    localStorage.removeItem("skillforge_active_resume_id");
    localStorage.removeItem("skillforge_active_resume_filename");
    localStorage.removeItem("skillforge_connected_github_user");
  } catch {
    // ignore
  }
}

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
 * Logs in candidate with email and password via POST /api/v1/auth/login.
 * Transmits credentials with credentials: "include" so the backend HttpOnly
 * session cookie (skillforge_session) is set automatically.
 */
export async function loginCandidate(params: {
  email: string;
  password: string;
  rememberMe?: boolean;
}): Promise<AuthResponse> {
  const { email, password, rememberMe = false } = params;

  if (!email || !email.trim()) {
    return {
      success: false,
      error: "Please enter your email address.",
    };
  }

  if (!password || !password.trim()) {
    return {
      success: false,
      error: "Please enter your password.",
    };
  }

  const cleanEmail = email.trim().toLowerCase();
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  try {
    const response = await fetch(`${apiBase}/api/v1/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({
        email: cleanEmail,
        password,
        remember_me: rememberMe,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      let message = "Authentication failed. Please verify your credentials.";

      if (response.status === 401) {
        // Backend-safe message that does not expose whether account exists
        message = "Invalid email or password. Please try again.";
      } else if (response.status === 422) {
        message = "Invalid login details. Please check your inputs.";
      } else if (response.status === 503) {
        message = "Authentication service temporarily unavailable. Please try again later.";
      } else if (errorData?.detail && typeof errorData.detail === "string") {
        message = errorData.detail;
      }

      return {
        success: false,
        error: message,
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

    // Purge old anonymous localStorage artifacts
    clearLegacyStorage();

    // Cache safe profile
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
 * Registers candidate with email, password, and profile details via POST /api/v1/auth/signup.
 * Establishes an authenticated session cookie immediately upon creation.
 */
export async function signupCandidate(params: {
  email: string;
  password: string;
  fullName?: string;
  targetRole?: string;
}): Promise<AuthResponse> {
  const { email, password, fullName, targetRole } = params;

  if (!email || !email.trim()) {
    return {
      success: false,
      error: "Please enter a valid email address.",
    };
  }

  if (!password || password.length < 8) {
    return {
      success: false,
      error: "Password must be at least 8 characters.",
    };
  }

  const cleanEmail = email.trim().toLowerCase();
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  try {
    const response = await fetch(`${apiBase}/api/v1/auth/signup`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({
        email: cleanEmail,
        password,
        full_name: fullName?.trim() || null,
        target_role: targetRole?.trim() || null,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      let message = "Account registration failed.";

      if (response.status === 409) {
        message = "An account with this email address already exists. Please log in instead.";
      } else if (response.status === 422) {
        message = "Password must be between 8 and 128 characters.";
      } else if (response.status === 503) {
        message = "Authentication service temporarily unavailable. Please try again later.";
      } else if (errorData?.detail && typeof errorData.detail === "string") {
        message = errorData.detail;
      }

      return {
        success: false,
        error: message,
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

    // Purge old anonymous localStorage artifacts
    clearLegacyStorage();

    if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
      try {
        localStorage.setItem(USER_PROFILE_STORAGE_KEY, JSON.stringify(userData));
      } catch {
        // ignore
      }

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
 * Fetches the currently authenticated candidate's profile via GET /api/v1/auth/me.
 * Restores user session state on page refresh or browser restart using the HttpOnly cookie.
 * Returns null if unauthenticated or session expired (401).
 */
export async function fetchCurrentCandidate(): Promise<UserProfile | null> {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  try {
    const res = await fetch(`${apiBase}/api/v1/auth/me`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
    });

    if (res.ok) {
      const user: UserProfile = await res.json();
      if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
        try {
          localStorage.setItem(USER_PROFILE_STORAGE_KEY, JSON.stringify(user));
        } catch {
          // ignore
        }
      }
      return user;
    }

    // If 401 (session missing/expired) or other error: visitor is unauthenticated
    if (res.status === 401 || res.status === 403) {
      if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
        try {
          localStorage.removeItem(USER_PROFILE_STORAGE_KEY);
        } catch {
          // ignore
        }
      }
      clearLegacyStorage();
    }

    return null;
  } catch {
    // On network failure during startup, fall back to locally cached profile if present
    return getStoredUserProfile();
  }
}

/**
 * Revokes active server session via POST /api/v1/auth/logout and clears client profile state.
 */
export async function logoutCandidate(): Promise<void> {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  try {
    await fetch(`${apiBase}/api/v1/auth/logout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
    });
  } catch {
    // Even if logout network call fails, proceed to clear local frontend state
  }

  clearCandidateUserId();
  clearLegacyStorage();

  if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
    try {
      localStorage.removeItem(USER_PROFILE_STORAGE_KEY);
    } catch {
      // ignore
    }

    window.dispatchEvent(
      new CustomEvent("skillforge:identity-updated", {
        detail: { userId: null, user: null },
      })
    );
    window.dispatchEvent(new Event("skillforge:resume-stale"));
    window.dispatchEvent(
      new CustomEvent("skillforge:github-evidence-updated", {
        detail: { githubUsername: null },
      })
    );
  }
}

/**
 * Backward compatibility wrapper for authenticateCandidate.
 * Directs to loginCandidate.
 */
export async function authenticateCandidate(params: {
  email: string;
  password?: string;
  fullName?: string;
  targetRole?: string;
  rememberMe?: boolean;
}): Promise<AuthResponse> {
  if (params.password) {
    return loginCandidate({
      email: params.email,
      password: params.password,
      rememberMe: params.rememberMe,
    });
  }
  return {
    success: false,
    error: "Password is required for candidate authentication.",
  };
}
