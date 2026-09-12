"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

export type Theme = "light" | "dark" | "system";

export interface ThemeContextType {
  theme: Theme;
  resolvedTheme: "light" | "dark";
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [systemTheme, setSystemTheme] = useState<"light" | "dark">("dark");
  const [mounted, setMounted] = useState(false);

  // Initialize theme from localStorage and system preference on client mount
  useEffect(() => {
    let isCancelled = false;
    Promise.resolve().then(() => {
      if (isCancelled) return;
      try {
        const stored = localStorage.getItem("skillforge_theme") as Theme | null;
        if (stored && (stored === "light" || stored === "dark" || stored === "system")) {
          setThemeState(stored);
        } else {
          setThemeState("dark");
        }

        if (typeof window !== "undefined" && window.matchMedia) {
          const isDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
          setSystemTheme(isDark ? "dark" : "light");
        }
      } catch {
        setThemeState("dark");
      }
      setMounted(true);
    });

    return () => {
      isCancelled = true;
    };
  }, []);

  // Compute resolvedTheme purely from current theme state and system preference
  const resolvedTheme: "light" | "dark" = theme === "system" ? systemTheme : theme;

  // Sync class and data-theme attribute on <html> element
  useEffect(() => {
    if (!mounted) return;

    const root = document.documentElement;
    const effectiveTheme = resolvedTheme;

    if (effectiveTheme === "dark") {
      root.classList.add("dark");
      root.classList.remove("light");
      root.setAttribute("data-theme", "dark");
    } else {
      root.classList.remove("dark");
      root.classList.add("light");
      root.setAttribute("data-theme", "light");
    }

    try {
      localStorage.setItem("skillforge_theme", theme);
    } catch {}

    // Listen to system changes if theme is "system"
    if (theme === "system" && typeof window !== "undefined" && window.matchMedia) {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const handleChange = (e: MediaQueryListEvent) => {
        setSystemTheme(e.matches ? "dark" : "light");
      };
      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }
  }, [theme, resolvedTheme, mounted]);

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
  };

  const toggleTheme = () => {
    setThemeState((prev) => {
      const currentResolved =
        prev === "system"
          ? typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches
            ? "dark"
            : "light"
          : prev;
      return currentResolved === "dark" ? "light" : "dark";
    });
  };

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
};
