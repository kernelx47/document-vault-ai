"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import {
  uploadBatch,
  getBatch,
  type BatchUploadResponse,
  type BatchDetail,
} from "@/lib/api";

/* ─── Types ──────────────────────────────────────────────────── */

interface UploaderPanelProps {
  onClose: () => void;
  onBatchComplete?: () => void;
}

type StageFile = {
  file: File;
  id: string;
};

type Phase = "staging" | "uploading" | "done";

/* ─── Helpers ────────────────────────────────────────────────── */

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function statusOf(
  doc: { status: string } | undefined,
): "pending" | "processing" | "ready" | "failed" {
  if (!doc) return "pending";
  if (doc.status === "ready") return "ready";
  if (doc.status === "failed") return "failed";
  if (doc.status === "processing") return "processing";
  return "pending";
}

/* ─── Icons ──────────────────────────────────────────────────── */

function IconX({ className }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  );
}

function IconCloudUpload({ className }: { className?: string }) {
  return (
    <svg className={className} width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 16V8m0 0l-3 3m3-3l3 3" />
      <path d="M20 16.7428C21.2215 15.734 22 14.2195 22 12.5C22 9.46243 19.5376 7 16.5 7C16.2815 7 16.0771 6.886 15.9661 6.69774C14.6621 4.48484 12.2544 3 9.5 3C5.35786 3 2 6.35786 2 10.5C2 12.5661 2.83545 14.4371 4.18695 15.7935" />
    </svg>
  );
}

function IconFile({ className }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

/* ─── Component ──────────────────────────────────────────────── */

export default function UploaderPanel({ onClose, onBatchComplete }: UploaderPanelProps) {
  const [phase, setPhase] = useState<Phase>("staging");
  const [stagedFiles, setStagedFiles] = useState<StageFile[]>([]);
  const [dragOver, setDragOver] = useState(false);

  const [uploadError, setUploadError] = useState<string | null>(null);
  const [batchResult, setBatchResult] = useState<BatchUploadResponse | null>(null);
  const [batchDetail, setBatchDetail] = useState<BatchDetail | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearPoll = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => clearPoll, [clearPoll]);

  /* ── File management ────────────────────────────────────────── */

  function addFiles(list: FileList | File[]) {
    const incoming: StageFile[] = Array.from(list).map((file) => ({
      file,
      id: crypto.randomUUID(),
    }));
    setStagedFiles((prev) => [...prev, ...incoming]);
  }

  function removeFile(id: string) {
    setStagedFiles((prev) => prev.filter((f) => f.id !== id));
  }

  function clearAll() {
    setStagedFiles([]);
  }

  /* ── Drag & drop ────────────────────────────────────────────── */

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(true);
  }
  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    if (e.currentTarget === e.target) setDragOver(false);
  }
  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
  }

  /* ── Upload ─────────────────────────────────────────────────── */

  async function handleUploadAll() {
    if (stagedFiles.length === 0) return;
    setPhase("uploading");
    setUploadError(null);
    setBatchResult(null);
    setBatchDetail(null);

    try {
      const result = await uploadBatch(stagedFiles.map((sf) => sf.file));
      setBatchResult(result);

      if (result.batch_id) {
        const initial = await getBatch(result.batch_id);
        setBatchDetail(initial);
        startPolling(result.batch_id);
      } else {
        setPhase("done");
      }
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
      setPhase("staging");
    }
  }

  function startPolling(batchId: string) {
    clearPoll();
    pollRef.current = setInterval(async () => {
      try {
        const detail = await getBatch(batchId);
        setBatchDetail(detail);

        const terminal = detail.ready + detail.failed;
        if (terminal >= detail.total_files) {
          clearPoll();
          setPhase("done");
          onBatchComplete?.();
        }
      } catch {
        /* keep polling */
      }
    }, 3000);
  }

  function handleUploadMore() {
    clearPoll();
    setStagedFiles([]);
    setBatchResult(null);
    setBatchDetail(null);
    setUploadError(null);
    setPhase("staging");
  }

  /* ── Derived state ──────────────────────────────────────────── */

  const totalFiles = batchDetail?.total_files ?? 0;
  const readyCount = batchDetail?.ready ?? 0;
  const failedCount = batchDetail?.failed ?? 0;
  const terminalCount = readyCount + failedCount;
  const progressPct = totalFiles > 0 ? Math.round((terminalCount / totalFiles) * 100) : 0;

  const docStatusMap = new Map(
    batchDetail?.documents.map((d) => [d.filename, d]) ?? [],
  );

  /* ── Render ─────────────────────────────────────────────────── */

  return (
      <div className="flex h-full w-[420px] flex-col bg-[var(--ghost-white)] shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--lavender-mist)] px-5 py-4">
          <h2
            className="text-base font-semibold text-[var(--deep-ink)]"
            style={{ fontFamily: "'Source Serif 4', serif" }}
          >
            Doc Uploader
          </h2>
          <button
            onClick={onClose}
            className="rounded-full p-1 text-[var(--mist)] transition-colors hover:bg-[var(--iris-haze)] hover:text-[var(--heather)]"
          >
            <IconX />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-5 py-5">
          {/* Error banner */}
          {uploadError && (
            <div className="mb-4 rounded-[var(--radius)] bg-[var(--danger-bg)] px-4 py-2.5 text-sm text-[var(--danger)]">
              {uploadError}
            </div>
          )}

          {/* ── Progress bar (uploading / done) ─────────────────── */}
          {phase !== "staging" && batchDetail && (
            <div className="mb-5">
              {phase === "uploading" && (
                <p className="mb-2 text-sm font-medium text-[var(--deep-ink)]">
                  Processing {terminalCount} of {totalFiles} file{totalFiles !== 1 ? "s" : ""}…
                </p>
              )}
              {phase === "done" && (
                <p className="mb-2 text-sm font-medium text-[var(--deep-ink)]">
                  {failedCount === 0
                    ? `All ${readyCount} file${readyCount !== 1 ? "s" : ""} processed`
                    : `${readyCount} succeeded, ${failedCount} failed`}
                </p>
              )}
              <div className="h-2 overflow-hidden rounded-full bg-[var(--lavender-mist)]">
                <div
                  className={clsx(
                    "h-full rounded-full transition-all duration-500",
                    phase === "done" && failedCount === 0
                      ? "bg-[var(--success)]"
                      : phase === "done" && failedCount > 0
                        ? "bg-[var(--warning)]"
                        : "bg-[var(--electric-violet)]",
                  )}
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>
          )}

          {/* ── Drop zone (staging only) ────────────────────────── */}
          {phase === "staging" && (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={clsx(
                "cursor-pointer rounded-[var(--radius)] border-2 border-dashed p-10 text-center transition-colors",
                dragOver
                  ? "border-[var(--electric-violet)] bg-[var(--iris-haze)]"
                  : "border-[var(--lavender-mist)] hover:border-[var(--electric-violet)]/40 hover:bg-[var(--iris-haze)]",
              )}
            >
              <IconCloudUpload
                className={clsx(
                  "mx-auto mb-3",
                  dragOver ? "text-[var(--electric-violet)]" : "text-[var(--mist)]",
                )}
              />
              <p className="text-sm text-[var(--deep-ink)]">
                Drag files here or{" "}
                <span className="font-medium text-[var(--electric-violet)]">click to browse</span>
              </p>
              <p className="mt-1 text-xs text-[var(--overcast)]">PDF, DOCX</p>
              <input
                ref={fileInputRef}
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
          )}

          {/* ── File list ───────────────────────────────────────── */}
          {phase === "staging" && stagedFiles.length > 0 && (
            <div className="mt-4 space-y-1.5">
              {stagedFiles.length > 1 && (
                <div className="flex justify-end">
                  <button
                    onClick={clearAll}
                    className="text-xs font-medium text-[var(--electric-violet)] hover:underline"
                  >
                    Clear all
                  </button>
                </div>
              )}
              {stagedFiles.map((sf) => (
                <div
                  key={sf.id}
                  className="flex items-center gap-3 rounded-[var(--radius)] border border-[var(--lavender-mist)] bg-white px-3 py-2.5"
                >
                  <IconFile className="shrink-0 text-[var(--mist)]" />
                  <span className="min-w-0 flex-1 truncate text-sm text-[var(--deep-ink)]">
                    {sf.file.name}
                  </span>
                  <span className="shrink-0 text-xs text-[var(--overcast)]">
                    {formatSize(sf.file.size)}
                  </span>
                  <button
                    onClick={() => removeFile(sf.id)}
                    className="shrink-0 rounded-full p-0.5 text-[var(--mist)] transition-colors hover:text-[var(--danger)]"
                  >
                    <IconX />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* ── File rows during upload / after done ─────────────── */}
          {phase !== "staging" && batchResult && (
            <div className="space-y-1.5">
              {batchResult.accepted.map((a) => {
                const status = statusOf(docStatusMap.get(a.filename));
                return (
                  <div
                    key={a.id}
                    className="flex items-center gap-3 rounded-[var(--radius)] border border-[var(--lavender-mist)] bg-white px-3 py-2.5"
                  >
                    <IconFile className="shrink-0 text-[var(--mist)]" />
                    <span className="min-w-0 flex-1 truncate text-sm text-[var(--deep-ink)]">
                      {a.filename}
                    </span>
                    <StatusBadge status={status} />
                  </div>
                );
              })}
              {batchResult.failed.map((f, i) => (
                <div
                  key={`fail-${i}`}
                  className="flex items-center gap-3 rounded-[var(--radius)] border border-[var(--lavender-mist)] bg-white px-3 py-2.5"
                >
                  <IconFile className="shrink-0 text-[var(--mist)]" />
                  <span className="min-w-0 flex-1 truncate text-sm text-[var(--deep-ink)]">
                    {f.filename}
                  </span>
                  <StatusBadge status="failed" />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="border-t border-[var(--lavender-mist)] px-5 py-4">
          {phase === "staging" && (
            <button
              onClick={() => void handleUploadAll()}
              disabled={stagedFiles.length === 0}
              className={clsx(
                "w-full rounded-[var(--radius)] py-2.5 text-sm font-medium transition-all",
                stagedFiles.length > 0
                  ? "bg-[var(--electric-violet)] text-white shadow-sm shadow-[var(--electric-violet)]/25 hover:opacity-90"
                  : "cursor-not-allowed bg-[var(--lavender-mist)] text-[var(--mist)]",
              )}
            >
              Upload All
            </button>
          )}
          {phase === "done" && (
            <button
              onClick={handleUploadMore}
              className="w-full rounded-[var(--radius)] border border-[var(--electric-violet)] py-2.5 text-sm font-medium text-[var(--electric-violet)] transition-colors hover:bg-[var(--iris-haze)]"
            >
              Upload more
            </button>
          )}
        </div>
      </div>
  );
}

/* ─── Status badge ───────────────────────────────────────────── */

function StatusBadge({ status }: { status: "pending" | "processing" | "ready" | "failed" }) {
  return (
    <span
      className={clsx(
        "shrink-0 text-xs px-2 py-0.5 rounded-full font-medium",
        status === "pending" && "bg-[var(--cloud)] text-[var(--overcast)]",
        status === "processing" && "bg-amber-100 text-amber-700 animate-pulse",
        status === "ready" && "bg-emerald-100 text-[var(--success)]",
        status === "failed" && "bg-[var(--danger-bg)] text-[var(--danger)]",
      )}
    >
      {status === "pending" && "Pending"}
      {status === "processing" && "Processing"}
      {status === "ready" && "Ready"}
      {status === "failed" && "Failed"}
    </span>
  );
}
