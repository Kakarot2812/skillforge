"use client";

import React, { useState, useEffect } from "react";
import { Briefcase, Check } from "lucide-react";
import { fetchRoles, JobRole } from "../lib/api";

const ROLE_FOCUS_MAP: Record<string, string> = {
  "backend-engineer": "APIs, Distributed Systems, Databases, Microservices",
  "full-stack-engineer": "React, Node.js/Python, System Architecture, UI/UX",
  "frontend-engineer": "React, Next.js, Modern UI/UX, Component Architecture",
  "cloud-devops-engineer": "Kubernetes, Docker, CI/CD, Terraform, Cloud Infra",
  "ai-ml-engineer": "Deep Learning, PyTorch, Model Deployment, RAG Pipelines",
};

export interface TargetRoleSelectorProps {
  selectedRoleId?: string;
  onSelectRole?: (roleId: string) => void;
}

export default function TargetRoleSelector({
  selectedRoleId,
  onSelectRole,
}: TargetRoleSelectorProps = {}) {
  const [roles, setRoles] = useState<JobRole[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const res = await fetchRoles();
      if (res.success && res.data?.data && res.data.data.length > 0) {
        setRoles(res.data.data);
      }
      setLoading(false);
    }
    load();
  }, []);

  const activeRole = roles.find((r) => r.role_id === selectedRoleId) || roles[0];

  return (
    <div className="editorial-card p-6 sm:p-7 relative select-none">
      {/* Header Bar */}
      <div className="flex items-center justify-between pb-4 border-b border-border">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold uppercase tracking-wider text-foreground">
              Target Career Track
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-border bg-surface-subtle text-muted uppercase tracking-wider">
              Benchmark Role
            </span>
          </div>
          <p className="text-xs text-muted">
            Configure target industry profile to benchmark capabilities against
          </p>
        </div>
        <span className="hidden sm:inline-block text-[11px] font-mono text-muted">
          5 Career Tracks Available
        </span>
      </div>

      <div className="mt-5 space-y-3">
        <div className="flex items-center justify-between text-xs">
          <label className="font-medium text-secondary">
            Select Track
          </label>
          <span className="text-[11px] font-mono text-muted">
            Click to activate
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {loading ? (
            <div className="col-span-full text-xs text-muted p-6 text-center">
              Loading target roles...
            </div>
          ) : (
            roles.map((role) => {
              const isSelected = selectedRoleId === role.role_id;
              const focusDesc = ROLE_FOCUS_MAP[role.slug] || role.category || "Industry standard track";
              return (
                <button
                  key={role.role_id}
                  type="button"
                  onClick={() => onSelectRole?.(role.role_id)}
                  className={`p-3.5 rounded-md text-left border transition-all cursor-pointer ${
                    isSelected
                      ? "bg-surface-subtle border-foreground text-foreground shadow-xs font-semibold"
                      : "bg-surface border-border text-secondary hover:border-border-hover hover:text-foreground"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold tracking-tight">{role.title}</span>
                    {isSelected ? (
                      <Check className="h-3.5 w-3.5 text-accent shrink-0" />
                    ) : (
                      <span className="h-1.5 w-1.5 rounded-full bg-border shrink-0" />
                    )}
                  </div>
                  <p className="text-[11px] text-muted mt-1 truncate font-normal">
                    {focusDesc}
                  </p>
                </button>
              );
            })
          )}
        </div>
      </div>

      <div className="mt-5 pt-3.5 border-t border-border flex items-center justify-between text-xs text-muted">
        <span>
          Selected Track: <strong className="text-foreground font-semibold">{activeRole?.title || "None"}</strong>
        </span>
        <span className="text-[11px] font-mono text-accent">
          Active In Intelligence Matrix
        </span>
      </div>
    </div>
  );
}
