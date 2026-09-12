"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { InteractiveCharacter } from "./InteractiveCharacter";
import { LoginForm } from "./LoginForm";

export const LoginPage: React.FC = () => {
  // Global mouse coordinates
  const [cursorPos, setCursorPos] = useState({ x: 0, y: 0 });

  // Password field interactive states
  const [isPasswordFocused, setIsPasswordFocused] = useState(false);
  const [passwordValue, setPasswordValue] = useState("");
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);

  // RAF ref for high-performance mouse tracking
  const rafId = useRef<number | null>(null);

  // Track global mouse movement smoothly
  useEffect(() => {
    let isCancelled = false;
    if (typeof window !== "undefined") {
      Promise.resolve().then(() => {
        if (!isCancelled) {
          setCursorPos({
            x: window.innerWidth / 3,
            y: window.innerHeight / 2,
          });
        }
      });
    }

    const handleMouseMove = (e: MouseEvent) => {
      if (rafId.current !== null) {
        cancelAnimationFrame(rafId.current);
      }

      rafId.current = requestAnimationFrame(() => {
        setCursorPos({ x: e.clientX, y: e.clientY });
      });
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });

    return () => {
      isCancelled = true;
      window.removeEventListener("mousemove", handleMouseMove);
      if (rafId.current !== null) {
        cancelAnimationFrame(rafId.current);
      }
    };
  }, []);

  const isTypingPassword = passwordValue.length > 0;

  const handlePasswordFocusChange = useCallback((isFocused: boolean) => {
    setIsPasswordFocused(isFocused);
  }, []);

  const handlePasswordValueChange = useCallback((value: string) => {
    setPasswordValue(value);
  }, []);

  const handlePasswordVisibilityChange = useCallback((isVisible: boolean) => {
    setIsPasswordVisible(isVisible);
  }, []);

  return (
    <div className="min-h-screen w-full bg-[#dcdfe4] dark:bg-[#0c0d12] text-neutral-900 dark:text-neutral-100 flex flex-col items-center justify-center p-3 sm:p-6 lg:p-10 select-none transition-colors">
      {/* Top Floating Back Button */}
      <div className="w-full max-w-5xl mb-3 flex items-center justify-between px-2">
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/90 dark:bg-neutral-900/90 backdrop-blur-sm border border-neutral-200 dark:border-neutral-800 shadow-sm text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:text-black dark:hover:text-white hover:bg-white dark:hover:bg-neutral-800 transition-all group"
        >
          <ArrowLeft className="h-3.5 w-3.5 group-hover:-translate-x-0.5 transition-transform" />
          <span>Back to Dashboard</span>
        </Link>
      </div>

      {/* Main Centered Split Card Frame matching reference */}
      <div className="w-full max-w-5xl min-h-[580px] lg:min-h-[640px] rounded-[2rem] sm:rounded-[2.5rem] bg-white dark:bg-[#14151a] shadow-2xl shadow-neutral-900/10 dark:shadow-black/60 border border-white/60 dark:border-neutral-800 overflow-hidden grid grid-cols-1 lg:grid-cols-12 transition-colors">
        {/* LEFT SIDE: Light Gray Canvas with 4 Colorful Geometric Mascot Characters */}
        <div className="lg:col-span-6 xl:col-span-7 relative bg-[#e7e9ed] dark:bg-[#1a1b24] flex flex-col justify-between p-6 sm:p-10 border-b lg:border-b-0 lg:border-r border-neutral-200/60 dark:border-neutral-800 overflow-hidden min-h-[360px] sm:min-h-[440px] lg:min-h-full transition-colors">
          {/* Top subtle branding watermark */}
          <div className="hidden lg:flex items-center gap-2 text-neutral-400 dark:text-neutral-500 text-xs font-mono select-none">
            <span className="font-semibold text-neutral-600 dark:text-neutral-300">SkillForge</span>
            <span>•</span>
            <span>Career Intelligence</span>
          </div>

          {/* Interactive Character Cluster */}
          <div className="flex-1 flex items-end justify-center w-full">
            <InteractiveCharacter
              cursorX={cursorPos.x}
              cursorY={cursorPos.y}
              isPasswordFocused={isPasswordFocused}
              isTypingPassword={isTypingPassword}
              isPasswordVisible={isPasswordVisible}
            />
          </div>
        </div>

        {/* RIGHT SIDE: Pure White / Modern Dark Login Card */}
        <div className="lg:col-span-6 xl:col-span-5 bg-white dark:bg-[#14151a] flex flex-col items-center justify-center p-6 sm:p-10 lg:p-12 relative transition-colors">
          <LoginForm
            onPasswordFocusChange={handlePasswordFocusChange}
            onPasswordValueChange={handlePasswordValueChange}
            onPasswordVisibilityChange={handlePasswordVisibilityChange}
          />
        </div>
      </div>
    </div>
  );
};
