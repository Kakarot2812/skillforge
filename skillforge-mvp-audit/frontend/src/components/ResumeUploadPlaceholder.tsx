"use client";

import React, { useState, useRef } from "react";
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
import { uploadResume, deleteResume, fetchResumes, ResumeUploadResult, ResumeListItem } from "@/lib/api";

const MAX_SIZE_MB = 5;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".pdf", ".docx"];

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export interface ResumeUploadPlaceholderProps {
  onResumeChange?: (hasResume: boolean, filename?: string) => void;
}

export default function ResumeUploadPlaceholder({
  onResumeChange,
}: ResumeUploadPlaceholderProps = {}) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<ResumeUploadResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sync initial state from localStorage on client mount, verifying backend validity
  React.useEffect(() => {
    async function verifyResumeState() {
      if (typeof window === "undefined") return;
      const activeId = localStorage.getItem("skillforge_active_resume_id");
      const activeName = localStorage.getItem("skillforge_active_resume_filename");
      if (!activeId) {
        onResumeChange?.(false);
        return;
      }
      try {
        const res = await fetchResumes(20, 0);
        if (res.success && res.data?.data) {
          const matching = res.data.data.find((r: ResumeListItem) => r.resume_id === activeId);
          if (matching) {
            onResumeChange?.(true, matching.filename || activeName || "Resume");
            setUploadResult({
              resume_id: matching.resume_id,
              filename: matching.filename,
              file_type: matching.file_type,
              file_size: matching.file_size,
              status: matching.status,
              message: "Resume verified",
              created_at: matching.created_at || new Date().toISOString(),
              extracted_sections: matching.detected_sections,
              claimed_skills: [],
            });
            return;
          }
        }
        // If not found on backend (deleted or wiped), purge stale state
        localStorage.removeItem("skillforge_active_resume_id");
        localStorage.removeItem("skillforge_active_resume_filename");
        onResumeChange?.(false);
      } catch {
        if (activeName) {
          onResumeChange?.(true, activeName);
        }
      }
    }
    verifyResumeState();
  }, [onResumeChange]);

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
      if (typeof window !== "undefined") {
        localStorage.setItem("skillforge_active_resume_id", result.data.resume_id);
        localStorage.setItem("skillforge_active_resume_filename", result.data.filename);
      }
      onResumeChange?.(true, result.data.filename);
    } else {
      setErrorMessage(result.error || "Upload failed. Please try again.");
    }
  };

  const resetForm = () => {
    setSelectedFile(null);
    setUploadResult(null);
    setErrorMessage(null);
    if (typeof window !== "undefined") {
      localStorage.removeItem("skillforge_active_resume_id");
      localStorage.removeItem("skillforge_active_resume_filename");
    }
    onResumeChange?.(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div id="resume-intelligence-card" className="bg-neutral-900/60 border border-neutral-800 rounded-2xl p-6 backdrop-blur-md relative flex flex-col justify-between shadow-lg">
      {/* Card Header */}
      <div>
        <div className="flex items-center justify-between pb-4 border-b border-neutral-800">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <FileText className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-neutral-200">
                Resume Intelligence
              </h3>
              <p className="text-xs text-neutral-500">
                Phase 2 • Resume Intelligence
              </p>
            </div>
          </div>
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 uppercase tracking-wider font-mono">
            Phase 2 Complete
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
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-neutral-200 space-y-3">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold text-xs">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>Resume Uploaded & Intelligence Verified</span>
              </div>

              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-neutral-400">File Name:</span>
                  <span className="font-mono text-neutral-200 font-medium truncate max-w-[200px]">
                    {uploadResult.filename}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-400">Format / Size:</span>
                  <span className="font-mono text-neutral-300">
                    {uploadResult.file_type.toUpperCase()} • {formatFileSize(uploadResult.file_size)}
                  </span>
                </div>
                <div className="flex justify-between items-center pt-1 border-t border-emerald-500/20">
                  <span className="text-neutral-400">Resume ID:</span>
                  <span className="font-mono text-[11px] text-emerald-300 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/50">
                    {uploadResult.resume_id}
                  </span>
                </div>

                {uploadResult.extracted_sections && uploadResult.extracted_sections.length > 0 && (
                  <div className="pt-2 border-t border-emerald-500/20">
                    <span className="text-[11px] text-neutral-400 block mb-1 font-medium">
                      Detected Sections:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {uploadResult.extracted_sections.map((sec) => (
                        <span
                          key={sec}
                          className="px-2 py-0.5 rounded-md bg-neutral-900 border border-neutral-700 text-neutral-300 text-[10px] font-mono capitalize"
                        >
                          {sec}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {uploadResult.claimed_skills && uploadResult.claimed_skills.length > 0 && (
                  <div className="pt-2 border-t border-emerald-500/20">
                    <div className="flex justify-between items-center mb-1.5">
                      <span className="text-[11px] text-neutral-300 font-medium">
                        Canonical Claimed Skills:
                      </span>
                      <span className="text-[10px] font-mono text-emerald-400">
                        {uploadResult.claimed_skills.length} normalized
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto pr-1">
                      {uploadResult.claimed_skills.map((skill) => (
                        <span
                          key={skill.skill_id}
                          className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-emerald-950/70 border border-emerald-600/50 text-emerald-200 text-[10px] font-medium"
                        >
                          <span>{skill.skill_name}</span>
                          <span className="text-[9px] font-mono text-emerald-400/80 bg-emerald-900/60 px-1 rounded">
                            {Math.round(skill.confidence_score * 100)}%
                          </span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Checkpoint 4 Notice */}
            <div className="p-3 rounded-xl bg-neutral-950/60 border border-neutral-800 text-[11px] text-neutral-400 space-y-1">
              <div className="flex items-center gap-1.5 font-medium text-emerald-400">
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>Phase 2 Resume Intelligence Complete</span>
              </div>
              <p className="leading-relaxed">
                Ingestion, section parsing, canonical normalization, and lifecycle management verified. 
                <strong className="text-purple-300 font-normal"> Integrated with SkillForge Career Intelligence Pipeline.</strong>
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={resetForm}
                className="py-2 px-3 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs font-medium transition-all flex items-center justify-center gap-1.5 border border-neutral-700 cursor-pointer"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Upload Another</span>
              </button>
              <button
                onClick={async () => {
                  if (uploadResult?.resume_id) {
                    await deleteResume(uploadResult.resume_id);
                    resetForm();
                  }
                }}
                className="py-2 px-3 rounded-xl bg-red-950/40 hover:bg-red-900/50 text-red-300 hover:text-red-200 text-xs font-medium transition-all flex items-center justify-center gap-1.5 border border-red-800/40 cursor-pointer"
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
                  ? "border-purple-500/50 bg-neutral-950/60"
                  : "border-neutral-800 hover:border-neutral-700 bg-neutral-950/40"
              }`}
            >
              <div className="p-3 rounded-full bg-neutral-900 text-neutral-400 mb-3 border border-neutral-800">
                {selectedFile ? (
                  <FileCheck2 className="h-6 w-6 text-purple-400" />
                ) : (
                  <UploadCloud className="h-6 w-6 text-neutral-500" />
                )}
              </div>

              {selectedFile ? (
                <div className="space-y-1">
                  <p className="text-xs font-semibold text-neutral-200 truncate max-w-xs">
                    {selectedFile.name}
                  </p>
                  <p className="text-[11px] font-mono text-purple-400">
                    {formatFileSize(selectedFile.size)} • Ready to upload
                  </p>
                  <span className="text-[10px] text-neutral-500 block pt-1">
                    Click to choose a different file
                  </span>
                </div>
              ) : (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-neutral-300">
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
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2">
                <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
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
                  className="flex-1 py-2 px-4 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-purple-950/40 transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
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
                  className="py-2 px-3 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs border border-neutral-700 transition-all cursor-pointer disabled:opacity-50"
                  title="Clear selected file"
                >
                  Clear
                </button>
              </div>
            )}

            {!selectedFile && (
              <div className="px-3 py-2 rounded-lg bg-neutral-950/50 border border-neutral-800/80 text-[11px] text-neutral-500 flex items-center justify-between">
                <span>Validation: MIME + Magic Bytes</span>
                <span className="font-mono text-[10px]">Strict 5 MB limit</span>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-neutral-800/50 flex items-center justify-between text-[11px] text-neutral-500">
        <span>GET /api/v1/resumes • DELETE /api/v1/resumes/{'{id}'}</span>
        <span className="text-emerald-400 font-medium font-mono">Phase 2 Complete</span>
      </div>
    </div>
  );
}
