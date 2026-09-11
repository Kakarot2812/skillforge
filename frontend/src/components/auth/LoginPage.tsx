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
    if (typeof window !== "undefined") {
      setCursorPos({
        x: window.innerWidth / 3,
        y: window.innerHeight / 2,
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
    <div className="min-h-screen w-full bg-[#dcdfe4] text-neutral-900 flex flex-col items-center justify-center p-3 sm:p-6 lg:p-10 select-none">
      {/* Top Floating Back Button */}
      <div className="w-full max-w-5xl mb-3 flex items-center justify-between px-2">
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/90 backdrop-blur-sm border border-neutral-200 shadow-sm text-xs font-medium text-neutral-700 hover:text-black hover:bg-white transition-all group"
        >
          <ArrowLeft className="h-3.5 w-3.5 group-hover:-translate-x-0.5 transition-transform" />
          <span>Back to Dashboard</span>
        </Link>
      </div>

      {/* Main Centered Split Card Frame matching reference */}
      <div className="w-full max-w-5xl min-h-[580px] lg:min-h-[640px] rounded-[2rem] sm:rounded-[2.5rem] bg-white shadow-2xl shadow-neutral-900/10 border border-white/60 overflow-hidden grid grid-cols-1 lg:grid-cols-12">
        {/* LEFT SIDE: Light Gray Canvas with 4 Colorful Geometric Mascot Characters */}
        <div className="lg:col-span-6 xl:col-span-7 relative bg-[#e7e9ed] flex flex-col justify-between p-6 sm:p-10 border-b lg:border-b-0 lg:border-r border-neutral-200/60 overflow-hidden min-h-[360px] sm:min-h-[440px] lg:min-h-full">
          {/* Top subtle branding watermark */}
          <div className="hidden lg:flex items-center gap-2 text-neutral-400 text-xs font-mono select-none">
            <span className="font-semibold text-neutral-600">SkillForge</span>
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

        {/* RIGHT SIDE: Pure White Modern Login Card */}
        <div className="lg:col-span-6 xl:col-span-5 bg-white flex flex-col items-center justify-center p-6 sm:p-10 lg:p-12 relative">
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
