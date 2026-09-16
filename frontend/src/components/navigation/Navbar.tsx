"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sun,
  Moon,
  User as UserIcon,
  LogOut,
  Menu,
  X,
} from "lucide-react";
import { useCandidate } from "@/context/CandidateContext";
import { useTheme } from "@/context/ThemeContext";

export type NavTab = "home" | "analyzer" | "dashboard" | "roadmaps" | "assistant" | "pdf-test";

export interface NavbarProps {
  activeTab?: NavTab;
  onSelectTab?: (tab: "home" | "analyzer" | "dashboard") => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, onSelectTab }) => {
  const pathname = usePathname();
  const { userProfile, handleLogout } = useCandidate();
  const { resolvedTheme, toggleTheme } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const currentTab: NavTab =
    activeTab ||
    (pathname === "/analyzer"
      ? "analyzer"
      : pathname === "/dashboard"
      ? "dashboard"
      : pathname === "/roadmaps"
      ? "roadmaps"
      : pathname === "/roadmap-pdf-test"
      ? "pdf-test"
      : "home");

  const navItems = [
    { id: "home", label: "Home", href: "/" },
    { id: "analyzer", label: "Skill Analyzer", href: "/analyzer" },
    { id: "dashboard", label: "Dashboard", href: "/dashboard" },
    { id: "roadmaps", label: "Roadmaps", href: "/roadmaps" },
    { id: "assistant", label: "AI Assistant", href: "/dashboard#ai-career-assistant-section" },
  ] as const;

  const handleNavClick = (id: typeof navItems[number]["id"], href: string, e: React.MouseEvent) => {
    setMobileMenuOpen(false);
    if (onSelectTab && pathname === "/") {
      if (id === "home" || id === "analyzer" || id === "dashboard") {
        e.preventDefault();
        onSelectTab(id);
        window.scrollTo({ top: 0, behavior: "smooth" });
      } else if (id === "assistant") {
        e.preventDefault();
        onSelectTab("dashboard");
        setTimeout(() => {
          const el = document.getElementById("ai-career-assistant-section");
          if (el) el.scrollIntoView({ behavior: "smooth" });
        }, 120);
      }
    }
  };

  return (
    <header className="sticky top-0 z-50 w-full h-16 bg-background/90 backdrop-blur-md border-b border-border select-none transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between">
        {/* Brand SF Logo & Name */}
        <Link
          href="/"
          onClick={(e) => handleNavClick("home", "/", e)}
          className="group flex items-center gap-3 cursor-pointer select-none"
          aria-label="SkillForge AI Home"
        >
          {/* SF Monogram Emblem with subtle hover scale & restrained teal edge glow */}
          <div className="relative flex items-center justify-center">
            <div className="h-8 w-8 rounded-md bg-foreground text-background flex items-center justify-center font-bold text-xs tracking-wider border border-border/80 transition-all duration-300 ease-out group-hover:scale-105 group-hover:border-accent group-hover:shadow-[0_0_12px_rgba(13,148,136,0.35)] dark:group-hover:shadow-[0_0_14px_rgba(20,184,166,0.4)]">
              <span>SF</span>
            </div>
          </div>

          {/* Clean Editorial Wordmark */}
          <div className="flex items-baseline gap-1">
            <span className="font-bold text-sm tracking-[0.14em] uppercase text-foreground transition-colors">
              SkillForge
            </span>
            <span className="text-[10px] font-mono tracking-widest text-accent font-semibold">
              .AI
            </span>
          </div>
        </Link>

        {/* Center Editorial Navigation Links (Desktop) */}
        <nav className="hidden md:flex items-center gap-6 lg:gap-8 text-xs">
          {navItems.map((item) => {
            const isActive = currentTab === item.id;
            return (
              <Link
                key={item.id}
                href={item.href}
                onClick={(e) => handleNavClick(item.id, item.href, e)}
                className={`relative py-1 font-medium tracking-wide transition-colors duration-200 cursor-pointer ${
                  isActive
                    ? "text-foreground font-semibold after:content-[''] after:absolute after:-bottom-1.5 after:left-0 after:right-0 after:h-[1.5px] after:bg-accent"
                    : "text-muted hover:text-foreground"
                }`}
              >
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Right Section: Market, Theme Toggle, Auth, Mobile Menu */}
        <div className="flex items-center gap-2.5 sm:gap-3 text-xs">
          {/* Market Indicator */}
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border bg-surface-subtle/50 text-[11px] font-medium text-secondary">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            <span>Market: India</span>
          </div>

          {/* Theme Switcher Button */}
          <button
            type="button"
            onClick={toggleTheme}
            title={resolvedTheme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            aria-label={resolvedTheme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            className="p-1.5 rounded-md border border-border bg-surface hover:bg-surface-subtle text-secondary hover:text-foreground transition-all duration-200 cursor-pointer flex items-center justify-center"
          >
            {resolvedTheme === "dark" ? (
              <Sun className="h-4 w-4 text-secondary hover:text-amber-400 transition-colors" />
            ) : (
              <Moon className="h-4 w-4 text-secondary hover:text-foreground transition-colors" />
            )}
          </button>

          {/* User Profile or Sign In CTA */}
          {userProfile ? (
            <div className="flex items-center gap-1.5">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border bg-surface-subtle text-foreground text-xs font-medium">
                <UserIcon className="h-3.5 w-3.5 text-accent" />
                <span className="max-w-[100px] truncate">
                  {userProfile.email.split("@")[0]}
                </span>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                title="Log out"
                aria-label="Log out"
                className="p-1.5 rounded-md border border-border bg-surface hover:bg-surface-subtle text-muted hover:text-danger transition-colors cursor-pointer"
              >
                <LogOut className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="editorial-btn-primary !py-1.5 !px-3.5 !text-xs !rounded-md"
            >
              Sign In
            </Link>
          )}

          {/* Mobile Menu Hamburger Toggle */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle Navigation Menu"
            className="md:hidden p-1.5 rounded-md border border-border bg-surface text-secondary hover:text-foreground transition-colors cursor-pointer"
          >
            {mobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-border bg-surface px-4 py-3 space-y-2 animate-in fade-in duration-150">
          <nav className="flex flex-col space-y-1">
            {navItems.map((item) => {
              const isActive = currentTab === item.id;
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  onClick={(e) => handleNavClick(item.id, item.href, e)}
                  className={`px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-surface-subtle text-foreground font-semibold border-l-2 border-accent"
                      : "text-muted hover:text-foreground hover:bg-surface-subtle"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="pt-2 border-t border-border flex items-center justify-between text-[11px] text-muted px-3">
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />
              Market: India
            </span>
          </div>
        </div>
      )}
    </header>
  );
};

