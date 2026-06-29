"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import {
  listBatches,
  getBatch,
  type BatchSummary,
  type BatchDetail,
} from "@/lib/api";

/* ─── Props ───────────────────────────────────────────────────── */

interface ActivityMonitorPanelProps {
  onClose: () => void;
}

/* ─── Helpers ─────────────────────────────────────────────────── */

function timeAgo(date: string): string {
  const seconds = Math.floor((Date.now() - new Date(date).getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return Math.floor(seconds / 60) + " min ago";
  if (seconds < 86400) return Math.floor(seconds / 3600) + "h ago";
  return Math.floor(seconds / 86400) + "d ago";
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

type BatchStatus = "complete" | "in_progress" | "failed" | "partial";

function deriveBatchStatus(b: BatchSummary): BatchStatus {
  if (b.failed === b.total_files && b.total_files > 0) return "failed";
  if (b.ready === b.total_files && b.total_files > 0) return "complete";
  if (b.processing > 0 || b.pending > 0) return "in_progress";
  if (b.ready > 0 && b.failed > 0) return "partial";
  return "complete";
}

/* ─── Icons ───────────────────────────────────────────────────── */

function IconX({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
    >
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  );
}

function IconChevron({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function IconFile({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

function IconLoader({ className }: { className?: string }) {
  return (
    <svg
      className={clsx("animate-spin", className)}
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
    >
      <path d="M21 12a9 9 0 11-6.219-8.56" />
    </svg>
  );
}

/* ─── Status badge ────────────────────────────────────────────── */

function StatusBadge({ status }: { status: BatchStatus | string }) {
  const config: Record<string, { label: string; classes: string }> = {
    complete: {
      label: "Complete",
      classes: "bg-[var(--success)]/10 text-[var(--success)]",
    },
    in_progress: {
      label: "In Progress",
      classes: "bg-[var(--warning)]/10 text-[var(--warning)] animate-pulse",
    },
    failed: {
      label: "Failed",
      classes: "bg-[var(--danger-bg)] text-[var(--danger)]",
    },
    partial: {
      label: "Partial",
      classes: "bg-orange-50 text-orange-600",
    },
    ready: {
      label: "Ready",
      classes: "bg-[var(--success)]/10 text-[var(--success)]",
    },
    processing: {
      label: "Processing",
      classes: "bg-[var(--warning)]/10 text-[var(--warning)] animate-pulse",
    },
    pending: {
      label: "Pending",
      classes: "bg-[var(--overcast)]/10 text-[var(--overcast)]",
    },
  };

  const c = config[status] ?? {
    label: status,
    classes: "bg-[var(--overcast)]/10 text-[var(--overcast)]",
  };

  return (
    <span
      className={clsx(
        "inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium",
        c.classes,
      )}
    >
      {c.label}
    </span>
  );
}

/* ─── Progress bar ────────────────────────────────────────────── */

function ProgressBar({ batch }: { batch: BatchSummary }) {
  const total = batch.total_files || 1;
  const segments = [
    { count: batch.ready, color: "var(--success)" },
    { count: batch.processing, color: "var(--warning)" },
    { count: batch.pending, color: "var(--overcast)" },
    { count: batch.failed, color: "var(--danger)" },
  ];

  return (
    <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-[var(--lavender-mist)]">
      {segments.map(
        (seg, i) =>
          seg.count > 0 && (
            <div
              key={i}
              className="h-full transition-all"
              style={{
                width: `${(seg.count / total) * 100}%`,
                backgroundColor: seg.color,
              }}
            />
          ),
      )}
    </div>
  );
}

/* ─── Expanded batch row ──────────────────────────────────────── */

function BatchDocuments({ batchId }: { batchId: string }) {
  const [detail, setDetail] = useState<BatchDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getBatch(batchId)
      .then((d) => {
        if (!cancelled) setDetail(d);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [batchId]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-4 py-3 text-xs text-[var(--overcast)]">
        <IconLoader className="h-3.5 w-3.5" />
        Loading documents…
      </div>
    );
  }

  if (!detail || detail.documents.length === 0) {
    return (
      <p className="px-4 py-3 text-xs text-[var(--mist)]">
        No documents in this batch.
      </p>
    );
  }

  return (
    <div className="divide-y divide-[var(--lavender-mist)]/60">
      {detail.documents.map((doc) => (
        <div
          key={doc.id}
          className="flex items-center gap-3 px-4 py-2.5 text-sm"
        >
          <IconFile className="shrink-0 text-[var(--mist)]" />
          <span className="min-w-0 flex-1 truncate text-[var(--deep-ink)]">
            {doc.filename}
          </span>
          <StatusBadge status={doc.status} />
          <span className="shrink-0 text-xs text-[var(--overcast)]">
            {formatFileSize(doc.file_size_bytes)}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ─── Main component ──────────────────────────────────────────── */

export default function ActivityMonitorPanel({
  onClose,
}: ActivityMonitorPanelProps) {
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [lastFetched, setLastFetched] = useState<number>(Date.now());
  const [secondsAgo, setSecondsAgo] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchBatches = useCallback(async () => {
    try {
      const res = await listBatches();
      setBatches(res.items);
      setLastFetched(Date.now());
    } catch {
      // keep stale data on error
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchBatches();
    const id = setInterval(() => void fetchBatches(), 5000);
    return () => clearInterval(id);
  }, [fetchBatches]);

  useEffect(() => {
    const tick = () =>
      setSecondsAgo(Math.floor((Date.now() - lastFetched) / 1000));
    tick();
    intervalRef.current = setInterval(tick, 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [lastFetched]);

  const toggleExpand = (id: string) =>
    setExpandedId((prev) => (prev === id ? null : id));

  return (
    <div className="flex h-full w-[480px] flex-col bg-[var(--ghost-white)]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--lavender-mist)] px-5 py-4">
        <h2
          className="text-base font-semibold text-[var(--deep-ink)]"
          style={{ fontFamily: "'Source Serif 4', serif" }}
        >
          Activity Monitor
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-[var(--overcast)]">
            Last updated: {secondsAgo === 0 ? "just now" : `${secondsAgo}s ago`}
          </span>
          <button
            onClick={onClose}
            className="rounded-full p-1 text-[var(--mist)] transition-colors hover:bg-[var(--iris-haze)] hover:text-[var(--heather)]"
          >
            <IconX />
          </button>
        </div>
      </div>

      {/* Batch list */}
      <div className="flex-1 overflow-y-auto">
        {loading && batches.length === 0 ? (
          <div className="flex items-center justify-center gap-2 py-16 text-sm text-[var(--overcast)]">
            <IconLoader className="h-4 w-4" />
            Loading batches…
          </div>
        ) : batches.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <p className="text-sm text-[var(--overcast)]">
              No upload batches yet.
            </p>
            <p className="mt-1 text-xs text-[var(--mist)]">
              Use the Doc Uploader to get started.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[var(--lavender-mist)]">
            {batches.map((batch) => {
              const status = deriveBatchStatus(batch);
              const isExpanded = expandedId === batch.id;

              return (
                <div key={batch.id}>
                  <button
                    type="button"
                    onClick={() => toggleExpand(batch.id)}
                    className="flex w-full flex-col gap-2 px-5 py-4 text-left transition-colors hover:bg-[var(--iris-haze)]/50"
                  >
                    {/* Top row */}
                    <div className="flex items-center gap-2">
                      <IconChevron
                        className={clsx(
                          "shrink-0 text-[var(--mist)] transition-transform",
                          isExpanded && "rotate-180",
                        )}
                      />
                      <span className="flex-1 truncate text-sm font-medium text-[var(--deep-ink)]">
                        {batch.label ||
                          `Batch — ${batch.total_files} file${batch.total_files !== 1 ? "s" : ""}`}
                      </span>
                      <StatusBadge status={status} />
                    </div>

                    {/* Progress bar */}
                    <div className="pl-[22px]">
                      <ProgressBar batch={batch} />
                    </div>

                    {/* Bottom meta */}
                    <div className="flex items-center gap-3 pl-[22px] text-xs text-[var(--overcast)]">
                      <span>
                        {batch.ready} of {batch.total_files}
                      </span>
                      <span className="text-[var(--mist)]">·</span>
                      <span>{timeAgo(batch.created_at)}</span>
                    </div>
                  </button>

                  {/* Expanded detail */}
                  {isExpanded && (
                    <div className="border-t border-[var(--lavender-mist)]/60 bg-white">
                      <BatchDocuments batchId={batch.id} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
