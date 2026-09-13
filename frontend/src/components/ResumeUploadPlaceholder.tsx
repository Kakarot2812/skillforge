"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  FileText,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FileCheck2,
  RotateCcw,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import {
  uploadResume,
  deleteResume,
  fetchResumeDetail,
  activateResume,
  ResumeUploadResult,
} from "@/lib/api";
import { useCandidate } from "@/context/CandidateContext";

const MAX_SIZE_MB = 5;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".pdf", ".docx"];

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export interface ResumeUploadPlaceholderProps {
  onResumeChange?: (hasResume: boolean, filename?: string, resumeId?: string) => void;
}

export default function ResumeUploadPlaceholder({ onResumeChange }: ResumeUploadPlaceholderProps) {
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<ResumeUploadResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { resumeId: contextResumeId, handleResumeChange } = useCandidate();

  const onResumeChangeRef = useRef(onResumeChange);
  useEffect(() => {
    onResumeChangeRef.current = onResumeChange;
  }, [onResumeChange]);

  // Listen for stale resume invalidation events across the dashboard
  useEffect(() => {
    const handleStaleResume = () => {
      setUploadResult(null);
      setSelectedFile(null);
      setErrorMessage(null);
      onResumeChangeRef.current?.(false);
    };
    window.addEventListener("skillforge:resume-stale", handleStaleResume);
    return () => {
      window.removeEventListener("skillforge:resume-stale", handleStaleResume);
    };
  }, []);

  // Sync state with server-provided active resume from CandidateContext
  useEffect(() => {
    let isCancelled = false;
    async function syncResume() {
      if (!contextResumeId) {
        setUploadResult(null);
        onResumeChangeRef.current?.(false);
        return;
      }

      try {
        const res = await fetchResumeDetail(contextResumeId);
        if (isCancelled) return;

        if (!res.success || !res.data || res.status === 403 || res.status === 404) {
          setUploadResult(null);
          onResumeChangeRef.current?.(false);
          return;
        }

        onResumeChangeRef.current?.(true, res.data.filename, res.data.resume_id);
        setUploadResult({
          resume_id: res.data.resume_id,
          user_id: res.data.user_id,
          filename: res.data.filename,
          file_type: res.data.file_type,
          file_size: res.data.file_size,
          status: "uploaded",
          message: "Resume verified",
          created_at: res.data.created_at || new Date().toISOString(),
          extracted_sections: res.data.detected_sections,
          claimed_skills: res.data.claimed_skills || [],
        });
      } catch {
        if (!isCancelled) {
          setUploadResult(null);
          onResumeChangeRef.current?.(false);
        }
      }
    }
    syncResume();
    return () => {
      isCancelled = true;
    };
  }, [contextResumeId]);

  const handleFileSelection = (file: File) => {
    setErrorMessage(null);
    setUploadResult(null);

    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setErrorMessage(
        `Unsupported file extension '${ext}'. Only PDF and DOCX documents are accepted.`
      );
      setSelectedFile(null);
      return;
    }

    if (file.size > MAX_SIZE_BYTES) {
      setErrorMessage(
        `File exceeds maximum limit of ${MAX_SIZE_MB} MB (Current: ${formatFileSize(file.size)}).`
      );
      setSelectedFile(null);
      return;
    }

    if (file.size === 0) {
      setErrorMessage("The selected file is empty (0 bytes).");
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelection(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setErrorMessage(null);

    const result = await uploadResume(selectedFile);
    setIsUploading(false);

    if (result.success && result.data) {
      setUploadResult(result.data);
      setSelectedFile(null);
      await activateResume(result.data.resume_id);
      onResumeChange?.(true, result.data.filename, result.data.resume_id);
      handleResumeChange(true, result.data.filename, result.data.resume_id);
    } else {
      setErrorMessage(result.error || "Upload failed. Please try again.");
    }
  };

  const resetForm = () => {
    setSelectedFile(null);
    setUploadResult(null);
    setErrorMessage(null);
    onResumeChange?.(false);
    handleResumeChange(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div id="resume-intelligence-card" className="bg-white dark:bg-neutral-900/60 border border-neutral-200 dark:border-neutral-800 rounded-2xl p-6 backdrop-blur-md relative flex flex-col justify-between shadow-xs transition-colors duration-200">
      {/* Card Header */}
      <div>
        <div className="flex items-center justify-between pb-4 border-b border-neutral-200 dark:border-neutral-800">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
              <FileText className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-200">
                Resume Intelligence
              </h3>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                Resume Evidence & Skill Extraction
              </p>
            </div>
          </div>
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-700 dark:text-purple-400 border border-purple-500/30 uppercase tracking-wider font-mono">
            {uploadResult ? "Profile Active" : "Resume Evidence"}
          </span>
        </div>

        {/* Hidden File Input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={handleInputChange}
          className="hidden"
          id="resume-file-input"
        />

        {/* Success View */}
        {uploadResult ? (
          <div className="mt-5 space-y-4">
            <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 text-neutral-800 dark:text-neutral-200 space-y-3">
              <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 font-semibold text-xs">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>Resume Uploaded & Intelligence Verified</span>
              </div>

              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-neutral-500 dark:text-neutral-400">File Name:</span>
                  <span className="font-mono text-neutral-800 dark:text-neutral-200 font-medium truncate max-w-[200px]">
                    {uploadResult.filename}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-500 dark:text-neutral-400">Format / Size:</span>
                  <span className="font-mono text-neutral-700 dark:text-neutral-300">
                    {uploadResult.file_type.toUpperCase()} • {formatFileSize(uploadResult.file_size)}
                  </span>
                </div>
                <div className="flex justify-between items-center pt-1 border-t border-emerald-200 dark:border-emerald-500/20">
                  <span className="text-neutral-500 dark:text-neutral-400">Resume ID:</span>
                  <span className="font-mono text-[11px] text-emerald-700 dark:text-emerald-300 bg-emerald-100 dark:bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-300 dark:border-emerald-800/50">
                    {uploadResult.resume_id}
                  </span>
                </div>

                {uploadResult.extracted_sections && uploadResult.extracted_sections.length > 0 && (
                  <div className="pt-2 border-t border-emerald-200 dark:border-emerald-500/20">
                    <span className="text-[11px] text-neutral-600 dark:text-neutral-400 block mb-1 font-medium">
                      Detected Sections:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {uploadResult.extracted_sections.map((sec) => (
                        <span
                          key={sec}
                          className="px-2 py-0.5 rounded-md bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 text-[10px] font-mono capitalize"
                        >
                          {sec}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {uploadResult.claimed_skills && uploadResult.claimed_skills.length > 0 && (
                  <div className="pt-2 border-t border-emerald-200 dark:border-emerald-500/20">
                    <div className="flex justify-between items-center mb-1.5">
                      <span className="text-[11px] text-neutral-700 dark:text-neutral-300 font-medium">
                        Extracted Claimed Skills:
                      </span>
                      <span className="text-[10px] font-mono text-emerald-700 dark:text-emerald-400 font-semibold">
                        {uploadResult.claimed_skills.length} normalized
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto pr-1">
                      {uploadResult.claimed_skills.map((skill) => (
                        <span
                          key={skill.skill_id}
                          className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-emerald-50 dark:bg-emerald-950/70 border border-emerald-200 dark:border-emerald-600/50 text-emerald-800 dark:text-emerald-200 text-[10px] font-medium"
                        >
                          <span>{skill.skill_name}</span>
                          <span className="text-[9px] font-mono text-emerald-700 dark:text-emerald-400/80 bg-emerald-100 dark:bg-emerald-900/60 px-1 rounded">
                            {Math.round(skill.confidence_score * 100)}%
                          </span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-neutral-50 dark:bg-neutral-950/60 border border-neutral-200 dark:border-neutral-800 text-[11px] text-neutral-600 dark:text-neutral-400 space-y-1">
              <div className="flex items-center gap-1.5 font-medium text-emerald-700 dark:text-emerald-400">
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>Resume Intelligence Verified</span>
              </div>
              <p className="leading-relaxed">
                Resume sections and skills extracted and verified.
                <strong className="text-purple-700 dark:text-purple-300 font-medium"> Integrated with SkillForge Career Intelligence.</strong>
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={resetForm}
                className="py-2 px-3 rounded-xl bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-200 text-xs font-medium transition-all flex items-center justify-center gap-1.5 border border-neutral-200 dark:border-neutral-700 cursor-pointer"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Upload Another</span>
              </button>
              <button
                type="button"
                onClick={async () => {
                  if (uploadResult?.resume_id) {
                    await deleteResume(uploadResult.resume_id);
                    resetForm();
                  }
                }}
                className="py-2 px-3 rounded-xl bg-rose-50 hover:bg-rose-100 dark:bg-red-950/40 dark:hover:bg-red-900/50 text-rose-700 dark:text-red-300 hover:text-rose-800 dark:hover:text-red-200 text-xs font-medium transition-all flex items-center justify-center gap-1.5 border border-rose-200 dark:border-red-800/40 cursor-pointer"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>Delete Resume</span>
              </button>
            </div>
          </div>
        ) : (
          /* Upload State */
          <div className="mt-5 space-y-3">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 text-center transition-all cursor-pointer flex flex-col items-center justify-center ${
                dragOver
                  ? "border-purple-500 bg-purple-500/10 scale-[0.99]"
                  : selectedFile
                  ? "border-purple-500/50 bg-purple-50/50 dark:bg-neutral-950/60"
                  : "border-neutral-300 dark:border-neutral-800 hover:border-neutral-400 dark:hover:border-neutral-700 bg-neutral-50/70 dark:bg-neutral-950/40"
              }`}
            >
              <div className="p-3 rounded-full bg-white dark:bg-neutral-900 text-neutral-500 dark:text-neutral-400 mb-3 border border-neutral-200 dark:border-neutral-800 shadow-xs">
                {selectedFile ? (
                  <FileCheck2 className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                ) : (
                  <UploadCloud className="h-6 w-6 text-neutral-400 dark:text-neutral-500" />
                )}
              </div>

              {selectedFile ? (
                <div className="space-y-1">
                  <p className="text-xs font-semibold text-neutral-900 dark:text-neutral-200 truncate max-w-xs">
                    {selectedFile.name}
                  </p>
                  <p className="text-[11px] font-mono text-purple-600 dark:text-purple-400">
                    {formatFileSize(selectedFile.size)} • Ready to upload
                  </p>
                  <span className="text-[10px] text-neutral-500 block pt-1">
                    Click to choose a different file
                  </span>
                </div>
              ) : (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-neutral-700 dark:text-neutral-300">
                    Click to select resume or drag & drop here
                  </p>
                  <p className="text-[11px] text-neutral-500">
                    PDF or DOCX documents only (Max {MAX_SIZE_MB} MB)
                  </p>
                </div>
              )}
            </div>

            {/* Error Message */}
            {errorMessage && (
              <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs flex items-start gap-2">
                <AlertCircle className="h-4 w-4 shrink-0 text-rose-600 dark:text-rose-400 mt-0.5" />
                <span className="leading-snug">{errorMessage}</span>
              </div>
            )}

            {/* Action Buttons */}
            {selectedFile && (
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={isUploading}
                  onClick={handleUpload}
                  className="flex-1 py-2 px-4 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-md shadow-purple-600/20 dark:shadow-purple-950/40 transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      <span>Validating & Uploading...</span>
                    </>
                  ) : (
                    <>
                      <UploadCloud className="h-3.5 w-3.5" />
                      <span>Upload & Validate Resume</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  disabled={isUploading}
                  onClick={resetForm}
                  className="py-2 px-3 rounded-xl bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300 text-xs border border-neutral-200 dark:border-neutral-700 transition-all cursor-pointer disabled:opacity-50"
                  title="Clear selected file"
                >
                  Clear
                </button>
              </div>
            )}

            {!selectedFile && (
              <div className="px-3 py-2 rounded-lg bg-neutral-50 dark:bg-neutral-950/50 border border-neutral-200 dark:border-neutral-800/80 text-[11px] text-neutral-500 flex items-center justify-between">
                <span>Supported Formats: PDF, DOCX</span>
                <span className="font-mono text-[10px]">Max 5 MB</span>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-neutral-200 dark:border-neutral-800/50 flex items-center justify-between text-[11px] text-neutral-500 dark:text-neutral-400">
        <span>Evidence Source: Candidate Resume</span>
        <span className="text-neutral-700 dark:text-neutral-400 font-medium">{uploadResult ? "Document Verified" : "No Resume Uploaded"}</span>
      </div>
    </div>
  );
}
