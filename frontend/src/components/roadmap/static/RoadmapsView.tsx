"use client";

import React from "react";
import SkillRoadmap from "./SkillRoadmap";

export interface RoadmapsViewProps {
  initialRoadmapId?: string;
}

export const RoadmapsView: React.FC<RoadmapsViewProps> = ({ initialRoadmapId }) => {
  return (
    <div className="w-full">
      <SkillRoadmap initialRoadmapId={initialRoadmapId} />
    </div>
  );
};

export default RoadmapsView;
