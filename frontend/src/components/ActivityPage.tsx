"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import clsx from "clsx";
import {
  listBatches,
  getBatch,
  type BatchSummary,
  type BatchDetail,
} from "@/lib/api";
import AppSidebar from "@/components/AppSidebar";

/* ─── Helpers ──────────────────────────────────────────────────── */

function timeAgo(date: string): string {
  const s = Math.floor((Date.now() - new Date(date).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return Math.floor(s / 60) + "m ago";
  if (s < 86400) return Math.floor(s / 3600) + "h ago";
  return Math.floor(s / 86400) + "d ago";
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

type BatchStatus = "complete" | "in_progress" | "failed" | "partial";

function deriveBatchStatus(b: BatchSummary): BatchStatus {
  if (b.total_files === 0) return "complete";
  if (b.failed === b.total_files) return "failed";
  if (b.ready === b.total_files) return "complete";
  if (b.processing > 0 || b.pending > 0) return "in_progress";
  if (b.ready > 0 && b.failed > 0) return "partial";
  return "complete";
}

const statusConfig: Record<BatchStatus, { label: string; dot: string; bg: string; text: string }> = {
  complete:    { label: "Complete",    dot: "bg-[var(--success)]",                bg: "bg-emerald-50",  text: "text-[var(--success)]" },
  in_progress: { label: "In Progress", dot: "bg-[var(--warning)] animate-pulse", bg: "bg-amber-50",    text: "text-[var(--warning)]" },
  failed:      { label: "Failed",      dot: "bg-[var(--danger)]",                bg: "bg-[var(--danger-bg)]", text: "text-[var(--danger)]" },
  partial:     { label: "Partial",     dot: "bg-orange-500",                     bg: "bg-orange-50",   text: "text-orange-600" },
};

const docStatusColors: Record<string, { bg: string; text: string }> = {
  ready:      { bg: "bg-emerald-50",         text: "text-[var(--success)]" },
  processing: { bg: "bg-amber-50",           text: "text-[var(--warning)]" },
  pending:    { bg: "bg-[var(--iris-haze)]", text: "text-[var(--overcast)]" },
  failed:     { bg: "bg-[var(--danger-bg)]", text: "text-[var(--danger)]" },
};

/* ─── Component ────────────────────────────────────────────────── */

export default function ActivityPage() {
  const searchParams = useSearchParams();
  const highlightId = searchParams.get("highlight");

  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(highlightId);
  const [expandedDetail, setExpandedDetail] = useState<BatchDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(Date.now());
  const [tick, setTick] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchBatches = useCallback(async () => {
    try {
      const res = await listBatches();
      setBatches(res.items);
      setLastRefresh(Date.now());
    } catch {
      /* keep stale */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchBatches();
    pollRef.current = setInterval(() => void fetchBatches(), 5000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [fetchBatches]);

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const secondsAgo = Math.floor((Date.now() - lastRefresh) / 1000);

  async function toggleExpand(batchId: string) {
    if (expandedId === batchId) {
      setExpandedId(null);
      setExpandedDetail(null);
      return;
    }
    setExpandedId(batchId);
    setDetailLoading(true);
    try {
      const detail = await getBatch(batchId);
      setExpandedDetail(detail);
    } catch {
      setExpandedDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }

  const activeCount = batches.filter((b) => deriveBatchStatus(b) === "in_progress").length;

  return (
    <AppSidebar>
      <main className="flex-1 overflow-y-auto bg-[var(--iris-haze)]">
        <div className="mx-auto max-w-[900px] px-6 py-10">
          {/* Title row */}
          <div className="mb-8 flex items-end justify-between">
            <div>
              <h1
                className="mb-1 text-[28px] font-medium tracking-[-0.03em] text-[var(--deep-ink)]"
                style={{ fontFamily: "'Source Serif 4', serif" }}
              >
                Activity{" "}
                <span className="bg-gradient-to-r from-[var(--electric-violet)] to-purple-500 bg-clip-text text-transparent">
                  Monitor
                </span>
              </h1>
              <p className="text-sm text-[var(--overcast)]">
                Track the processing status of your document batches
              </p>
            </div>
            <div className="flex items-center gap-3">
              {activeCount > 0 && (
                <span className="flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-[var(--warning)]">
                  <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--warning)]" />
                  {activeCount} active
                </span>
              )}
              <span className="text-xs text-[var(--mist)]">
                Updated {secondsAgo === 0 ? "just now" : `${secondsAgo}s ago`}
              </span>
            </div>
          </div>

          {/* Batch list */}
          {loading && batches.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24">
              <svg className="mb-3 h-8 w-8 animate-spin text-[var(--electric-violet)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M21 12a9 9 0 11-6.219-8.56" />
              </svg>
              <p className="text-sm text-[var(--overcast)]">Loading batches…</p>
            </div>
          ) : batches.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-[var(--radius-lg)] border-2 border-dashed border-[var(--lavender-mist)] py-24">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--iris-haze)]">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--mist)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                </svg>
              </div>
              <p className="mb-1 text-sm font-medium text-[var(--deep-ink)]">No upload batches yet</p>
              <p className="mb-5 text-xs text-[var(--overcast)]">Upload documents to see their processing status here</p>
              <Link
                href="/upload"
                className="rounded-full bg-[var(--electric-violet)] px-6 py-2.5 text-sm font-medium text-white shadow-sm shadow-[var(--electric-violet)]/25 hover:shadow-md"
              >
                Upload Files
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {batches.map((batch) => {
                const status = deriveBatchStatus(batch);
                const cfg = statusConfig[status];
                const isExpanded = expandedId === batch.id;
                const pct = batch.total_files > 0 ? Math.round((batch.ready / batch.total_files) * 100) : 0;
                const isHighlighted = batch.id === highlightId;

                return (
                  <div
                    key={batch.id}
                    className={clsx(
                      "overflow-hidden rounded-[var(--radius-lg)] border bg-[var(--pure-paper)] transition-all",
                      isHighlighted && !isExpanded
                        ? "border-[var(--electric-violet)]/30 shadow-md shadow-[var(--electric-violet)]/10"
                        : isExpanded
                          ? "border-[var(--electric-violet)]/20 shadow-lg shadow-[var(--deep-ink)]/5"
                          : "border-[var(--lavender-mist)] hover:border-[var(--electric-violet)]/15 hover:shadow-md hover:shadow-[var(--deep-ink)]/5",
                    )}
                  >
                    {/* Batch row */}
                    <button
                      type="button"
                      onClick={() => void toggleExpand(batch.id)}
                      className="flex w-full items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-[var(--iris-haze)]/40"
                    >
                      {/* Chevron */}
                      <svg
                        width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                        className={clsx("shrink-0 text-[var(--mist)] transition-transform duration-200", isExpanded && "rotate-90")}
                      >
                        <polyline points="9 18 15 12 9 6" />
                      </svg>

                      {/* Info */}
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-[var(--deep-ink)]">
                          {batch.label}
                        </p>
                        <div className="mt-1.5 flex items-center gap-3 text-xs text-[var(--overcast)]">
                          <span>{batch.total_files} file{batch.total_files !== 1 ? "s" : ""}</span>
                          <span className="text-[var(--lavender-mist)]">·</span>
                          <span>{timeAgo(batch.created_at)}</span>
                        </div>
                      </div>

                      {/* Progress */}
                      <div className="flex w-[140px] shrink-0 flex-col items-end gap-1.5">
                        <div className="flex w-full items-center gap-2">
                          <div className="flex h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--lavender-mist)]">
                            {batch.ready > 0 && (
                              <div className="h-full bg-[var(--success)] transition-all" style={{ width: `${(batch.ready / batch.total_files) * 100}%` }} />
                            )}
                            {batch.processing > 0 && (
                              <div className="h-full bg-[var(--warning)] transition-all" style={{ width: `${(batch.processing / batch.total_files) * 100}%` }} />
                            )}
                            {batch.failed > 0 && (
                              <div className="h-full bg-[var(--danger)] transition-all" style={{ width: `${(batch.failed / batch.total_files) * 100}%` }} />
                            )}
                          </div>
                          <span className="w-[32px] text-right text-[11px] font-medium text-[var(--overcast)]">
                            {pct}%
                          </span>
                        </div>
                      </div>

                      {/* Status badge */}
                      <span className={clsx("flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium", cfg.bg, cfg.text)}>
                        <span className={clsx("inline-block h-1.5 w-1.5 rounded-full", cfg.dot)} />
                        {cfg.label}
                      </span>
                    </button>

                    {/* Expanded detail */}
                    {isExpanded && (
                      <div className="border-t border-[var(--lavender-mist)]">
                        {detailLoading ? (
                          <div className="flex items-center justify-center gap-2 py-8 text-sm text-[var(--overcast)]">
                            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                              <path d="M21 12a9 9 0 11-6.219-8.56" />
                            </svg>
                            Loading documents…
                          </div>
                        ) : expandedDetail && expandedDetail.documents.length > 0 ? (
                          <div className="divide-y divide-[var(--lavender-mist)]/60">
                            {/* Stats row */}
                            <div className="flex items-center gap-6 bg-[var(--iris-haze)]/50 px-5 py-3">
                              <Stat label="Ready" value={expandedDetail.ready} color="text-[var(--success)]" />
                              <Stat label="Processing" value={expandedDetail.processing} color="text-[var(--warning)]" />
                              <Stat label="Pending" value={expandedDetail.pending} color="text-[var(--overcast)]" />
                              <Stat label="Failed" value={expandedDetail.failed} color="text-[var(--danger)]" />
                            </div>
                            {/* Document rows */}
                            {expandedDetail.documents.map((doc) => {
                              const dc = docStatusColors[doc.status] ?? docStatusColors.pending;
                              return (
                                <div key={doc.id} className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-[var(--iris-haze)]/30">
                                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--iris-haze)] text-[9px] font-bold text-[var(--overcast)]">
                                    {doc.filename.toLowerCase().endsWith(".docx") ? "DOCX" : "PDF"}
                                  </div>
                                  <div className="min-w-0 flex-1">
                                    <p className="truncate text-sm text-[var(--deep-ink)]">{doc.filename}</p>
                                  </div>
                                  <span className="text-xs text-[var(--overcast)]">{formatSize(doc.file_size_bytes)}</span>
                                  <span className={clsx("rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize", dc.bg, dc.text)}>
                                    {doc.status}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <p className="px-5 py-6 text-center text-sm text-[var(--mist)]">No documents in this batch</p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </AppSidebar>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className={clsx("text-sm font-semibold", color)}>{value}</span>
      <span className="text-xs text-[var(--overcast)]">{label}</span>
    </div>
  );
}
