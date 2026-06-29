"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import {
  Activity,
  ArrowLeft,
  BarChart3,
  Cpu,
  Database,
  FileStack,
  Gauge,
  Loader2,
  RefreshCw,
} from "lucide-react";
import {
  AIUsageMetrics,
  DocumentMetrics,
  PlatformMetricsSnapshot,
  ProcessingHistory,
  ProcessingMetrics,
  StorageMetrics,
  SystemMetrics,
  getPlatformMetricsSnapshot,
} from "@/lib/api";

type PlatformSection = "usage" | "documents" | "processing" | "storage" | "system";

const NAV_ITEMS: { id: PlatformSection; label: string; icon: typeof Gauge }[] = [
  { id: "usage", label: "Usage", icon: Gauge },
  { id: "documents", label: "Documents", icon: FileStack },
  { id: "processing", label: "Processing", icon: Cpu },
  { id: "storage", label: "Storage", icon: Database },
  { id: "system", label: "System", icon: Activity },
];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function formatMs(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

function formatPercent(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

function formatUsd(amount: number): string {
  if (amount < 0.01) return `$${amount.toFixed(4)}`;
  return `$${amount.toFixed(2)}`;
}

function formatNumber(value: number): string {
  return value.toLocaleString();
}

function StatCard({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: string;
  hint?: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--lavender-mist)] bg-[var(--pure-paper)] p-4">
      <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-[var(--mist)]">{label}</p>
      <p
        className={clsx(
          "mt-1 text-2xl font-semibold tracking-tight",
          accent ? "text-[var(--electric-violet)]" : "text-[var(--deep-ink)]",
        )}
      >
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-[var(--overcast)]">{hint}</p>}
    </div>
  );
}

function SectionHeader({ title, description }: { title: string; description: string }) {
  return (
    <div className="mb-6">
      <h1
        className="text-2xl font-semibold tracking-[-0.02em] text-[var(--deep-ink)]"
        style={{ fontFamily: "'Source Serif 4', serif" }}
      >
        {title}
      </h1>
      <p className="mt-1 text-sm text-[var(--overcast)]">{description}</p>
    </div>
  );
}

function StatusBar({
  segments,
}: {
  segments: { label: string; value: number; color: string }[];
}) {
  const total = segments.reduce((sum, item) => sum + item.value, 0);
  if (total === 0) {
    return <p className="text-sm text-[var(--mist)]">No documents yet</p>;
  }

  return (
    <div>
      <div className="flex h-3 overflow-hidden rounded-full bg-[var(--lavender-mist)]">
        {segments.map((segment) =>
          segment.value > 0 ? (
            <div
              key={segment.label}
              className="h-full transition-all"
              style={{
                width: `${(segment.value / total) * 100}%`,
                backgroundColor: segment.color,
              }}
              title={`${segment.label}: ${segment.value}`}
            />
          ) : null,
        )}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2">
        {segments.map((segment) => (
          <div key={segment.label} className="flex items-center gap-2 text-xs text-[var(--heather)]">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: segment.color }} />
            <span>
              {segment.label}: <strong className="text-[var(--deep-ink)]">{segment.value}</strong>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function UsagePanel({ data }: { data: AIUsageMetrics }) {
  const quotaUsed =
    data.daily_request_quota != null && data.daily_request_quota > 0
      ? (data.daily_request_count / data.daily_request_quota) * 100
      : null;

  return (
    <div>
      <SectionHeader
        title="Usage"
        description="AI API consumption, token counts, and estimated cost for this vault."
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total requests" value={formatNumber(data.total_requests)} accent />
        <StatCard
          label="Input tokens"
          value={formatNumber(data.total_input_tokens)}
          hint={`Output: ${formatNumber(data.total_output_tokens)}`}
        />
        <StatCard label="Estimated cost" value={formatUsd(data.estimated_cost_usd)} accent />
        <StatCard
          label="Daily quota"
          value={
            data.daily_request_quota != null
              ? `${formatNumber(data.daily_request_count)} / ${formatNumber(data.daily_request_quota)}`
              : formatNumber(data.daily_request_count)
          }
          hint={
            data.daily_quota_remaining != null
              ? `${formatNumber(data.daily_quota_remaining)} remaining today`
              : undefined
          }
        />
      </div>

      {quotaUsed != null && (
        <div className="mt-6 rounded-[var(--radius-lg)] border border-[var(--lavender-mist)] bg-[var(--pure-paper)] p-4">
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="font-medium text-[var(--deep-ink)]">Daily request quota</span>
            <span className="text-[var(--overcast)]">{formatPercent(quotaUsed / 100)} used</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-[var(--lavender-mist)]">
            <div
              className="h-full rounded-full bg-[var(--electric-violet)] transition-all"
              style={{ width: `${Math.min(quotaUsed, 100)}%` }}
            />
          </div>
        </div>
      )}

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <BreakdownTable
          title="By operation"
          columns={["Operation", "Requests", "Tokens", "Cost"]}
          rows={data.by_operation.map((row) => [
            row.operation,
            formatNumber(row.requests),
            formatNumber(row.input_tokens + row.output_tokens),
            formatUsd(row.estimated_cost_usd),
          ])}
          emptyMessage="No AI operations recorded yet."
        />
        <BreakdownTable
          title="By provider"
          columns={["Provider", "Requests", "Tokens", "Cost"]}
          rows={data.by_provider.map((row) => [
            row.provider,
            formatNumber(row.requests),
            formatNumber(row.input_tokens + row.output_tokens),
            formatUsd(row.estimated_cost_usd),
          ])}
          emptyMessage="No provider usage recorded yet."
        />
      </div>
    </div>
  );
}

function DocumentsPanel({ data }: { data: DocumentMetrics }) {
  return (
    <div>
      <SectionHeader
        title="Documents"
        description="Vault inventory, processing status, and indexed chunk totals."
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total documents" value={formatNumber(data.total)} accent />
        <StatCard label="Ready for chat" value={formatNumber(data.ready)} />
        <StatCard label="Total storage" value={formatBytes(data.total_size_bytes)} />
        <StatCard label="Indexed chunks" value={formatNumber(data.total_chunks)} />
      </div>

      <div className="mt-6 rounded-[var(--radius-lg)] border border-[var(--lavender-mist)] bg-[var(--pure-paper)] p-5">
        <p className="mb-4 text-sm font-medium text-[var(--deep-ink)]">Status breakdown</p>
        <StatusBar
          segments={[
            { label: "Ready", value: data.ready, color: "#16a34a" },
            { label: "Processing", value: data.processing, color: "#ca8a04" },
            { label: "Pending", value: data.pending, color: "#676b89" },
            { label: "Failed", value: data.failed, color: "#ef4444" },
          ]}
        />
      </div>
    </div>
  );
}

function ProcessingPanel({
  metrics,
  history,
}: {
  metrics: ProcessingMetrics;
  history: ProcessingHistory;
}) {
  return (
    <div>
      <SectionHeader
        title="Processing"
        description="Ingestion pipeline performance, failure rates, and recent job history."
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total jobs" value={formatNumber(metrics.total_jobs)} accent />
        <StatCard label="Completed" value={formatNumber(metrics.completed)} />
        <StatCard label="Failed" value={formatNumber(metrics.failed)} />
        <StatCard
          label="Failure rate"
          value={formatPercent(metrics.failure_rate)}
          hint={`Avg duration: ${formatMs(metrics.avg_duration_ms)}`}
        />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <BreakdownTable
          title="Stage breakdown"
          columns={["Stage", "Completed", "Failed", "Avg time"]}
          rows={metrics.by_stage.map((row) => [
            row.stage,
            formatNumber(row.completed),
            formatNumber(row.failed),
            formatMs(row.avg_duration_ms),
          ])}
          emptyMessage="No pipeline stages recorded yet."
        />

        <div className="rounded-[var(--radius-lg)] border border-[var(--lavender-mist)] bg-[var(--pure-paper)] p-4">
          <p className="mb-3 text-sm font-medium text-[var(--deep-ink)]">Recent jobs</p>
          {history.items.length === 0 ? (
            <p className="text-sm text-[var(--mist)]">No processing jobs yet.</p>
          ) : (
            <div className="max-h-72 overflow-y-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[var(--lavender-mist)] text-[var(--overcast)]">
                    <th className="pb-2 pr-2 font-medium">Stage</th>
                    <th className="pb-2 pr-2 font-medium">Status</th>
                    <th className="pb-2 pr-2 font-medium">Duration</th>
                    <th className="pb-2 font-medium">When</th>
                  </tr>
                </thead>
                <tbody>
                  {history.items.map((job) => (
                    <tr key={job.id} className="border-b border-[var(--lavender-mist)]/60">
                      <td className="py-2 pr-2 font-medium text-[var(--deep-ink)]">{job.stage}</td>
                      <td className="py-2 pr-2">
                        <span
                          className={clsx(
                            "rounded-full px-2 py-0.5 text-[10px] font-medium uppercase",
                            job.status === "completed" && "bg-green-50 text-green-700",
                            job.status === "failed" && "bg-red-50 text-red-700",
                            job.status === "started" && "bg-amber-50 text-amber-700",
                          )}
                        >
                          {job.status}
                        </span>
                      </td>
                      <td className="py-2 pr-2 text-[var(--heather)]">{formatMs(job.duration_ms)}</td>
                      <td className="py-2 text-[var(--overcast)]">
                        {new Date(job.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StoragePanel({ data }: { data: StorageMetrics }) {
  return (
    <div>
      <SectionHeader
        title="Storage"
        description="Uploaded files, indexed chunks, chat data, and embedding configuration."
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <StatCard label="File storage" value={formatBytes(data.total_file_bytes)} accent />
        <StatCard
          label="Filesystem usage"
          value={data.filesystem_bytes != null ? formatBytes(data.filesystem_bytes) : "—"}
          hint="On-disk upload directory size"
        />
        <StatCard label="Indexed chunks" value={formatNumber(data.total_chunks)} />
        <StatCard label="Chat sessions" value={formatNumber(data.total_chat_sessions)} />
        <StatCard label="Chat messages" value={formatNumber(data.total_chat_messages)} />
        <StatCard
          label="Embedding dimension"
          value={formatNumber(data.embedding_dimension)}
          hint="Vector size per chunk"
        />
      </div>
    </div>
  );
}

function SystemPanel({ data }: { data: SystemMetrics }) {
  return (
    <div>
      <SectionHeader
        title="System"
        description="API latency, worker queue depth, throughput, and chat/RAG performance."
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Avg API latency" value={formatMs(data.avg_api_latency_ms)} accent />
        <StatCard label="P95 API latency" value={formatMs(data.p95_api_latency_ms)} />
        <StatCard label="Queue depth" value={formatNumber(data.worker_queue_depth)} />
        <StatCard
          label="Docs / hour"
          value={formatNumber(data.documents_per_hour)}
          hint={`Doc failure rate: ${formatPercent(data.document_failure_rate)}`}
        />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <div className="rounded-[var(--radius-lg)] border border-[var(--lavender-mist)] bg-[var(--pure-paper)] p-4">
          <p className="mb-3 text-sm font-medium text-[var(--deep-ink)]">Chat / RAG</p>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--overcast)]">Requests (sample window)</dt>
              <dd className="font-medium text-[var(--deep-ink)]">{formatNumber(data.chat.total_requests)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--overcast)]">Error rate</dt>
              <dd className="font-medium text-[var(--deep-ink)]">{formatPercent(data.chat.error_rate)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--overcast)]">Avg RAG duration</dt>
              <dd className="font-medium text-[var(--deep-ink)]">{formatMs(data.chat.avg_rag_duration_ms)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--overcast)]">Avg retrieval</dt>
              <dd className="font-medium text-[var(--deep-ink)]">
                {formatMs(data.chat.avg_retrieval_duration_ms)}
              </dd>
            </div>
          </dl>
        </div>

        <BreakdownTable
          title="Latency by route"
          columns={["Route", "Avg", "P95", "Samples"]}
          rows={data.api_latency_by_route.map((row) => [
            row.route,
            formatMs(row.avg_duration_ms),
            formatMs(row.p95_duration_ms),
            formatNumber(row.sample_count),
          ])}
          emptyMessage="No API latency samples yet."
        />
      </div>
    </div>
  );
}

function BreakdownTable({
  title,
  columns,
  rows,
  emptyMessage,
}: {
  title: string;
  columns: string[];
  rows: string[][];
  emptyMessage: string;
}) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--lavender-mist)] bg-[var(--pure-paper)] p-4">
      <p className="mb-3 text-sm font-medium text-[var(--deep-ink)]">{title}</p>
      {rows.length === 0 ? (
        <p className="text-sm text-[var(--mist)]">{emptyMessage}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[var(--lavender-mist)] text-[var(--overcast)]">
                {columns.map((column) => (
                  <th key={column} className="pb-2 pr-3 font-medium last:pr-0">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index} className="border-b border-[var(--lavender-mist)]/60 last:border-0">
                  {row.map((cell, cellIndex) => (
                    <td
                      key={cellIndex}
                      className={clsx(
                        "py-2 pr-3 last:pr-0",
                        cellIndex === 0 ? "font-medium text-[var(--deep-ink)]" : "text-[var(--heather)]",
                      )}
                    >
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function PlatformDashboard() {
  const [section, setSection] = useState<PlatformSection>("usage");
  const [data, setData] = useState<PlatformMetricsSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadMetrics = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const snapshot = await getPlatformMetricsSnapshot();
      setData(snapshot);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load metrics");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadMetrics();
    const interval = window.setInterval(() => void loadMetrics(true), 30000);
    return () => window.clearInterval(interval);
  }, [loadMetrics]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--iris-haze)]">
      <aside className="flex w-[240px] shrink-0 flex-col border-r border-[var(--lavender-mist)] bg-[var(--pure-paper)]">
        <div className="border-b border-[var(--lavender-mist)] px-4 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--electric-violet)] text-white">
              <BarChart3 className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-semibold text-[var(--deep-ink)]">Platform</p>
              <p className="text-[11px] text-[var(--overcast)]">Document Vault AI</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-3">
          <p className="px-3 pb-2 text-[11px] font-medium uppercase tracking-[0.06em] text-[var(--mist)]">
            Metrics
          </p>
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setSection(id)}
              className={clsx(
                "mb-0.5 flex w-full items-center gap-2.5 rounded-[var(--radius)] px-3 py-2 text-left text-[14px] transition-colors",
                section === id
                  ? "bg-[var(--iris-haze)] font-medium text-[var(--deep-ink)]"
                  : "text-[var(--heather)] hover:bg-[var(--iris-haze)]",
              )}
            >
              <Icon className="h-4 w-4 shrink-0 opacity-70" />
              {label}
            </button>
          ))}
        </nav>

        <div className="border-t border-[var(--lavender-mist)] px-3 py-3">
          <Link
            href="/"
            className="flex items-center gap-2 rounded-[var(--radius)] px-3 py-2 text-[14px] text-[var(--heather)] transition-colors hover:bg-[var(--iris-haze)] hover:text-[var(--deep-ink)]"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to chat
          </Link>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-[var(--lavender-mist)] bg-[var(--pure-paper)] px-6">
          <div>
            <p className="text-xs text-[var(--overcast)]">Operations dashboard</p>
            {lastUpdated && (
              <p className="text-[11px] text-[var(--mist)]">
                Updated {lastUpdated.toLocaleTimeString()} · refreshes every 30s
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() => void loadMetrics(true)}
            disabled={refreshing}
            className="flex items-center gap-2 rounded-full border border-[var(--lavender-mist)] px-3 py-1.5 text-xs font-medium text-[var(--heather)] transition-colors hover:border-[var(--electric-violet)] hover:text-[var(--electric-violet)] disabled:opacity-60"
          >
            {refreshing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Refresh
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          {loading && !data ? (
            <div className="flex h-full items-center justify-center">
              <div className="flex items-center gap-2 text-sm text-[var(--overcast)]">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading metrics…
              </div>
            </div>
          ) : error && !data ? (
            <div className="mx-auto max-w-lg rounded-[var(--radius-lg)] border border-red-200 bg-[var(--danger-bg)] p-5 text-center">
              <p className="text-sm text-[var(--danger)]">{error}</p>
              <button
                type="button"
                onClick={() => void loadMetrics()}
                className="mt-3 rounded-full bg-[var(--electric-violet)] px-4 py-1.5 text-xs font-medium text-white"
              >
                Retry
              </button>
            </div>
          ) : data ? (
            <>
              {error && (
                <p className="mb-4 rounded-[var(--radius)] bg-[var(--danger-bg)] px-4 py-2 text-sm text-[var(--danger)]">
                  Refresh failed: {error}
                </p>
              )}
              {section === "usage" && <UsagePanel data={data.aiUsage} />}
              {section === "documents" && <DocumentsPanel data={data.documents} />}
              {section === "processing" && (
                <ProcessingPanel metrics={data.processing} history={data.processingHistory} />
              )}
              {section === "storage" && <StoragePanel data={data.storage} />}
              {section === "system" && <SystemPanel data={data.system} />}
            </>
          ) : null}
        </div>
      </main>
    </div>
  );
}
