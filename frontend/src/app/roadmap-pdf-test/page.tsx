"use client";

import React, { Suspense, useState, useEffect, useId } from "react";
import { useSearchParams } from "next/navigation";
import {
  FileText,
  Download,
  ExternalLink,
  Loader2,
  AlertCircle,
  CheckCircle2,
  FileCheck,
  ShieldCheck,
  Zap,
  Info,
} from "lucide-react";
import { Navbar } from "@/components/navigation/Navbar";
import { getCandidateUserId, isValidUUID } from "@/lib/identity";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Default real records seeded in database for quick testing
const DEFAULT_VALID_USER_ID = "545af71d-d432-434f-9353-77063a733fda";
const DEFAULT_VALID_ROADMAP_ID = "5d06b4c8-235d-4efe-9d55-3b16135d821f";
const DEFAULT_UNAUTHORIZED_USER_ID = "e5c070b6-fcdd-4dd9-a8a5-0a781e1c7614";

type GenerationStatus = "Ready" | "Generating" | "Success" | "Failed";

interface GenerationMetadata {
  httpStatus: number;
  contentType: string;
  fileSizeBytes: number;
  filename: string;
  durationMs: number;
}

function RoadmapPdfTestContent() {
  const searchParams = useSearchParams();
  const roadmapInputId = useId();
  const userInputId = useId();

  // Inputs
  const [roadmapId, setRoadmapId] = useState<string>("");
  const [userId, setUserId] = useState<string>("");

  // States
  const [status, setStatus] = useState<GenerationStatus>("Ready");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<GenerationMetadata | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState<boolean>(false);

  // Initialize from searchParams or stored identity
  useEffect(() => {
    const qRoadmap = searchParams.get("roadmap_id") || searchParams.get("roadmapId");
    const qUser = searchParams.get("user_id") || searchParams.get("userId");

    if (qRoadmap) {
      setRoadmapId(qRoadmap.trim());
    } else {
      setRoadmapId(DEFAULT_VALID_ROADMAP_ID);
    }

    if (qUser) {
      setUserId(qUser.trim());
    } else {
      const storedId = getCandidateUserId();
      setUserId(storedId || DEFAULT_VALID_USER_ID);
    }
  }, [searchParams]);

  // Clean up object URL on unmount or re-generation
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  /**
   * Safe mapping for HTTP and network errors
   */
  const mapSafeErrorMessage = (statusCode: number, rawDetail?: string): string => {
    switch (statusCode) {
      case 401:
        return "Authentication required: Missing or invalid User ID in X-User-Id header.";
      case 403:
        return "Cross-user access denied: You do not own this roadmap.";
      case 404:
        return rawDetail && rawDetail.toLowerCase().includes("user")
          ? "User not found in database."
          : "Roadmap not found in database.";
      case 422:
        return "Invalid Roadmap ID or User ID format. Please ensure valid UUIDs.";
      case 500:
        return "Roadmap integrity or PDF document compilation failed. Please try again.";
      case 502:
        return "AI narrative generation service unavailable. Please check Gemini API status.";
      case 504:
        return "Gemini generation timed out. Please try again.";
      default:
        return `PDF generation request failed (HTTP ${statusCode}). Please check backend status.`;
    }
  };

  /**
   * Helper to parse filename from Content-Disposition header
   */
  const extractFilename = (disposition: string | null, fallbackRoadmapId: string): string => {
    if (disposition) {
      const match = disposition.match(/filename="?([^";]+)"?/i);
      if (match && match[1]) {
        return match[1].trim();
      }
    }
    return `skillforge-roadmap-${fallbackRoadmapId.slice(0, 8)}.pdf`;
  };

  /**
   * Helper to format bytes nicely
   */
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  /**
   * Action 1: Generate & Preview PDF (download=false)
   */
  const handleGenerateAndPreview = async () => {
    const cleanRoadmap = roadmapId.trim();
    const cleanUser = userId.trim();

    if (!cleanRoadmap) {
      setErrorMessage("Roadmap ID is required.");
      setStatus("Failed");
      return;
    }
    if (!cleanUser) {
      setErrorMessage("User ID is required.");
      setStatus("Failed");
      return;
    }

    // Reset previous states
    setErrorMessage(null);
    setSuccessMessage(null);
    setStatus("Generating");
    const startTime = performance.now();

    try {
      const url = `${API_BASE_URL}/api/v1/roadmaps/${encodeURIComponent(cleanRoadmap)}/pdf?download=false`;
      const response = await fetch(url, {
        method: "GET",
        headers: {
          "X-User-Id": cleanUser,
        },
      });

      const durationMs = Math.round(performance.now() - startTime);

      if (!response.ok) {
        let detail = "";
        try {
          const errJson = await response.json();
          detail = errJson?.detail || "";
        } catch {
          // ignore json parse error
        }
        const safeError = mapSafeErrorMessage(response.status, detail);
        setErrorMessage(safeError);
        setStatus("Failed");
        setMetadata({
          httpStatus: response.status,
          contentType: response.headers.get("content-type") || "unknown",
          fileSizeBytes: 0,
          filename: "",
          durationMs,
        });
        return;
      }

      // Successful PDF Blob
      const blob = await response.blob();
      const contentType = response.headers.get("content-type") || "application/pdf";
      const disposition = response.headers.get("content-disposition");
      const filename = extractFilename(disposition, cleanRoadmap);

      // Create browser Object URL
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
      const objectUrl = URL.createObjectURL(blob);
      setPreviewUrl(objectUrl);

      setStatus("Success");
      setSuccessMessage("PDF generated successfully");
      setMetadata({
        httpStatus: response.status,
        contentType,
        fileSizeBytes: blob.size,
        filename,
        durationMs,
      });
    } catch (err: unknown) {
      const durationMs = Math.round(performance.now() - startTime);
      setErrorMessage("Network error: Failed to connect to FastAPI backend at " + API_BASE_URL);
      setStatus("Failed");
      setMetadata({
        httpStatus: 0,
        contentType: "none",
        fileSizeBytes: 0,
        filename: "",
        durationMs,
      });
    }
  };

  /**
   * Action 2: Download PDF (download=true)
   */
  const handleDownload = async () => {
    const cleanRoadmap = roadmapId.trim();
    const cleanUser = userId.trim();

    if (!cleanRoadmap || !cleanUser) {
      setErrorMessage("Both Roadmap ID and User ID are required to download.");
      setStatus("Failed");
      return;
    }

    setErrorMessage(null);
    setIsDownloading(true);

    try {
      const url = `${API_BASE_URL}/api/v1/roadmaps/${encodeURIComponent(cleanRoadmap)}/pdf?download=true`;
      const response = await fetch(url, {
        method: "GET",
        headers: {
          "X-User-Id": cleanUser,
        },
      });

      if (!response.ok) {
        let detail = "";
        try {
          const errJson = await response.json();
          detail = errJson?.detail || "";
        } catch {
          // ignore
        }
        setErrorMessage(mapSafeErrorMessage(response.status, detail));
        setIsDownloading(false);
        return;
      }

      const blob = await response.blob();
      const disposition = response.headers.get("content-disposition");
      const filename = extractFilename(disposition, cleanRoadmap);

      // Trigger browser download
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(downloadUrl), 60000);

      setIsDownloading(false);
    } catch {
      setErrorMessage("Network error: Failed to download PDF from backend.");
      setIsDownloading(false);
    }
  };

  const isWorking = status === "Generating" || isDownloading;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0a0a0c] text-neutral-900 dark:text-neutral-100 flex flex-col transition-colors duration-200">
      <Navbar activeTab="pdf-test" />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Header Section */}
        <div className="border-b border-neutral-200 dark:border-neutral-800 pb-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border dark:border-emerald-800/60 mb-2">
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>Phase 5 Manual Test Harness</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">
                AI Roadmap PDF
              </h1>
              <p className="mt-1 text-sm sm:text-base text-neutral-600 dark:text-neutral-400">
                Generate your personalized SkillForge roadmap as a verified PDF.
              </p>
            </div>

            {/* Quick preset badges */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="text-neutral-500 font-medium">Quick Test Presets:</span>
              <button
                type="button"
                onClick={() => {
                  setUserId(DEFAULT_VALID_USER_ID);
                  setRoadmapId(DEFAULT_VALID_ROADMAP_ID);
                  setErrorMessage(null);
                }}
                className="px-2.5 py-1 rounded bg-neutral-200 dark:bg-neutral-800 hover:bg-neutral-300 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300 transition-colors cursor-pointer"
                title="Loads valid owner User A and Roadmap A"
              >
                Valid IDs (200 OK)
              </button>
              <button
                type="button"
                onClick={() => {
                  setUserId(DEFAULT_UNAUTHORIZED_USER_ID);
                  setRoadmapId(DEFAULT_VALID_ROADMAP_ID);
                  setErrorMessage(null);
                }}
                className="px-2.5 py-1 rounded bg-rose-100 dark:bg-rose-950/50 hover:bg-rose-200 dark:hover:bg-rose-900/50 text-rose-800 dark:text-rose-300 transition-colors cursor-pointer"
                title="Loads User B to test cross-user 403 Forbidden"
              >
                Cross-User (403 Test)
              </button>
              <button
                type="button"
                onClick={() => {
                  setUserId(DEFAULT_VALID_USER_ID);
                  setRoadmapId("not-a-valid-uuid");
                  setErrorMessage(null);
                }}
                className="px-2.5 py-1 rounded bg-amber-100 dark:bg-amber-950/50 hover:bg-amber-200 dark:hover:bg-amber-900/50 text-amber-800 dark:text-amber-300 transition-colors cursor-pointer"
                title="Loads invalid UUID string to test 422 Unprocessable"
              >
                Invalid UUID (422 Test)
              </button>
            </div>
          </div>
        </div>

        {/* 2-Column Grid: Form & Controls (Left) / PDF Preview (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Form Controls & Status Card */}
          <div className="lg:col-span-5 space-y-6">
            {/* Input Parameters Card */}
            <div className="bg-white/80 dark:bg-[#121216]/90 border border-neutral-200 dark:border-neutral-800 rounded-xl p-6 shadow-sm backdrop-blur-xs space-y-5">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
                  <FileText className="h-4 w-4 text-emerald-500" />
                  <span>Request Parameters</span>
                </h2>
                <span className="text-xs font-mono text-neutral-400">GET /api/v1/roadmaps/:id/pdf</span>
              </div>

              {/* Roadmap ID Field */}
              <div className="space-y-1.5">
                <label
                  htmlFor={roadmapInputId}
                  className="block text-xs font-semibold uppercase tracking-wider text-neutral-700 dark:text-neutral-300"
                >
                  Roadmap ID <span className="text-rose-500">*</span>
                </label>
                <input
                  id={roadmapInputId}
                  type="text"
                  value={roadmapId}
                  onChange={(e) => setRoadmapId(e.target.value)}
                  placeholder="Paste CandidateRoadmap UUID..."
                  className={`w-full px-3.5 py-2 rounded-lg text-sm font-mono bg-white dark:bg-[#141418] border ${
                    roadmapId && !isValidUUID(roadmapId)
                      ? "border-amber-400 dark:border-amber-600 focus:ring-amber-500"
                      : "border-neutral-300 dark:border-neutral-700 focus:ring-emerald-500"
                  } text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 focus:outline-none focus:ring-2 transition-all`}
                />
                {roadmapId && !isValidUUID(roadmapId) && (
                  <p className="text-[11px] text-amber-600 dark:text-amber-400">
                    Note: String is not a standard UUID format.
                  </p>
                )}
              </div>

              {/* User ID Field */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor={userInputId}
                    className="block text-xs font-semibold uppercase tracking-wider text-neutral-700 dark:text-neutral-300"
                  >
                    User ID <span className="text-rose-500">*</span>
                  </label>
                  <span className="text-[11px] text-neutral-500 dark:text-neutral-400">Sent via X-User-Id header</span>
                </div>
                <input
                  id={userInputId}
                  type="text"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  placeholder="Paste Authenticated User UUID..."
                  className={`w-full px-3.5 py-2 rounded-lg text-sm font-mono bg-white dark:bg-[#141418] border ${
                    userId && !isValidUUID(userId)
                      ? "border-amber-400 dark:border-amber-600 focus:ring-amber-500"
                      : "border-neutral-300 dark:border-neutral-700 focus:ring-emerald-500"
                  } text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 focus:outline-none focus:ring-2 transition-all`}
                />
              </div>

              {/* Action Buttons */}
              <div className="pt-2 flex flex-col sm:flex-row gap-3">
                <button
                  type="button"
                  onClick={handleGenerateAndPreview}
                  disabled={isWorking}
                  className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  {status === "Generating" ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Generating...</span>
                    </>
                  ) : (
                    <>
                      <Zap className="h-4 w-4" />
                      <span>Generate &amp; Preview PDF</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={handleDownload}
                  disabled={isWorking}
                  className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-900 dark:hover:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 text-neutral-800 dark:text-neutral-200 font-semibold text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                  title="Directly trigger browser PDF download"
                >
                  {isDownloading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="h-4 w-4" />
                  )}
                  <span>Download PDF</span>
                </button>
              </div>

              {/* In-progress banner */}
              {status === "Generating" && (
                <div className="p-3.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 text-emerald-900 dark:text-emerald-200 text-xs flex items-start gap-2.5 animate-pulse">
                  <Loader2 className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400 animate-spin mt-0.5" />
                  <div>
                    <p className="font-semibold">Generating your roadmap...</p>
                    <p className="text-[11px] text-emerald-700 dark:text-emerald-300/80 mt-0.5">
                      SkillForge is building and validating your personalized PDF.
                    </p>
                  </div>
                </div>
              )}

              {/* Error Alert Box */}
              {errorMessage && (
                <div className="p-3.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 text-rose-900 dark:text-rose-200 text-xs flex items-start gap-2.5">
                  <AlertCircle className="h-4 w-4 shrink-0 text-rose-600 dark:text-rose-400 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-semibold">Generation Failed</p>
                    <p className="text-[11px] text-rose-800 dark:text-rose-300 mt-0.5">{errorMessage}</p>
                  </div>
                </div>
              )}

              {/* Success Alert Box */}
              {successMessage && (
                <div className="p-3.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 text-emerald-900 dark:text-emerald-200 text-xs flex items-center justify-between gap-2.5">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    <span className="font-semibold">{successMessage}</span>
                  </div>
                  {previewUrl && (
                    <a
                      href={previewUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 font-medium text-emerald-700 dark:text-emerald-300 hover:underline cursor-pointer"
                    >
                      <span>Open in New Tab</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
              )}
            </div>

            {/* Generation Status / Debug Card */}
            <div className="bg-white/70 dark:bg-[#121216]/70 border border-neutral-200 dark:border-neutral-800/80 rounded-xl p-5 shadow-xs text-xs space-y-3">
              <div className="flex items-center justify-between border-b border-neutral-200 dark:border-neutral-800/60 pb-2.5">
                <span className="font-semibold text-neutral-800 dark:text-neutral-200 flex items-center gap-1.5">
                  <Info className="h-3.5 w-3.5 text-neutral-500" />
                  <span>Generation Status</span>
                </span>
                <span
                  className={`px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider text-[10px] ${
                    status === "Ready"
                      ? "bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400"
                      : status === "Generating"
                      ? "bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 animate-pulse"
                      : status === "Success"
                      ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300"
                      : "bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300"
                  }`}
                >
                  {status}
                </span>
              </div>

              {metadata ? (
                <div className="grid grid-cols-2 gap-2.5 text-neutral-600 dark:text-neutral-400 font-mono text-[11px]">
                  <div>
                    <span className="text-neutral-400 dark:text-neutral-500 block text-[10px] uppercase font-sans">
                      HTTP Status
                    </span>
                    <span className="font-semibold text-neutral-800 dark:text-neutral-200">
                      {metadata.httpStatus || "N/A"}
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-400 dark:text-neutral-500 block text-[10px] uppercase font-sans">
                      Latency
                    </span>
                    <span className="font-semibold text-neutral-800 dark:text-neutral-200">
                      {metadata.durationMs} ms
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-400 dark:text-neutral-500 block text-[10px] uppercase font-sans">
                      Content-Type
                    </span>
                    <span className="truncate block font-semibold text-neutral-800 dark:text-neutral-200">
                      {metadata.contentType}
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-400 dark:text-neutral-500 block text-[10px] uppercase font-sans">
                      File Size
                    </span>
                    <span className="font-semibold text-neutral-800 dark:text-neutral-200">
                      {metadata.fileSizeBytes > 0 ? formatBytes(metadata.fileSizeBytes) : "0 B"}
                    </span>
                  </div>
                  {metadata.filename && (
                    <div className="col-span-2 pt-1 border-t border-neutral-100 dark:border-neutral-800/40">
                      <span className="text-neutral-400 dark:text-neutral-500 block text-[10px] uppercase font-sans">
                        Filename
                      </span>
                      <span className="truncate block font-semibold text-neutral-800 dark:text-neutral-200">
                        {metadata.filename}
                      </span>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-[11px] text-neutral-500 dark:text-neutral-400">
                  Ready to invoke backend PDF generator. Click &quot;Generate &amp; Preview PDF&quot; to test.
                </p>
              )}
            </div>
          </div>

          {/* Right Column: PDF Preview Area */}
          <div className="lg:col-span-7">
            <div className="bg-white/80 dark:bg-[#121216]/90 border border-neutral-200 dark:border-neutral-800 rounded-xl overflow-hidden shadow-sm flex flex-col h-[780px]">
              {/* Preview Header / Toolbar */}
              <div className="px-4 py-3 bg-neutral-100/70 dark:bg-neutral-900/70 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <FileCheck className="h-4 w-4 text-emerald-500" />
                  <span className="font-semibold text-neutral-800 dark:text-neutral-200">ReportLab PDF Preview</span>
                  {metadata?.fileSizeBytes ? (
                    <span className="text-neutral-400 dark:text-neutral-500">
                      ({formatBytes(metadata.fileSizeBytes)})
                    </span>
                  ) : null}
                </div>

                {previewUrl && (
                  <div className="flex items-center gap-2">
                    <a
                      href={previewUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-neutral-200 dark:bg-neutral-800 hover:bg-neutral-300 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300 font-medium text-xs transition-colors cursor-pointer"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      <span>Open in New Tab</span>
                    </a>
                    <button
                      type="button"
                      onClick={handleDownload}
                      disabled={isDownloading}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs transition-colors cursor-pointer"
                    >
                      <Download className="h-3.5 w-3.5" />
                      <span>Download</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Preview Content Body */}
              <div className="flex-1 bg-neutral-100 dark:bg-[#0c0c0e] relative flex items-center justify-center p-2">
                {previewUrl ? (
                  <iframe
                    src={previewUrl}
                    className="w-full h-full rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white"
                    title="Personalized Career Roadmap PDF"
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center text-center p-8 max-w-md space-y-3">
                    <div className="w-16 h-16 rounded-2xl bg-neutral-200/70 dark:bg-neutral-800/50 flex items-center justify-center text-neutral-400 dark:text-neutral-500">
                      <FileText className="h-8 w-8" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">
                        Your generated roadmap will appear here.
                      </h3>
                      <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                        Enter valid Roadmap and User UUIDs above and click &quot;Generate &amp; Preview PDF&quot;.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default function RoadmapPdfTestPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-50 dark:bg-[#0a0a0c] flex items-center justify-center">
          <Loader2 className="h-8 w-8 text-emerald-500 animate-spin" />
        </div>
      }
    >
      <RoadmapPdfTestContent />
    </Suspense>
  );
}
