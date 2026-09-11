"use client";

import React, { useEffect, useState, useCallback } from "react";
import { checkBackendHealth, checkDatabaseHealth, DbHealthResponse } from "@/lib/api";
import { CheckCircle2, XCircle, RefreshCw, Database, Server, Cpu, ShieldCheck } from "lucide-react";

interface StatusState {
  loading: boolean;
  backendConnected: boolean;
  backendStatus: string;
  latencyMs: number;
  dbConnected: boolean;
  pgvectorInstalled: boolean;
  dbVersion?: string;
  lastChecked: string | null;
}

export default function ConnectionStatus() {
  const [state, setState] = useState<StatusState>({
    loading: true,
    backendConnected: false,
    backendStatus: "Checking...",
    latencyMs: 0,
    dbConnected: false,
    pgvectorInstalled: false,
    lastChecked: null,
  });

  const checkHealth = useCallback(async () => {
    const backendResult = await checkBackendHealth();
    let dbResult: DbHealthResponse = {
      status: "error",
      database: "disconnected",
      pgvector_installed: false,
    };

    if (backendResult.connected) {
      dbResult = await checkDatabaseHealth();
    }

    return { backendResult, dbResult };
  }, []);

  const handleManualRefresh = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true }));
    const { backendResult, dbResult } = await checkHealth();
    setState({
      loading: false,
      backendConnected: backendResult.connected,
      backendStatus: backendResult.status,
      latencyMs: backendResult.latencyMs,
      dbConnected: dbResult.database === "connected",
      pgvectorInstalled: dbResult.pgvector_installed,
      dbVersion: dbResult.database_version,
      lastChecked: new Date().toLocaleTimeString(),
    });
  }, [checkHealth]);

  useEffect(() => {
    let isMounted = true;

    const execute = async () => {
      const { backendResult, dbResult } = await checkHealth();
      if (!isMounted) return;
      setState({
        loading: false,
        backendConnected: backendResult.connected,
        backendStatus: backendResult.status,
        latencyMs: backendResult.latencyMs,
        dbConnected: dbResult.database === "connected",
        pgvectorInstalled: dbResult.pgvector_installed,
        dbVersion: dbResult.database_version,
        lastChecked: new Date().toLocaleTimeString(),
      });
    };

    void execute();
    const interval = setInterval(execute, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [checkHealth]);

  return (
    <div className="w-full bg-neutral-900/80 border border-neutral-800 rounded-2xl p-6 backdrop-blur-xl shadow-2xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-neutral-800/80">
        <div>
          <div className="flex items-center gap-2">
            <div className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <h2 className="text-lg font-semibold text-neutral-100 tracking-tight">
              Stack Connectivity Monitor
            </h2>
            <span className="text-xs font-mono px-2 py-0.5 rounded-md bg-neutral-800 text-neutral-400 border border-neutral-700">
              Live Diagnostics
            </span>
          </div>
          <p className="text-xs text-neutral-400 mt-1">
            Real-time, unsimulated health verification across Browser → Next.js → FastAPI → PostgreSQL + pgvector
          </p>
        </div>

        <button
          onClick={handleManualRefresh}
          disabled={state.loading}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 active:bg-neutral-800 text-neutral-200 text-xs font-medium transition-all duration-150 border border-neutral-700/80 disabled:opacity-50 disabled:cursor-not-allowed self-start sm:self-auto cursor-pointer"
          title="Re-run live health check"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${state.loading ? "animate-spin text-emerald-400" : ""}`} />
          <span>{state.loading ? "Checking..." : "Refresh"}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-5">
        {/* Backend Card */}
        <div className="bg-neutral-950/60 border border-neutral-800/90 rounded-xl p-4 flex items-start gap-3.5">
          <div
            className={`p-2.5 rounded-lg border ${
              state.backendConnected
                ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                : "bg-rose-500/10 border-rose-500/20 text-rose-400"
            }`}
          >
            <Server className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-neutral-400">FastAPI Backend</span>
              <span className="text-[10px] font-mono text-neutral-500">
                {state.latencyMs ? `${state.latencyMs}ms` : "--"}
              </span>
            </div>
            <div className="flex items-center gap-1.5 mt-1">
              {state.backendConnected ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                  <span className="text-sm font-semibold text-emerald-300">
                    Backend: Connected
                  </span>
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4 text-rose-400 shrink-0" />
                  <span className="text-sm font-semibold text-rose-300">
                    Backend: {state.backendStatus}
                  </span>
                </>
              )}
            </div>
            <p className="text-[11px] text-neutral-500 mt-1 truncate">
              {state.backendConnected ? "HTTP 200 OK • port 8000" : "Cannot reach backend service"}
            </p>
          </div>
        </div>

        {/* Database Card */}
        <div className="bg-neutral-950/60 border border-neutral-800/90 rounded-xl p-4 flex items-start gap-3.5">
          <div
            className={`p-2.5 rounded-lg border ${
              state.dbConnected
                ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                : "bg-rose-500/10 border-rose-500/20 text-rose-400"
            }`}
          >
            <Database className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-neutral-400">PostgreSQL</span>
              <span className="text-[10px] font-mono text-neutral-500">Port 5432</span>
            </div>
            <div className="flex items-center gap-1.5 mt-1">
              {state.dbConnected ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                  <span className="text-sm font-semibold text-emerald-300">
                    Database: Connected
                  </span>
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4 text-rose-400 shrink-0" />
                  <span className="text-sm font-semibold text-rose-300">
                    Database: Disconnected
                  </span>
                </>
              )}
            </div>
            <p className="text-[11px] text-neutral-500 mt-1 truncate">
              {state.dbConnected ? (state.dbVersion || "PostgreSQL 16+ Active") : "Database query failed"}
            </p>
          </div>
        </div>

        {/* pgvector Card */}
        <div className="bg-neutral-950/60 border border-neutral-800/90 rounded-xl p-4 flex items-start gap-3.5">
          <div
            className={`p-2.5 rounded-lg border ${
              state.pgvectorInstalled
                ? "bg-indigo-500/10 border-indigo-500/20 text-indigo-400"
                : "bg-amber-500/10 border-amber-500/20 text-amber-400"
            }`}
          >
            <Cpu className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-neutral-400">pgvector Extension</span>
              <ShieldCheck className="h-3.5 w-3.5 text-indigo-400/80" />
            </div>
            <div className="flex items-center gap-1.5 mt-1">
              {state.pgvectorInstalled ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-indigo-400 shrink-0" />
                  <span className="text-sm font-semibold text-indigo-300">
                    pgvector: Active
                  </span>
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4 text-amber-400 shrink-0" />
                  <span className="text-sm font-semibold text-amber-300">
                    pgvector: Not Detected
                  </span>
                </>
              )}
            </div>
            <p className="text-[11px] text-neutral-500 mt-1 truncate">
              {state.pgvectorInstalled
                ? "Vector extension registered"
                : "Run CREATE EXTENSION vector"}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-neutral-800/60 flex items-center justify-between text-[11px] text-neutral-500">
        <span>Environment: Local Development</span>
        <span>Last checked: {state.lastChecked || "In progress..."}</span>
      </div>
    </div>
  );
}
