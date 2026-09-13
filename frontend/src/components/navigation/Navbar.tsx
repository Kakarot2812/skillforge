"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sparkles,
  Home,
  ScanLine,
  LayoutDashboard,
  LogIn,
  LogOut,
  User as UserIcon,
  Sun,
  Moon,
} from "lucide-react";
import { useCandidate } from "@/context/CandidateContext";
import { useTheme } from "@/context/ThemeContext";

export interface NavbarProps {
  activeTab?: "home" | "analyzer" | "dashboard";
  onSelectTab?: (tab: "home" | "analyzer" | "dashboard") => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, onSelectTab }) => {
  const pathname = usePathname();
  const { userProfile, handleLogout } = useCandidate();
  const { resolvedTheme, toggleTheme } = useTheme();

  const currentTab =
    activeTab ||
    (pathname === "/analyzer"
      ? "analyzer"
      : pathname === "/dashboard"
      ? "dashboard"
      : pathname === "/login"
      ? ""
      : "home");

  const navItems = [
    { id: "home", label: "Home", href: "/", icon: Home },
    { id: "analyzer", label: "Skill Analyzer", href: "/analyzer", icon: ScanLine },
    { id: "dashboard", label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  ] as const;

  return (
    <header className="sticky top-0 z-50 w-full h-14 bg-white/85 dark:bg-neutral-950/90 backdrop-blur-md border-b border-neutral-200/80 dark:border-neutral-800/80 select-none transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        {/* Brand Logo & Compact Name */}
        <Link
          href="/"
          onClick={() => onSelectTab?.("home")}
          className="flex items-center gap-2.5 group"
          aria-label="SkillForge AI Home"
        >
          <div className="h-7 w-7 rounded-lg bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center shadow-md group-hover:scale-105 transition-transform">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <span className="font-bold text-sm sm:text-base tracking-tight text-neutral-900 dark:text-white">
            SkillForge<span className="text-emerald-600 dark:text-emerald-400">.ai</span>
          </span>
        </Link>

        {/* Center Navigation Links */}
        <nav className="flex items-center gap-1 p-1 bg-neutral-100/90 dark:bg-neutral-900/60 rounded-xl border border-neutral-200/80 dark:border-neutral-800/60 text-xs">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return onSelectTab ? (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectTab(item.id)}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg font-medium transition-all cursor-pointer ${
                  isActive
                    ? "bg-white dark:bg-neutral-800 text-emerald-600 dark:text-emerald-400 font-semibold shadow-xs border border-neutral-200/60 dark:border-transparent"
                    : "text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200 hover:bg-neutral-200/60 dark:hover:bg-neutral-800/50"
                }`}
              >
                <Icon className={`h-3.5 w-3.5 ${isActive ? "text-emerald-600 dark:text-emerald-400" : "text-neutral-500 dark:text-neutral-400"}`} />
                <span>{item.label}</span>
              </button>
            ) : (
              <Link
                key={item.id}
                href={item.href}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg font-medium transition-all ${
                  isActive
                    ? "bg-white dark:bg-neutral-800 text-emerald-600 dark:text-emerald-400 font-semibold shadow-xs border border-neutral-200/60 dark:border-transparent"
                    : "text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200 hover:bg-neutral-200/60 dark:hover:bg-neutral-800/50"
                }`}
              >
                <Icon className={`h-3.5 w-3.5 ${isActive ? "text-emerald-600 dark:text-emerald-400" : "text-neutral-500 dark:text-neutral-400"}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Right Section: Theme Toggle, Market & Authentication */}
        <div className="flex items-center gap-2 sm:gap-2.5 text-xs">
          {/* Theme Switcher Button */}
          <button
            type="button"
            onClick={toggleTheme}
            title={resolvedTheme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            aria-label={resolvedTheme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            className="p-1.5 rounded-lg bg-neutral-100 dark:bg-neutral-900 hover:bg-neutral-200 dark:hover:bg-neutral-800 border border-neutral-200 dark:border-neutral-800 text-neutral-600 dark:text-neutral-300 hover:text-amber-500 dark:hover:text-amber-300 transition-all cursor-pointer flex items-center justify-center shadow-xs"
          >
            {resolvedTheme === "dark" ? (
              <Sun className="h-4 w-4 text-amber-400 transition-transform hover:rotate-45" />
            ) : (
              <Moon className="h-4 w-4 text-indigo-600 transition-transform hover:-rotate-12" />
            )}
          </button>

          <div className="hidden md:flex items-center gap-1.5 text-neutral-600 dark:text-neutral-400 font-medium text-xs bg-neutral-100 dark:bg-neutral-900/60 px-2.5 py-1 rounded-lg border border-neutral-200 dark:border-neutral-800/60">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span>Market: India</span>
          </div>

          {userProfile ? (
            <div className="flex items-center gap-1.5">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-neutral-100 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 text-neutral-800 dark:text-neutral-300">
                <UserIcon className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                <span className="max-w-[120px] truncate font-medium text-xs">
                  {userProfile.full_name || userProfile.email.split("@")[0]}
                </span>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                title="Log out"
                aria-label="Log out"
                className="p-1.5 rounded-lg bg-neutral-100 dark:bg-neutral-900 hover:bg-neutral-200 dark:hover:bg-neutral-850 border border-neutral-200 dark:border-neutral-800 text-neutral-600 dark:text-neutral-400 hover:text-rose-500 transition-colors cursor-pointer"
              >
                <LogOut className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs shadow-sm transition-all"
            >
              <LogIn className="h-3.5 w-3.5" />
              <span>Sign In</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
};
