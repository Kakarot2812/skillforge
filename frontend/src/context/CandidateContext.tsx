"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { ensureCandidateIdentity } from "@/lib/identity";
import { fetchResumeDetail } from "@/lib/api";
import { getStoredUserProfile, logoutCandidate, UserProfile } from "@/lib/auth";

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

  // Initial load from localStorage and backend identity
  useEffect(() => {
    let isCancelled = false;
    if (typeof window !== "undefined") {
      Promise.resolve().then(async () => {
        const candidateId = await ensureCandidateIdentity();
        if (isCancelled) return;

        const activeResume = localStorage.getItem("skillforge_active_resume_id");
        const activeFileName = localStorage.getItem("skillforge_active_resume_filename");

        if (activeResume && candidateId) {
          const detailRes = await fetchResumeDetail(activeResume, candidateId);
          if (isCancelled) return;
          if (
            !detailRes.success ||
            !detailRes.data ||
            detailRes.status === 403 ||
            detailRes.status === 404 ||
            detailRes.data.user_id !== candidateId
          ) {
            localStorage.removeItem("skillforge_active_resume_id");
            localStorage.removeItem("skillforge_active_resume_filename");
            setHasResume(false);
            setResumeFileName(null);
            setResumeId(null);
          } else {
            setHasResume(true);
            setResumeFileName(detailRes.data.filename || activeFileName);
            setResumeId(activeResume);
          }
        } else {
          setHasResume(false);
          setResumeFileName(null);
          setResumeId(null);
        }

        const activeGitHub = localStorage.getItem("skillforge_connected_github_user");
        setConnectedGitHubUser(activeGitHub || null);

        const storedProfile = getStoredUserProfile();
        setUserProfile(storedProfile);
      });
    }
    return () => {
      isCancelled = true;
    };
  }, []);

  // Sync identity updates
  useEffect(() => {
    const handleIdentityUpdated = (event: Event) => {
      const customEv = event as CustomEvent<{ user?: UserProfile | null }>;
      if (customEv.detail && customEv.detail.user !== undefined) {
        setUserProfile(customEv.detail.user);
      } else {
        setUserProfile(getStoredUserProfile());
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
        setConnectedGitHubUser(customEv.detail.githubUsername);
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
  }, []);

  const handleGitHubChange = useCallback((username: string | null) => {
    setConnectedGitHubUser(username);
  }, []);

  const handleLogout = useCallback(() => {
    logoutCandidate();
    setUserProfile(null);
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
