import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { CandidateProvider } from "@/context/CandidateContext";
import { ThemeProvider } from "@/context/ThemeContext";
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

const antiFlashScript = `
  (function() {
    try {
      var stored = localStorage.getItem('skillforge_theme');
      var isDark = stored === 'dark' || (!stored && true) || (stored === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
      if (isDark) {
        document.documentElement.classList.add('dark');
        document.documentElement.classList.remove('light');
        document.documentElement.setAttribute('data-theme', 'dark');
      } else {
        document.documentElement.classList.remove('dark');
        document.documentElement.classList.add('light');
        document.documentElement.setAttribute('data-theme', 'light');
      }
    } catch (e) {}
  })();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: antiFlashScript }} />
      </head>
      <body className="min-h-full flex flex-col bg-slate-50 dark:bg-[#0a0a0c] text-neutral-900 dark:text-neutral-100 transition-colors duration-200">
        <ThemeProvider>
          <CandidateProvider>{children}</CandidateProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
