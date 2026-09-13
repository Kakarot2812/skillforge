"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { fetchResumeDetail } from "@/lib/api";
import {
  fetchCurrentCandidate,
  logoutCandidate,
  clearLegacyStorage,
  UserProfile,
} from "@/lib/auth";

interface CandidateContextType {
  selectedRoleId: string;
  setSelectedRoleId: (roleId: string) => void;
  hasResume: boolean;
  resumeFileName: string | null;
  resumeId: string | null;
  connectedGitHubUser: string | null;
  userProfile: UserProfile | null;
  candidateReady: boolean;
  handleResumeChange: (has: boolean, filename?: string, id?: string) => void;
  handleGitHubChange: (username: string | null) => void;
  handleLogout: () => void;
}

const CandidateContext = createContext<CandidateContextType | undefined>(undefined);

export const CandidateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedRoleId, setSelectedRoleId] = useState<string>("");
  const [hasResume, setHasResume] = useState<boolean>(false);
  const [resumeFileName, setResumeFileName] = useState<string | null>(null);
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [connectedGitHubUser, setConnectedGitHubUser] = useState<string | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);

  // Initial load from backend session via GET /api/v1/auth/me
  useEffect(() => {
    let isCancelled = false;
    if (typeof window !== "undefined") {
      Promise.resolve().then(async () => {
        try {
          const profile = await fetchCurrentCandidate();
          if (isCancelled) return;

          if (profile) {
            setUserProfile(profile);
            const activeResume = profile.active_resume_id;
            const activeGitHub = profile.connected_github_username;

            if (activeResume) {
              const detailRes = await fetchResumeDetail(activeResume);
              if (isCancelled) return;
              if (
                !detailRes.success ||
                !detailRes.data ||
                detailRes.status === 403 ||
                detailRes.status === 404
              ) {
                setHasResume(false);
                setResumeFileName(null);
                setResumeId(null);
              } else {
                setHasResume(true);
                setResumeFileName(detailRes.data.filename);
                setResumeId(activeResume);
              }
            } else {
              setHasResume(false);
              setResumeFileName(null);
              setResumeId(null);
            }

            setConnectedGitHubUser(activeGitHub || null);
            if (profile.target_role) {
              setSelectedRoleId(profile.target_role);
            }
          } else {
            setUserProfile(null);
            setHasResume(false);
            setResumeFileName(null);
            setResumeId(null);
            setConnectedGitHubUser(null);
            clearLegacyStorage();
          }
        } catch {
          if (!isCancelled) {
            setUserProfile(null);
            setHasResume(false);
            setResumeFileName(null);
            setResumeId(null);
            setConnectedGitHubUser(null);
          }
        }
      });
    }
    return () => {
      isCancelled = true;
    };
  }, []);

  // Sync identity updates across tabs / components
  useEffect(() => {
    const handleIdentityUpdated = (event: Event) => {
      const customEv = event as CustomEvent<{ user?: UserProfile | null }>;
      if (customEv.detail && customEv.detail.user !== undefined) {
        const u = customEv.detail.user;
        setUserProfile(u || null);
        if (u) {
          setHasResume(Boolean(u.active_resume_id));
          setResumeId(u.active_resume_id || null);
          setConnectedGitHubUser(u.connected_github_username || null);
          if (u.target_role) {
            setSelectedRoleId(u.target_role);
          }
        } else {
          setHasResume(false);
          setResumeFileName(null);
          setResumeId(null);
          setConnectedGitHubUser(null);
        }
      }
    };
    window.addEventListener("skillforge:identity-updated", handleIdentityUpdated);
    return () => {
      window.removeEventListener("skillforge:identity-updated", handleIdentityUpdated);
    };
  }, []);

  // Sync stale resume events
  useEffect(() => {
    const handleStaleResume = () => {
      setHasResume(false);
      setResumeFileName(null);
      setResumeId(null);
      setUserProfile((prev) => (prev ? { ...prev, active_resume_id: null } : null));
    };
    window.addEventListener("skillforge:resume-stale", handleStaleResume);
    return () => {
      window.removeEventListener("skillforge:resume-stale", handleStaleResume);
    };
  }, []);

  // Sync GitHub updates
  useEffect(() => {
    const handleGitHubUpdated = (event: Event) => {
      const customEv = event as CustomEvent<{ githubUsername?: string | null }>;
      if (customEv.detail && customEv.detail.githubUsername !== undefined) {
        const gh = customEv.detail.githubUsername;
        setConnectedGitHubUser(gh);
        setUserProfile((prev) => (prev ? { ...prev, connected_github_username: gh } : null));
      }
    };
    window.addEventListener("skillforge:github-evidence-updated", handleGitHubUpdated);
    return () => {
      window.removeEventListener("skillforge:github-evidence-updated", handleGitHubUpdated);
    };
  }, []);

  const handleResumeChange = useCallback((has: boolean, filename?: string, id?: string) => {
    setHasResume(has);
    setResumeFileName(filename || null);
    setResumeId(has ? (id || null) : null);
    setUserProfile((prev) => (prev ? { ...prev, active_resume_id: has ? (id || null) : null } : null));
  }, []);

  const handleGitHubChange = useCallback((username: string | null) => {
    setConnectedGitHubUser(username);
    setUserProfile((prev) => (prev ? { ...prev, connected_github_username: username } : null));
  }, []);

  const handleLogout = useCallback(async () => {
    await logoutCandidate();
    setUserProfile(null);
    setHasResume(false);
    setResumeFileName(null);
    setResumeId(null);
    setConnectedGitHubUser(null);
  }, []);

  const candidateReady = Boolean(hasResume || connectedGitHubUser);

  return (
    <CandidateContext.Provider
      value={{
        selectedRoleId,
        setSelectedRoleId,
        hasResume,
        resumeFileName,
        resumeId,
        connectedGitHubUser,
        userProfile,
        candidateReady,
        handleResumeChange,
        handleGitHubChange,
        handleLogout,
      }}
    >
      {children}
    </CandidateContext.Provider>
  );
};

export const useCandidate = () => {
  const context = useContext(CandidateContext);
  if (!context) {
    throw new Error("useCandidate must be used within a CandidateProvider");
  }
  return context;
};
