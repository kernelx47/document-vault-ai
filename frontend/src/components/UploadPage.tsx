"use client";

import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";
import clsx from "clsx";
import { uploadBatch, type BatchUploadResponse } from "@/lib/api";
import AppSidebar from "@/components/AppSidebar";

type StagedFile = { file: File; id: string };

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function fileIcon(name: string) {
  return name.toLowerCase().endsWith(".docx") ? "DOCX" : "PDF";
}

export default function UploadPage() {
  const router = useRouter();
  const [files, setFiles] = useState<StagedFile[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((list: FileList | File[]) => {
    const accepted = Array.from(list).filter((f) => {
      const ext = f.name.toLowerCase();
      return ext.endsWith(".pdf") || ext.endsWith(".docx");
    });
    if (accepted.length === 0) return;
    setFiles((prev) => [
      ...prev,
      ...accepted.map((file) => ({ file, id: crypto.randomUUID() })),
    ]);
    setError(null);
  }, []);

  function removeFile(id: string) {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(true);
  }
  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setDragOver(false);
  }
  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
  }

  async function handleSubmit() {
    if (files.length === 0 || uploading) return;
    setUploading(true);
    setError(null);
    try {
      const result: BatchUploadResponse = await uploadBatch(files.map((f) => f.file));
      if (result.batch_id) {
        router.push(`/activity?highlight=${result.batch_id}`);
      } else {
        router.push("/activity");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed. Please try again.");
      setUploading(false);
    }
  }

  const totalSize = files.reduce((sum, f) => sum + f.file.size, 0);

  return (
    <AppSidebar>
      <main className="flex flex-1 flex-col items-center justify-center overflow-y-auto px-4 pb-16">
        <div className="w-full max-w-[680px]">
          {/* Title */}
          <div className="mb-8 text-center">
            <h1
              className="mb-2 text-[32px] font-medium tracking-[-0.03em] text-[var(--deep-ink)]"
              style={{ fontFamily: "'Source Serif 4', serif" }}
            >
              Upload{" "}
              <span className="bg-gradient-to-r from-[var(--electric-violet)] to-purple-500 bg-clip-text text-transparent">
                Documents
              </span>
            </h1>
            <p className="text-[15px] text-[var(--overcast)]">
              Drop your files below and we&apos;ll process them into your vault
            </p>
          </div>

          {/* Drop zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={clsx(
              "group relative cursor-pointer overflow-hidden rounded-[var(--radius-lg)] border-2 border-dashed transition-all duration-300",
              dragOver
                ? "border-[var(--electric-violet)] bg-[var(--electric-violet)]/5 shadow-lg shadow-[var(--electric-violet)]/10"
                : "border-[var(--lavender-mist)] bg-[var(--pure-paper)] hover:border-[var(--electric-violet)]/40 hover:shadow-md hover:shadow-[var(--deep-ink)]/5",
              files.length > 0 ? "px-6 py-6" : "px-6 py-16",
            )}
          >
            {files.length === 0 ? (
              <div className="flex flex-col items-center">
                <div
                  className={clsx(
                    "mb-4 flex h-16 w-16 items-center justify-center rounded-2xl transition-all duration-300",
                    dragOver
                      ? "bg-[var(--electric-violet)]/10 text-[var(--electric-violet)]"
                      : "bg-[var(--iris-haze)] text-[var(--mist)] group-hover:bg-[var(--electric-violet)]/5 group-hover:text-[var(--electric-violet)]",
                  )}
                >
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                </div>
                <p className="mb-1 text-[15px] font-medium text-[var(--deep-ink)]">
                  Drag &amp; drop files here
                </p>
                <p className="mb-4 text-sm text-[var(--overcast)]">
                  or{" "}
                  <span className="font-medium text-[var(--electric-violet)] underline decoration-[var(--electric-violet)]/30 underline-offset-2">
                    click to browse
                  </span>
                </p>
                <div className="flex items-center gap-3">
                  <span className="rounded-full bg-red-50 px-3 py-1 text-xs font-medium text-red-600">PDF</span>
                  <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-600">DOCX</span>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-3" onClick={(e) => e.stopPropagation()}>
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--electric-violet)]/10">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--electric-violet)" strokeWidth="1.5" strokeLinecap="round">
                    <path d="M12 5v14M5 12h14" />
                  </svg>
                </div>
                <button
                  onClick={() => inputRef.current?.click()}
                  className="text-sm font-medium text-[var(--electric-violet)] underline decoration-[var(--electric-violet)]/30 underline-offset-2 hover:decoration-[var(--electric-violet)]"
                >
                  Add more files
                </button>
              </div>
            )}

            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx"
              multiple
              className="hidden"
              onChange={(e) => {
                if (e.target.files?.length) addFiles(e.target.files);
                e.target.value = "";
              }}
            />
          </div>

          {/* File list */}
          {files.length > 0 && (
            <div className="mt-4">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-sm font-medium text-[var(--deep-ink)]">
                  {files.length} file{files.length !== 1 ? "s" : ""}{" "}
                  <span className="font-normal text-[var(--overcast)]">({formatSize(totalSize)})</span>
                </p>
                <button onClick={() => setFiles([])} className="text-xs font-medium text-[var(--danger)] hover:underline">
                  Clear all
                </button>
              </div>

              <div className="max-h-[280px] space-y-2 overflow-y-auto pr-1">
                {files.map((sf) => (
                  <div
                    key={sf.id}
                    className="group/item flex items-center gap-3 rounded-[var(--radius)] border border-[var(--lavender-mist)] bg-[var(--pure-paper)] px-4 py-3 transition-all hover:border-[var(--electric-violet)]/20 hover:shadow-sm"
                  >
                    <div
                      className={clsx(
                        "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[10px] font-bold tracking-wide",
                        sf.file.name.toLowerCase().endsWith(".docx") ? "bg-blue-50 text-blue-600" : "bg-red-50 text-red-600",
                      )}
                    >
                      {fileIcon(sf.file.name)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-[var(--deep-ink)]">{sf.file.name}</p>
                      <p className="text-xs text-[var(--overcast)]">{formatSize(sf.file.size)}</p>
                    </div>
                    <button
                      onClick={() => removeFile(sf.id)}
                      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[var(--mist)] opacity-0 transition-all hover:bg-[var(--danger-bg)] hover:text-[var(--danger)] group-hover/item:opacity-100"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                        <path d="M18 6L6 18M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="mt-4 flex items-center gap-3 rounded-[var(--radius)] border border-[var(--danger)]/20 bg-[var(--danger-bg)] px-4 py-3">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" strokeWidth="2" strokeLinecap="round">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 8v4M12 16h.01" />
              </svg>
              <p className="text-sm text-[var(--danger)]">{error}</p>
            </div>
          )}

          {/* Submit */}
          {files.length > 0 && (
            <div className="mt-6 flex justify-center">
              <button
                onClick={() => void handleSubmit()}
                disabled={uploading}
                className={clsx(
                  "flex items-center gap-2.5 rounded-full px-8 py-3 text-[15px] font-semibold shadow-lg transition-all",
                  uploading
                    ? "cursor-wait bg-[var(--electric-violet)]/70 text-white/80 shadow-[var(--electric-violet)]/20"
                    : "bg-[var(--electric-violet)] text-white shadow-[var(--electric-violet)]/25 hover:shadow-xl hover:shadow-[var(--electric-violet)]/30 active:scale-[0.98]",
                )}
              >
                {uploading ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                      <path d="M21 12a9 9 0 11-6.219-8.56" />
                    </svg>
                    Uploading {files.length} file{files.length !== 1 ? "s" : ""}…
                  </>
                ) : (
                  <>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                      <polyline points="17 8 12 3 7 8" />
                      <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                    Upload &amp; Process {files.length} file{files.length !== 1 ? "s" : ""}
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </main>
    </AppSidebar>
  );
}
