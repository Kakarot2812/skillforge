"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Eye,
  EyeOff,
  Loader2,
  AlertCircle,
  CheckCircle2,
  HelpCircle,
} from "lucide-react";
import {
  loginCandidate,
  signupCandidate,
  getRememberedEmail,
  isRememberMeActive,
} from "@/lib/auth";

export interface LoginFormProps {
  onPasswordFocusChange?: (isFocused: boolean) => void;
  onPasswordValueChange?: (value: string) => void;
  onPasswordVisibilityChange?: (isVisible: boolean) => void;
  onSuccess?: () => void;
  className?: string;
}

export const LoginForm: React.FC<LoginFormProps> = ({
  onPasswordFocusChange,
  onPasswordValueChange,
  onPasswordVisibilityChange,
  onSuccess,
  className = "",
}) => {
  const router = useRouter();

  // Mode: "login" | "signup"
  const [mode, setMode] = useState<"login" | "signup">("login");

  // Form fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [targetRole, setTargetRole] = useState("Full Stack Engineer");
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Status & validation states
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showForgotModal, setShowForgotModal] = useState(false);

  // Initialize remembered email on client mount
  useEffect(() => {
    let isCancelled = false;
    Promise.resolve().then(() => {
      if (isCancelled) return;
      const remembered = getRememberedEmail();
      const rememberActive = isRememberMeActive();
      if (remembered) {
        setEmail(remembered);
        setRememberMe(rememberActive);
      }
    });
    return () => {
      isCancelled = true;
    };
  }, []);

  // Handle password input changes & propagate to parent for mascot eyes
  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setPassword(val);
    onPasswordValueChange?.(val);
  };

  const handlePasswordFocus = () => {
    onPasswordFocusChange?.(true);
  };

  const handlePasswordBlur = () => {
    onPasswordFocusChange?.(false);
  };

  const handleTogglePasswordVisibility = () => {
    const nextState = !showPassword;
    setShowPassword(nextState);
    onPasswordVisibilityChange?.(nextState);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!email || !email.trim()) {
      setErrorMessage("Please enter your email address.");
      return;
    }

    const minPassLength = mode === "signup" ? 8 : 6;
    if (!password || password.length < minPassLength) {
      setErrorMessage(
        mode === "signup"
          ? "Password must be at least 8 characters."
          : "Password must be at least 6 characters."
      );
      return;
    }

    setIsLoading(true);

    try {
      const res =
        mode === "signup"
          ? await signupCandidate({
              email,
              password,
              fullName: fullName?.trim() || undefined,
              targetRole: targetRole || undefined,
            })
          : await loginCandidate({
              email,
              password,
              rememberMe,
            });

      if (res.success && res.user) {
        setSuccessMessage(
          mode === "signup"
            ? "Account created successfully! Redirecting..."
            : "Welcome back! Redirecting to dashboard..."
        );

        if (onSuccess) {
          onSuccess();
        } else {
          setTimeout(() => {
            router.push("/");
          }, 700);
        }
      } else {
        setErrorMessage(res.error || "Authentication failed. Please verify your credentials.");
      }
    } catch {
      setErrorMessage("An unexpected network error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    window.location.href = `${apiBase}/api/v1/auth/google/login`;
  };

  return (
    <div
      className={`w-full max-w-[380px] sm:max-w-[400px] mx-auto flex flex-col items-center select-none ${className}`}
    >
      {/* Top Geometric Cube Emblem from Reference */}
      <Link href="/" className="mb-5 flex flex-col items-center group" aria-label="SkillForge Home">
        <div className="w-11 h-11 flex items-center justify-center text-neutral-900 dark:text-neutral-100 group-hover:scale-105 transition-transform">
          {/* Isometric 3D Geometric Cube Logo matching reference */}
          <svg viewBox="0 0 36 36" fill="none" className="w-9 h-9">
            {/* Top Face */}
            <path
              d="M 18 3 L 31 10.5 L 18 18 L 5 10.5 Z"
              className="fill-zinc-800 dark:fill-indigo-500"
            />
            {/* Left Face */}
            <path
              d="M 5 10.5 L 18 18 L 18 33 L 5 25.5 Z"
              className="fill-zinc-700 dark:fill-indigo-600"
            />
            {/* Right Face */}
            <path
              d="M 18 18 L 31 10.5 L 31 25.5 L 18 33 Z"
              className="fill-zinc-900 dark:fill-indigo-700"
            />
            {/* Inner negative cut accent */}
            <circle cx="18" cy="18" r="2.5" className="fill-zinc-100 dark:fill-zinc-900" />
          </svg>
        </div>
      </Link>

      {/* Main Heading & Subtitle */}
      <div className="text-center space-y-1.5 mb-8">
        <h1 className="text-2xl sm:text-[28px] font-extrabold tracking-tight text-neutral-900 dark:text-neutral-100">
          {mode === "login" ? "Welcome back!" : "Create an account"}
        </h1>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 font-normal">
          {mode === "login"
            ? "Please enter your details"
            : "Enter your information to get started"}
        </p>
      </div>

      {/* Error / Success Notifications */}
      {errorMessage && (
        <div
          role="alert"
          className="w-full mb-4 p-3 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 flex items-start gap-2.5 text-xs text-rose-700 dark:text-rose-300 animate-in fade-in duration-150"
        >
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <div className="flex-1 font-medium">{errorMessage}</div>
        </div>
      )}

      {successMessage && (
        <div
          role="status"
          className="w-full mb-4 p-3 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 flex items-start gap-2.5 text-xs text-emerald-700 dark:text-emerald-300 animate-in fade-in duration-150"
        >
          <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
          <div className="flex-1 font-medium">{successMessage}</div>
        </div>
      )}

      {/* Login / Sign Up Form */}
      <form onSubmit={handleSubmit} className="w-full space-y-6">
        {mode === "signup" && (
          <>
            <div className="space-y-1">
              <label
                htmlFor="fullname-input"
                className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300"
              >
                Full Name
              </label>
              <input
                id="fullname-input"
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Alex Mercer"
                className="w-full pb-2 pt-1 text-sm bg-transparent border-b border-neutral-300 dark:border-neutral-700 text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-500 focus:outline-none focus:border-neutral-900 dark:focus:border-neutral-100 transition-colors"
              />
            </div>

            <div className="space-y-1">
              <label
                htmlFor="targetrole-input"
                className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300"
              >
                Target Role
              </label>
              <select
                id="targetrole-input"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                className="w-full pb-2 pt-1 text-sm bg-transparent border-b border-neutral-300 dark:border-neutral-700 text-neutral-900 dark:text-neutral-100 focus:outline-none focus:border-neutral-900 dark:focus:border-neutral-100 transition-colors"
              >
                <option value="Full Stack Engineer" className="dark:bg-neutral-900">Full Stack Engineer</option>
                <option value="Backend Engineer" className="dark:bg-neutral-900">Backend Engineer (Python / Go)</option>
                <option value="Frontend Engineer" className="dark:bg-neutral-900">Frontend Engineer (React / Next.js)</option>
                <option value="AI / ML Engineer" className="dark:bg-neutral-900">AI / ML Engineer</option>
              </select>
            </div>
          </>
        )}

        {/* Email Underline Field matching reference */}
        <div className="space-y-1">
          <label
            htmlFor="email-input"
            className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300"
          >
            Email
          </label>
          <input
            id="email-input"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder=""
            className="w-full pb-2 pt-1 text-sm bg-transparent border-b border-neutral-300 dark:border-neutral-700 text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-500 focus:outline-none focus:border-neutral-900 dark:focus:border-neutral-100 transition-colors"
          />
        </div>

        {/* Password Underline Field matching reference with Eye toggle */}
        <div className="space-y-1">
          <label
            htmlFor="password-input"
            className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300"
          >
            Password
          </label>
          <div className="relative flex items-center border-b border-neutral-300 dark:border-neutral-700 focus-within:border-neutral-900 dark:focus-within:border-neutral-100 transition-colors">
            <input
              id="password-input"
              type={showPassword ? "text" : "password"}
              required
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              value={password}
              onChange={handlePasswordChange}
              onFocus={handlePasswordFocus}
              onBlur={handlePasswordBlur}
              placeholder=""
              className="w-full pb-2 pt-1 pr-8 text-sm bg-transparent text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={handleTogglePasswordVisibility}
              className="absolute right-0 bottom-2 text-neutral-600 dark:text-neutral-400 hover:text-black dark:hover:text-white transition-colors cursor-pointer"
              title={showPassword ? "Hide password" : "Show password"}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4 stroke-[1.8]" />
              ) : (
                <Eye className="h-4 w-4 stroke-[1.8]" />
              )}
            </button>
          </div>
        </div>

        {/* Remember me & Forgot password Row matching reference */}
        <div className="flex items-center justify-between text-xs pt-0.5">
          <label className="flex items-center gap-2 cursor-pointer group select-none">
            <input
              type="checkbox"
              id="remember-me"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-neutral-300 dark:border-neutral-700 text-neutral-900 dark:text-indigo-600 focus:ring-0 cursor-pointer"
            />
            <span className="text-neutral-600 dark:text-neutral-400 text-[11px] sm:text-xs">
              Remember me
            </span>
          </label>

          {mode === "login" && (
            <button
              type="button"
              onClick={() => setShowForgotModal(true)}
              className="text-neutral-400 dark:text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 text-[11px] sm:text-xs transition-colors cursor-pointer"
            >
              Forgot password?
            </button>
          )}
        </div>

        {/* Solid Dark Pill "Log in" Button matching reference */}
        <div className="space-y-3 pt-2">
          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 px-6 rounded-full font-medium text-xs sm:text-sm text-white bg-[#18181b] dark:bg-indigo-600 hover:bg-neutral-800 dark:hover:bg-indigo-500 active:scale-[0.99] disabled:opacity-60 transition-all flex items-center justify-center gap-2 shadow-sm cursor-pointer"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Processing...</span>
              </>
            ) : (
              <span>{mode === "login" ? "Log in" : "Sign up"}</span>
            )}
          </button>

          {/* Light Gray / Dark Pill "Log in with Google" Button matching reference */}
          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={isLoading}
            className="w-full py-2.5 px-6 rounded-full font-medium text-xs sm:text-sm text-neutral-800 dark:text-neutral-200 bg-[#f4f4f5] dark:bg-neutral-800/80 hover:bg-[#eaeaea] dark:hover:bg-neutral-800 active:scale-[0.99] border border-transparent dark:border-neutral-700 transition-all flex items-center justify-center gap-2.5 cursor-pointer"
          >
            {/* Google G SVG */}
            <svg className="h-4 w-4" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"
              />
              <path
                fill="#34A853"
                d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24z"
              />
              <path
                fill="#FBBC05"
                d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 10.04 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
              />
              <path
                fill="#EA4335"
                d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
              />
            </svg>
            <span>Log in with Google</span>
          </button>
        </div>
      </form>

      {/* Bottom Switch Link matching reference */}
      <div className="mt-12 text-center">
        <p className="text-xs text-neutral-500 dark:text-neutral-400">
          {mode === "login" ? (
            <>
              Don&apos;t have an account?{" "}
              <button
                type="button"
                onClick={() => {
                  setMode("signup");
                  setErrorMessage(null);
                }}
                className="font-semibold text-neutral-800 dark:text-neutral-200 hover:text-black dark:hover:text-white transition-colors cursor-pointer"
              >
                Sign Up
              </button>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <button
                type="button"
                onClick={() => {
                  setMode("login");
                  setErrorMessage(null);
                }}
                className="font-semibold text-neutral-800 dark:text-neutral-200 hover:text-black dark:hover:text-white transition-colors cursor-pointer"
              >
                Log In
              </button>
            </>
          )}
        </p>
      </div>

      {/* Forgot Password Modal */}
      {showForgotModal && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150"
        >
          <div className="w-full max-w-sm p-6 bg-white dark:bg-neutral-900 rounded-3xl shadow-2xl border border-neutral-100 dark:border-neutral-800 space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-2xl bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 flex items-center justify-center">
                <HelpCircle className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-neutral-900 dark:text-neutral-100">Reset Password</h3>
                <p className="text-xs text-neutral-500 dark:text-neutral-400">SkillForge Candidate Account</p>
              </div>
            </div>

            <p className="text-xs text-neutral-600 dark:text-neutral-300 leading-relaxed">
              SkillForge authenticates candidates securely via canonical UUID rows. You can log in directly using your registered email address to instantly restore your verified roadmap and evidence profile.
            </p>

            <div className="pt-2">
              <button
                type="button"
                onClick={() => setShowForgotModal(false)}
                className="w-full py-2.5 px-4 rounded-full bg-neutral-900 dark:bg-indigo-600 text-white font-medium text-xs hover:bg-neutral-800 dark:hover:bg-indigo-500 transition-colors cursor-pointer"
              >
                Return to Login
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
