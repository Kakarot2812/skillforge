"use client";

import React from "react";
import SkillGapExplorer, { SkillGapExplorerProps } from "./SkillGapExplorer";

/**
 * SkillAnalysisPlaceholder is replaced by the completed Phase 5 SkillGapExplorer.
 * Re-exports the full interactive Skill Gap & Priority Engine to prevent any stale placeholder rendering.
 */
export default function SkillAnalysisPlaceholder(props: SkillGapExplorerProps) {
  return <SkillGapExplorer {...props} />;
}
