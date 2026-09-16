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
    <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
      {/* Freshness Timestamp */}
      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-subtle border border-border">
        <Calendar className="h-3.5 w-3.5 text-accent" />
        <span>
          Market Freshness: <strong className="text-foreground font-mono">{formattedDate}</strong>
        </span>
      </div>

      {/* Geographic Scope */}
      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-subtle border border-border">
        <MapPin className="h-3.5 w-3.5 text-foreground" />
        <span>
          Region: <strong className="text-foreground font-mono">{location}</strong>
        </span>
      </div>

      {/* Audit Verification */}
      {typeof auditRecordsCount === "number" && auditRecordsCount > 0 && (
        <div className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-subtle text-foreground border border-border font-mono text-[11px]">
          <ShieldCheck className="h-3.5 w-3.5 text-accent" />
          <span>{auditRecordsCount.toLocaleString()} Records</span>
        </div>
      )}
    </div>
  );
}
