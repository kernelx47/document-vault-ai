"use client";

import clsx from "clsx";
import {
  Activity,
  Coins,
  Cpu,
  Database,
  FileStack,
  Gauge,
  HardDrive,
  Layers,
  MessageSquare,
  Sparkles,
  Timer,
  TrendingUp,
  Zap,
} from "lucide-react";
import type {
  AIUsageMetrics,
  DocumentMetrics,
  MetricsTimeseries,
  PlatformMetricsSnapshot,
  ProcessingHistory,
  ProcessingMetrics,
  StorageMetrics,
  SystemMetrics,
} from "@/lib/api";
import {
  AIUsageTrendChart,
  CostByOperationChart,
  DonutChart,
  LatencySparklineChart,
  ProcessingTimelineChart,
  QuotaRadialChart,
  RouteLatencyChart,
  StageBarChart,
  StageDurationChart,
  StorageBreakdownChart,
  TokenSplitChart,
  UsageBarChart,
} from "./Charts";
import { ExportButton } from "./ExportButton";
import { exportAiUsageCsv, exportProcessingJobsCsv, exportRouteLatencyCsv } from "./export";
import {
  ChartCard,
  SectionHeader,
  StatCard,
  STATUS_COLORS,
  formatBytes,
  formatMs,
  formatNumber,
  formatPercent,
  formatUsd,
} from "./shared";

function HealthBadge({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold",
        ok ? "bg-emerald-500/10 text-emerald-600" : "bg-amber-500/10 text-amber-600",
      )}
    >
      <span className={clsx("h-1.5 w-1.5 rounded-full", ok ? "bg-emerald-500" : "bg-amber-500")} />
      {label}
    </span>
  );
}

function seriesFromTimeseries(ts: MetricsTimeseries) {
  return {
    aiRequests: ts.ai_usage.map((point) => point.requests),
    aiTokens: ts.ai_usage.map((point) => point.tokens),
    processingActivity: ts.processing_jobs.map((point) => point.completed + point.failed),
    latency: ts.api_latency_ms,
  };
}

export function OverviewPanel({ data }: { data: PlatformMetricsSnapshot }) {
  const series = seriesFromTimeseries(data.timeseries);
  const healthOk =
    data.processing.failure_rate < 0.1 &&
    data.system.chat.error_rate < 0.05 &&
    data.documents.failed <= Math.max(1, data.documents.total * 0.05);

  return (
    <div>
      <SectionHeader
        title="Overview"
        description="Real-time snapshot of vault health, AI consumption, and pipeline performance."
      />

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <HealthBadge label={healthOk ? "All systems healthy" : "Needs attention"} ok={healthOk} />
        <span className="text-xs text-[var(--overcast)]">
          {formatNumber(data.documents.ready)} docs ready · {formatNumber(data.system.worker_queue_depth)} queued jobs
        </span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Documents" value={formatNumber(data.documents.total)} hint={`${formatNumber(data.documents.ready)} ready`} icon={FileStack} gradient="violet" large sparkline={series.processingActivity} sparklineColor="#7c3aed" />
        <StatCard label="AI requests" value={formatNumber(data.aiUsage.total_requests)} hint={formatUsd(data.aiUsage.estimated_cost_usd)} icon={Sparkles} gradient="cyan" large sparkline={series.aiRequests} sparklineColor="#06b6d4" />
        <StatCard label="Pipeline jobs" value={formatNumber(data.processing.total_jobs)} hint={`${formatPercent(data.processing.failure_rate)} failure rate`} icon={Cpu} gradient="amber" sparkline={series.processingActivity} sparklineColor="#ca8a04" />
        <StatCard label="API latency" value={formatMs(data.system.avg_api_latency_ms)} hint={`P95 ${formatMs(data.system.p95_api_latency_ms)}`} icon={HardDrive} gradient="green" sparkline={series.latency} sparklineColor="#16a34a" />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <ChartCard title="AI usage trend" subtitle="Hourly requests and tokens (24h)" className="xl:col-span-2">
          <AIUsageTrendChart data={data.timeseries.ai_usage} />
        </ChartCard>
        <ChartCard title="Document status" subtitle="Distribution across the vault">
          <DonutChart
            data={[
              { name: "Ready", value: data.documents.ready, color: STATUS_COLORS.ready },
              { name: "Processing", value: data.documents.processing, color: STATUS_COLORS.processing },
              { name: "Pending", value: data.documents.pending, color: STATUS_COLORS.pending },
              { name: "Failed", value: data.documents.failed, color: STATUS_COLORS.failed },
            ]}
          />
        </ChartCard>

        <ChartCard title="AI usage by operation" subtitle="Request volume per task type">
          <UsageBarChart
            data={data.aiUsage.by_operation.map((row) => ({ name: row.operation, value: row.requests }))}
            name="Requests"
            color="#06b6d4"
          />
        </ChartCard>

        <ChartCard title="Pipeline stages" subtitle="Completed vs failed by stage">
          <StageBarChart
            data={data.processing.by_stage.map((row) => ({
              stage: row.stage,
              completed: row.completed,
              failed: row.failed,
              avgMs: row.avg_duration_ms,
            }))}
          />
        </ChartCard>

        <ChartCard title="Recent job activity" subtitle="Processing timeline from job history">
          <ProcessingTimelineChart history={data.processingHistory} />
        </ChartCard>
      </div>
    </div>
  );
}

export function UsagePanel({ data, timeseries }: { data: AIUsageMetrics; timeseries: MetricsTimeseries }) {
  const series = seriesFromTimeseries({ ai_usage: timeseries.ai_usage, api_latency_ms: [], processing_jobs: [] });

  return (
    <div>
      <SectionHeader title="Usage" description="AI API consumption, token economics, and cost breakdown." />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total requests" value={formatNumber(data.total_requests)} icon={Zap} gradient="violet" sparkline={series.aiRequests} />
        <StatCard label="Input tokens" value={formatNumber(data.total_input_tokens)} hint={`Output: ${formatNumber(data.total_output_tokens)}`} icon={Layers} gradient="cyan" sparkline={series.aiTokens} sparklineColor="#06b6d4" />
        <StatCard label="Estimated cost" value={formatUsd(data.estimated_cost_usd)} icon={Coins} gradient="green" />
        <StatCard
          label="Daily quota"
          value={data.daily_request_quota != null ? `${formatNumber(data.daily_request_count)} / ${formatNumber(data.daily_request_quota)}` : formatNumber(data.daily_request_count)}
          hint={data.daily_quota_remaining != null ? `${formatNumber(data.daily_quota_remaining)} remaining` : undefined}
          icon={Gauge}
          gradient="amber"
        />
      </div>

      <div className="mt-6">
        <ChartCard
          title="Usage over time"
          subtitle="Hourly AI requests and token volume"
          action={<ExportButton compact onClick={() => exportAiUsageCsv(data.by_operation)} label="Export ops" />}
        >
          <AIUsageTrendChart data={timeseries.ai_usage} />
        </ChartCard>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <ChartCard title="Token distribution" subtitle="Input vs output token split">
          <TokenSplitChart input={data.total_input_tokens} output={data.total_output_tokens} />
        </ChartCard>

        {data.daily_request_quota != null && data.daily_request_quota > 0 ? (
          <ChartCard title="Daily quota" subtitle="Request budget consumption">
            <QuotaRadialChart used={data.daily_request_count} total={data.daily_request_quota} />
          </ChartCard>
        ) : (
          <ChartCard title="Requests by provider" subtitle="Volume per LLM provider">
            <UsageBarChart
              data={data.by_provider.map((row) => ({ name: row.provider, value: row.requests }))}
              name="Requests"
              color="#8b5cf6"
            />
          </ChartCard>
        )}

        <ChartCard
          title="Requests by operation"
          subtitle="Which AI tasks consume the most calls"
          action={<ExportButton compact onClick={() => exportAiUsageCsv(data.by_operation)} />}
        >
          <UsageBarChart
            data={data.by_operation.map((row) => ({ name: row.operation, value: row.requests }))}
            name="Requests"
          />
        </ChartCard>

        <ChartCard title="Cost by operation" subtitle="Estimated spend per task type">
          <CostByOperationChart
            data={data.by_operation.map((row) => ({
              operation: row.operation,
              cost: row.estimated_cost_usd,
              requests: row.requests,
            }))}
          />
        </ChartCard>
      </div>
    </div>
  );
}

export function DocumentsPanel({ data }: { data: DocumentMetrics }) {
  const avgChunks = data.total > 0 ? Math.round(data.total_chunks / data.total) : 0;

  return (
    <div>
      <SectionHeader title="Documents" description="Vault inventory, processing status, and indexing density." />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total documents" value={formatNumber(data.total)} icon={FileStack} gradient="violet" />
        <StatCard label="Ready for chat" value={formatNumber(data.ready)} icon={TrendingUp} gradient="green" />
        <StatCard label="Total storage" value={formatBytes(data.total_size_bytes)} icon={HardDrive} gradient="cyan" />
        <StatCard label="Indexed chunks" value={formatNumber(data.total_chunks)} hint={`~${avgChunks} per doc`} icon={Layers} gradient="amber" />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <ChartCard title="Status distribution" subtitle="Visual breakdown of document states">
          <DonutChart
            data={[
              { name: "Ready", value: data.ready, color: STATUS_COLORS.ready },
              { name: "Processing", value: data.processing, color: STATUS_COLORS.processing },
              { name: "Pending", value: data.pending, color: STATUS_COLORS.pending },
              { name: "Failed", value: data.failed, color: STATUS_COLORS.failed },
            ]}
          />
        </ChartCard>

        <ChartCard title="Volume metrics" subtitle="Storage and indexing at a glance">
          <UsageBarChart
            data={[
              { name: "Total docs", value: data.total },
              { name: "Ready", value: data.ready },
              { name: "Chunks", value: data.total_chunks },
              { name: "Failed", value: data.failed },
            ]}
            name="Count"
            color="#7c3aed"
          />
        </ChartCard>
      </div>
    </div>
  );
}

export function ProcessingPanel({
  metrics,
  history,
}: {
  metrics: ProcessingMetrics;
  history: ProcessingHistory;
}) {
  return (
    <div>
      <SectionHeader title="Processing" description="Ingestion pipeline performance, failures, and job timeline." />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total jobs" value={formatNumber(metrics.total_jobs)} icon={Cpu} gradient="violet" />
        <StatCard label="Completed" value={formatNumber(metrics.completed)} icon={TrendingUp} gradient="green" />
        <StatCard label="Failed" value={formatNumber(metrics.failed)} icon={Activity} gradient="rose" />
        <StatCard label="Failure rate" value={formatPercent(metrics.failure_rate)} hint={`Avg: ${formatMs(metrics.avg_duration_ms)}`} icon={Timer} gradient="amber" />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <ChartCard title="Stage success vs failure" subtitle="Per-stage job outcomes">
          <StageBarChart
            data={metrics.by_stage.map((row) => ({
              stage: row.stage,
              completed: row.completed,
              failed: row.failed,
              avgMs: row.avg_duration_ms,
            }))}
          />
        </ChartCard>

        <ChartCard title="Stage duration" subtitle="Average time per pipeline stage">
          <StageDurationChart data={metrics.by_stage.map((row) => ({ stage: row.stage, avgMs: row.avg_duration_ms }))} />
        </ChartCard>

        <ChartCard title="Job activity timeline" subtitle="Recent completed and failed jobs">
          <ProcessingTimelineChart history={history} />
        </ChartCard>

        <ChartCard title="Recent jobs" subtitle={`Showing ${history.items.length} of ${history.total}`} action={<ExportButton compact onClick={() => exportProcessingJobsCsv(history.items)} />}>
          {history.items.length === 0 ? (
            <p className="py-12 text-center text-sm text-[var(--admin-muted)]">No processing jobs yet.</p>
          ) : (
            <div className="max-h-[260px] overflow-y-auto">
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-[var(--admin-card)]/95 backdrop-blur-sm">
                  <tr className="border-b border-[var(--admin-border)] text-[var(--admin-muted)]">
                    <th className="pb-2 pr-2 font-semibold">Stage</th>
                    <th className="pb-2 pr-2 font-semibold">Status</th>
                    <th className="pb-2 pr-2 font-semibold">Duration</th>
                    <th className="pb-2 font-semibold">When</th>
                  </tr>
                </thead>
                <tbody>
                  {history.items.map((job) => (
                    <tr key={job.id} className="border-b border-[var(--admin-border)]/50 transition-colors hover:bg-[var(--admin-surface)]">
                      <td className="py-2.5 pr-2 font-medium capitalize text-[var(--admin-text)]">{job.stage}</td>
                      <td className="py-2.5 pr-2">
                        <span
                          className={clsx(
                            "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
                            job.status === "completed" && "bg-emerald-50 text-emerald-700",
                            job.status === "failed" && "bg-red-50 text-red-700",
                            job.status === "started" && "bg-amber-50 text-amber-700",
                          )}
                        >
                          {job.status}
                        </span>
                      </td>
                      <td className="py-2.5 pr-2 text-[var(--heather)]">{formatMs(job.duration_ms)}</td>
                      <td className="py-2.5 text-[var(--overcast)]">{new Date(job.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </ChartCard>
      </div>
    </div>
  );
}

export function StoragePanel({ data }: { data: StorageMetrics }) {
  return (
    <div>
      <SectionHeader title="Storage" description="File footprint, indexed data, chat history, and vector configuration." />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <StatCard label="File storage" value={formatBytes(data.total_file_bytes)} icon={HardDrive} gradient="violet" />
        <StatCard label="Filesystem" value={data.filesystem_bytes != null ? formatBytes(data.filesystem_bytes) : "—"} hint="On-disk uploads" icon={Database} gradient="cyan" />
        <StatCard label="Indexed chunks" value={formatNumber(data.total_chunks)} icon={Layers} gradient="green" />
        <StatCard label="Chat sessions" value={formatNumber(data.total_chat_sessions)} icon={MessageSquare} gradient="amber" />
        <StatCard label="Chat messages" value={formatNumber(data.total_chat_messages)} icon={MessageSquare} gradient="violet" />
        <StatCard label="Embedding dim" value={formatNumber(data.embedding_dimension)} hint="Vector size per chunk" icon={Sparkles} gradient="rose" />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <ChartCard title="Storage composition" subtitle="Files, chunks, sessions, and messages">
          <StorageBreakdownChart
            fileBytes={data.total_file_bytes}
            chatSessions={data.total_chat_sessions}
            chatMessages={data.total_chat_messages}
            chunks={data.total_chunks}
          />
        </ChartCard>

        <ChartCard title="Data footprint" subtitle="Relative scale of stored entities">
          <DonutChart
            data={[
              { name: "Chunks", value: data.total_chunks, color: "#7c3aed" },
              { name: "Messages", value: data.total_chat_messages, color: "#a78bfa" },
              { name: "Sessions", value: data.total_chat_sessions, color: "#06b6d4" },
            ]}
          />
        </ChartCard>
      </div>
    </div>
  );
}

export function SystemPanel({ data, timeseries }: { data: SystemMetrics; timeseries: MetricsTimeseries }) {
  return (
    <div>
      <SectionHeader title="System" description="API performance, worker queue, throughput, and RAG health." />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Avg API latency" value={formatMs(data.avg_api_latency_ms)} icon={Timer} gradient="violet" sparkline={timeseries.api_latency_ms} sparklineColor="#f59e0b" />
        <StatCard label="P95 latency" value={formatMs(data.p95_api_latency_ms)} icon={Activity} gradient="cyan" />
        <StatCard label="Queue depth" value={formatNumber(data.worker_queue_depth)} icon={Layers} gradient="amber" />
        <StatCard label="Docs / hour" value={formatNumber(data.documents_per_hour)} hint={`Doc fail: ${formatPercent(data.document_failure_rate)}`} icon={TrendingUp} gradient="green" sparkline={timeseries.processing_jobs.map((p) => p.completed)} sparklineColor="#16a34a" />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <ChartCard title="API latency trend" subtitle="Recent request latency samples">
          <LatencySparklineChart data={timeseries.api_latency_ms} />
        </ChartCard>

        <ChartCard
          title="Route latency"
          subtitle="Average vs P95 by endpoint"
          action={<ExportButton compact onClick={() => exportRouteLatencyCsv(data.api_latency_by_route)} />}
        >
          <RouteLatencyChart
            data={data.api_latency_by_route.map((row) => ({
              route: row.route,
              avgMs: row.avg_duration_ms,
              p95Ms: row.p95_duration_ms,
            }))}
          />
        </ChartCard>

        <ChartCard title="RAG performance" subtitle="Chat pipeline metrics">
          <UsageBarChart
            data={[
              { name: "Requests", value: data.chat.total_requests },
              { name: "Errors", value: data.chat.error_count },
              { name: "RAG ms", value: Math.round(data.chat.avg_rag_duration_ms ?? 0) },
              { name: "Retrieve ms", value: Math.round(data.chat.avg_retrieval_duration_ms ?? 0) },
            ]}
            name="Value"
            color="#7c3aed"
          />
          <div className="mt-4 grid grid-cols-2 gap-3 rounded-xl bg-[var(--admin-surface)] p-4 text-sm">
            <div>
              <p className="text-[11px] uppercase tracking-wide text-[var(--admin-muted)]">Error rate</p>
              <p className="mt-1 text-lg font-bold text-[var(--admin-text)]">{formatPercent(data.chat.error_rate)}</p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-[var(--admin-muted)]">API samples</p>
              <p className="mt-1 text-lg font-bold text-[var(--admin-text)]">{formatNumber(data.api_request_samples)}</p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-[var(--admin-muted)]">Proc. fail rate</p>
              <p className="mt-1 text-lg font-bold text-[var(--admin-text)]">{formatPercent(data.processing_failure_rate)}</p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-[var(--admin-muted)]">Avg processing</p>
              <p className="mt-1 text-lg font-bold text-[var(--admin-text)]">{formatMs(data.avg_processing_duration_ms)}</p>
            </div>
          </div>
        </ChartCard>

        <ChartCard title="Stage timing" subtitle="Average duration per pipeline stage" className="xl:col-span-2">
          <StageDurationChart data={data.stage_avg_duration_ms.map((row) => ({ stage: row.stage, avgMs: row.avg_duration_ms }))} />
        </ChartCard>
      </div>
    </div>
  );
}
