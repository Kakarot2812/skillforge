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
    <div className="bg-neutral-900/60 border border-neutral-800 rounded-2xl p-6 backdrop-blur-md relative overflow-hidden">
      {/* Header Bar */}
      <div className="flex items-center justify-between pb-4 border-b border-neutral-800">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Briefcase className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-neutral-200">Target Career Role</h3>
            <p className="text-xs text-neutral-500">Configure target industry profile</p>
          </div>
        </div>
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 uppercase tracking-wider font-mono">
          Career Tracks
        </span>
      </div>

      <div className="mt-4 space-y-2.5">
        <div className="flex items-center justify-between">
          <label className="text-xs font-medium text-neutral-400">Select Target Role</label>
          <span className="text-[11px] text-neutral-500 font-mono">5 Career Tracks</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {loading ? (
            <div className="col-span-2 text-xs text-neutral-500 p-4 text-center">Loading target roles...</div>
          ) : (
            roles.map((role) => {
              const isSelected = selectedRoleId === role.role_id;
              const focusDesc = ROLE_FOCUS_MAP[role.slug] || role.category || "Industry standard track";
              return (
                <button
                  key={role.role_id}
                  type="button"
                  onClick={() => onSelectRole?.(role.role_id)}
                  className={`p-3 rounded-xl text-left border transition-all cursor-pointer ${
                    isSelected
                      ? "bg-neutral-800/90 border-blue-500/50 text-neutral-100 shadow-sm ring-1 ring-blue-500/30"
                      : "bg-neutral-950/40 border-neutral-800/80 text-neutral-400 hover:border-neutral-700 hover:text-neutral-200"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold">{role.title}</span>
                    {isSelected && <Check className="h-3.5 w-3.5 text-blue-400" />}
                  </div>
                  <p className="text-[11px] text-neutral-500 mt-1 truncate">{focusDesc}</p>
                </button>
              );
            })
          )}
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-neutral-800/50 flex items-center justify-between text-xs text-neutral-500">
        <span>Selected Track: <strong className="text-neutral-300 font-medium">{activeRole?.title || "None"}</strong></span>
        <span className="text-[11px] text-emerald-400/80 font-medium">Synchronized with Career Intelligence</span>
      </div>
    </div>
  );
}
