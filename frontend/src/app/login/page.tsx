import type { Metadata } from "next";
import { LoginPage } from "@/components/auth/LoginPage";

export const metadata: Metadata = {
  title: "Sign In — SkillForge AI",
  description:
    "Log in to SkillForge AI to access your evidence-based skill gap analysis, verified GitHub code insights, and personalized career roadmaps.",
};

export default function Page() {
  return <LoginPage />;
}
