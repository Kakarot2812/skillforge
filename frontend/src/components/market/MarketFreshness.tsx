"use client";

import React from "react";
import { Calendar, MapPin, ShieldCheck } from "lucide-react";

export interface MarketFreshnessProps {
  dataFreshness?: string;
  location?: string;
  auditRecordsCount?: number;
}

function formatFreshnessDate(dateStr?: string): string {
  if (!dateStr) return "Synchronized";
  try {
    const parts = dateStr.split("-");
    if (parts.length === 3) {
      const year = parseInt(parts[0], 10);
      const monthIndex = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const date = new Date(year, monthIndex, day);
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    }
    return dateStr;
  } catch {
    return dateStr;
  }
}

export default function MarketFreshness({
  dataFreshness,
  location = "India",
  auditRecordsCount,
}: MarketFreshnessProps) {
  const formattedDate = formatFreshnessDate(dataFreshness);

  return (
    <div className="flex flex-wrap items-center gap-2.5 text-xs text-neutral-400">
      {/* Freshness Timestamp */}
      <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-neutral-950/80 border border-neutral-800">
        <Calendar className="h-3.5 w-3.5 text-indigo-400" />
        <span>
          Market Freshness: <strong className="text-neutral-200 font-mono">{formattedDate}</strong>
        </span>
      </div>

      {/* Geographic Scope */}
      <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-neutral-950/80 border border-neutral-800">
        <MapPin className="h-3.5 w-3.5 text-emerald-400" />
        <span>
          Region: <strong className="text-neutral-200 font-medium">{location}</strong>
        </span>
      </div>

      {/* Audit Verification */}
      {typeof auditRecordsCount === "number" && auditRecordsCount > 0 && (
        <div className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
          <ShieldCheck className="h-3.5 w-3.5" />
          <span>{auditRecordsCount.toLocaleString()} Verified Market Records</span>
        </div>
      )}
    </div>
  );
}
