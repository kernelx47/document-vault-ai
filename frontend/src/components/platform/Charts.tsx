"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ProcessingHistory } from "@/lib/api";
import { CHART_COLORS, EmptyChart, formatCompact, formatMs, formatNumber, formatUsd, STATUS_COLORS } from "./shared";

type ChartTooltipProps = {
  active?: boolean;
  payload?: Array<{ name?: string; value?: number; color?: string; payload?: Record<string, unknown> }>;
  label?: string;
};

function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-[var(--lavender-mist)] bg-white/95 px-3 py-2 shadow-xl backdrop-blur-sm">
      {label && <p className="mb-1 text-[11px] font-medium text-[var(--overcast)]">{label}</p>}
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-[var(--heather)]">{entry.name}:</span>
          <span className="font-semibold text-[var(--deep-ink)]">{entry.value}</span>
        </div>
      ))}
    </div>
  );
}

export function DonutChart({
  data,
  emptyMessage = "No data yet",
}: {
  data: { name: string; value: number; color?: string }[];
  emptyMessage?: string;
}) {
  const filtered = data.filter((d) => d.value > 0);
  if (filtered.length === 0) return <EmptyChart message={emptyMessage} />;

  const total = filtered.reduce((sum, d) => sum + d.value, 0);

  return (
    <div className="flex flex-col items-center gap-4 lg:flex-row">
      <div className="h-[220px] w-full lg:w-[55%]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={filtered}
              cx="50%"
              cy="50%"
              innerRadius={62}
              outerRadius={88}
              paddingAngle={3}
              dataKey="value"
              stroke="none"
            >
              {filtered.map((entry, index) => (
                <Cell key={entry.name} fill={entry.color ?? CHART_COLORS[index % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip content={<ChartTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="w-full flex-1 space-y-2.5">
        {filtered.map((entry, index) => {
          const pct = total > 0 ? (entry.value / total) * 100 : 0;
          return (
            <div key={entry.name}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="flex items-center gap-2 font-medium text-[var(--deep-ink)]">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: entry.color ?? CHART_COLORS[index % CHART_COLORS.length] }}
                  />
                  {entry.name}
                </span>
                <span className="text-[var(--overcast)]">
                  {formatNumber(entry.value)} · {pct.toFixed(0)}%
                </span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-[var(--lavender-mist)]">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${pct}%`,
                    backgroundColor: entry.color ?? CHART_COLORS[index % CHART_COLORS.length],
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function StageBarChart({
  data,
}: {
  data: { stage: string; completed: number; failed: number; avgMs: number | null }[];
}) {
  if (data.length === 0) return <EmptyChart message="No pipeline stages recorded yet." />;

  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} barGap={4} barCategoryGap="20%">
          <CartesianGrid strokeDasharray="3 3" stroke="#e7e6f4" vertical={false} />
          <XAxis dataKey="stage" tick={{ fill: "#676b89", fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#676b89", fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip content={<ChartTooltip />} />
          <Legend wrapperStyle={{ fontSize: 12, color: "#676b89" }} />
          <Bar dataKey="completed" name="Completed" fill="#16a34a" radius={[6, 6, 0, 0]} />
          <Bar dataKey="failed" name="Failed" fill="#ef4444" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function StageDurationChart({
  data,
}: {
  data: { stage: string; avgMs: number | null }[];
}) {
  const chartData = data
    .filter((d) => d.avgMs != null && d.avgMs > 0)
    .map((d) => ({ stage: d.stage, duration: Math.round(d.avgMs ?? 0) }));

  if (chartData.length === 0) return <EmptyChart message="No stage timing data yet." />;

  return (
    <div className="h-[220px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e7e6f4" horizontal={false} />
          <XAxis type="number" tick={{ fill: "#676b89", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => formatMs(v)} />
          <YAxis type="category" dataKey="stage" width={72} tick={{ fill: "#676b89", fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              return (
                <div className="rounded-xl border bg-white px-3 py-2 text-xs shadow-xl">
                  <span className="font-semibold text-[var(--deep-ink)]">{formatMs(payload[0].value as number)}</span>
                </div>
              );
            }}
          />
          <Bar dataKey="duration" name="Avg duration" fill="#7c3aed" radius={[0, 6, 6, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function UsageBarChart({
  data,
  dataKey,
  name,
  color = "#7c3aed",
}: {
  data: { name: string; value: number }[];
  dataKey?: string;
  name: string;
  color?: string;
}) {
  if (data.length === 0) return <EmptyChart message="No usage data yet." />;

  return (
    <div className="h-[240px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e7e6f4" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: "#676b89", fontSize: 10 }} axisLine={false} tickLine={false} interval={0} angle={-20} textAnchor="end" height={50} />
          <YAxis tick={{ fill: "#676b89", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={formatCompact} />
          <Tooltip content={<ChartTooltip />} />
          <Bar dataKey={dataKey ?? "value"} name={name} fill={color} radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function TokenSplitChart({ input, output }: { input: number; output: number }) {
  const data = [
    { name: "Input tokens", value: input, color: "#7c3aed" },
    { name: "Output tokens", value: output, color: "#a78bfa" },
  ].filter((d) => d.value > 0);

  if (data.length === 0) return <EmptyChart message="No token usage yet." />;
  return <DonutChart data={data} />;
}

export function QuotaRadialChart({ used, total }: { used: number; total: number }) {
  if (total <= 0) return <EmptyChart message="No daily quota configured." />;

  const pct = Math.min(100, Math.round((used / total) * 100));
  const chartData = [{ name: "Used", value: pct, fill: pct > 85 ? "#ef4444" : pct > 65 ? "#ca8a04" : "#7c3aed" }];

  return (
    <div className="relative h-[220px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart cx="50%" cy="50%" innerRadius="68%" outerRadius="100%" barSize={14} data={chartData} startAngle={90} endAngle={-270}>
          <RadialBar background={{ fill: "#e7e6f4" }} dataKey="value" cornerRadius={8} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold text-[var(--deep-ink)]">{pct}%</span>
        <span className="text-xs text-[var(--overcast)]">
          {formatNumber(used)} / {formatNumber(total)}
        </span>
      </div>
    </div>
  );
}

export function StorageBreakdownChart({
  fileBytes,
  chatSessions,
  chatMessages,
  chunks,
}: {
  fileBytes: number;
  chatSessions: number;
  chatMessages: number;
  chunks: number;
}) {
  const data = [
    { name: "Files (MB)", value: Math.round(fileBytes / (1024 * 1024) * 10) / 10 },
    { name: "Chunks", value: chunks },
    { name: "Sessions", value: chatSessions },
    { name: "Messages", value: chatMessages },
  ].filter((d) => d.value > 0);

  if (data.length === 0) return <EmptyChart message="No storage data yet." />;

  return (
    <div className="h-[240px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e7e6f4" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: "#676b89", fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#676b89", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={formatCompact} />
          <Tooltip content={<ChartTooltip />} />
          <Bar dataKey="value" name="Count" radius={[8, 8, 0, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function RouteLatencyChart({
  data,
}: {
  data: { route: string; avgMs: number | null; p95Ms: number | null }[];
}) {
  const chartData = data
    .filter((d) => d.avgMs != null)
    .slice(0, 8)
    .map((d) => ({
      route: d.route.replace("/api/v1/", "").slice(0, 28),
      avg: Math.round(d.avgMs ?? 0),
      p95: Math.round(d.p95Ms ?? 0),
    }));

  if (chartData.length === 0) return <EmptyChart message="No latency samples yet." />;

  return (
    <div className="h-[280px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ left: 4, right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e7e6f4" horizontal={false} />
          <XAxis type="number" tick={{ fill: "#676b89", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => formatMs(v)} />
          <YAxis type="category" dataKey="route" width={120} tick={{ fill: "#676b89", fontSize: 10 }} axisLine={false} tickLine={false} />
          <Tooltip content={<ChartTooltip />} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="avg" name="Avg" fill="#7c3aed" radius={[0, 4, 4, 0]} />
          <Bar dataKey="p95" name="P95" fill="#a78bfa" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ProcessingTimelineChart({ history }: { history: ProcessingHistory }) {
  const buckets = new Map<string, { completed: number; failed: number }>();

  for (const job of history.items) {
    const hour = new Date(job.created_at);
    hour.setMinutes(0, 0, 0);
    const key = hour.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric" });
    const bucket = buckets.get(key) ?? { completed: 0, failed: 0 };
    if (job.status === "failed") bucket.failed += 1;
    else if (job.status === "completed") bucket.completed += 1;
    buckets.set(key, bucket);
  }

  const chartData = Array.from(buckets.entries())
    .map(([time, counts]) => ({ time, ...counts, total: counts.completed + counts.failed }))
    .reverse()
    .slice(-12);

  if (chartData.length === 0) return <EmptyChart message="No recent job activity." />;

  return (
    <div className="h-[240px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="completedGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#16a34a" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#16a34a" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="failedGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ef4444" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e7e6f4" vertical={false} />
          <XAxis dataKey="time" tick={{ fill: "#676b89", fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#676b89", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
          <Tooltip content={<ChartTooltip />} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Area type="monotone" dataKey="completed" name="Completed" stroke="#16a34a" fill="url(#completedGrad)" strokeWidth={2} />
          <Area type="monotone" dataKey="failed" name="Failed" stroke="#ef4444" fill="url(#failedGrad)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function CostByOperationChart({
  data,
}: {
  data: { operation: string; cost: number; requests: number }[];
}) {
  const chartData = data
    .filter((d) => d.requests > 0)
    .map((d) => ({ name: d.operation, cost: Number(d.cost.toFixed(4)), requests: d.requests }));

  if (chartData.length === 0) return <EmptyChart message="No cost breakdown yet." />;

  return (
    <div className="h-[240px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e7e6f4" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: "#676b89", fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#676b89", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => formatUsd(v)} />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              return (
                <div className="rounded-xl border bg-white px-3 py-2 text-xs shadow-xl">
                  <p className="font-semibold text-[var(--deep-ink)]">{formatUsd(payload[0].value as number)}</p>
                  <p className="text-[var(--overcast)]">{formatNumber((payload[0].payload as { requests: number }).requests)} requests</p>
                </div>
              );
            }}
          />
          <Bar dataKey="cost" name="Est. cost" fill="#7c3aed" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function AIUsageTrendChart({
  data,
}: {
  data: { label: string; requests: number; tokens: number; cost_usd: number }[];
}) {
  if (data.length === 0) return <EmptyChart message="No AI activity in the selected window." />;

  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="aiReqGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#7c3aed" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="aiTokGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.25} />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e7e6f4" vertical={false} />
          <XAxis dataKey="label" tick={{ fill: "#676b89", fontSize: 10 }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
          <YAxis yAxisId="left" tick={{ fill: "#676b89", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
          <YAxis yAxisId="right" orientation="right" tick={{ fill: "#676b89", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={formatCompact} />
          <Tooltip content={<ChartTooltip />} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Area yAxisId="left" type="monotone" dataKey="requests" name="Requests" stroke="#7c3aed" fill="url(#aiReqGrad)" strokeWidth={2} />
          <Area yAxisId="right" type="monotone" dataKey="tokens" name="Tokens" stroke="#06b6d4" fill="url(#aiTokGrad)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LatencySparklineChart({ data }: { data: number[] }) {
  const chartData = data.map((value, index) => ({ index, value }));
  if (chartData.length < 2) return <EmptyChart message="Not enough latency samples yet." />;

  return (
    <div className="h-[220px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="latencyGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e7e6f4" vertical={false} />
          <XAxis dataKey="index" hide />
          <YAxis tick={{ fill: "#676b89", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => formatMs(v)} />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              return (
                <div className="rounded-xl border bg-white px-3 py-2 text-xs shadow-xl">
                  <span className="font-semibold">{formatMs(payload[0].value as number)}</span>
                </div>
              );
            }}
          />
          <Area type="monotone" dataKey="value" name="Latency" stroke="#f59e0b" fill="url(#latencyGrad)" strokeWidth={2} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
