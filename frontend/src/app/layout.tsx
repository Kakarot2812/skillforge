import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { CandidateProvider } from "@/context/CandidateContext";
import { ThemeProvider } from "@/context/ThemeContext";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
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
      className={`${inter.variable} h-full antialiased dark`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: antiFlashScript }} />
      </head>
      <body className="min-h-full flex flex-col bg-background text-foreground transition-colors duration-200">
        <ThemeProvider>
          <CandidateProvider>{children}</CandidateProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
