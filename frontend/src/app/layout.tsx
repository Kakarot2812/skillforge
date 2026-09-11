import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { CandidateProvider } from "@/context/CandidateContext";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SkillForge AI — Evidence-Based AI Skill Gap & Career Roadmap",
  description:
    "SkillForge AI bridges candidate resumes, verifiable GitHub code artifacts, and data-driven industry demand to generate personalized career roadmaps.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-[#0a0a0c] text-neutral-100">
        <CandidateProvider>{children}</CandidateProvider>
      </body>
    </html>
  );
}
