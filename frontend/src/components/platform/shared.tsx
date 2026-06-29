import clsx from "clsx";
import type { LucideIcon } from "lucide-react";
import { Sparkline } from "./Sparkline";

export const STATUS_COLORS = {
  ready: "#16a34a",
  processing: "#ca8a04",
  pending: "#676b89",
  failed: "#ef4444",
  completed: "#16a34a",
  started: "#ca8a04",
} as const;

export const CHART_COLORS = [
  "#7c3aed",
  "#8b5cf6",
  "#a78bfa",
  "#16a34a",
  "#ca8a04",
  "#ef4444",
  "#676b89",
  "#06b6d4",
] as const;

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export function formatMs(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

export function formatPercent(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

export function formatUsd(amount: number): string {
  if (amount < 0.01) return `$${amount.toFixed(4)}`;
  return `$${amount.toFixed(2)}`;
}

export function formatNumber(value: number): string {
  return value.toLocaleString();
}

export function formatCompact(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return String(value);
}

export function ChartCard({
  title,
  subtitle,
  children,
  className,
  action,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
  action?: React.ReactNode;
}) {
  return (
    <div
      className={clsx(
        "admin-chart-card rounded-2xl border p-5 shadow-[0_8px_30px_rgb(40_25_80_/_6%)] backdrop-blur-sm",
        "border-[var(--admin-border)] bg-[var(--admin-card)]",
        className,
      )}
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-[var(--admin-text)]">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-[var(--admin-muted)]">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  gradient = "violet",
  large,
  sparkline,
  sparklineColor = "#7c3aed",
}: {
  label: string;
  value: string;
  hint?: string;
  icon: LucideIcon;
  gradient?: "violet" | "green" | "amber" | "cyan" | "rose";
  large?: boolean;
  sparkline?: number[];
  sparklineColor?: string;
}) {
  const gradients = {
    violet: "from-violet-500/15 to-violet-600/5 border-violet-200/60 dark:from-violet-500/20 dark:to-violet-900/10 dark:border-violet-500/20",
    green: "from-emerald-500/15 to-emerald-600/5 border-emerald-200/60 dark:from-emerald-500/20 dark:to-emerald-900/10 dark:border-emerald-500/20",
    amber: "from-amber-500/15 to-amber-600/5 border-amber-200/60 dark:from-amber-500/20 dark:to-amber-900/10 dark:border-amber-500/20",
    cyan: "from-cyan-500/15 to-cyan-600/5 border-cyan-200/60 dark:from-cyan-500/20 dark:to-cyan-900/10 dark:border-cyan-500/20",
    rose: "from-rose-500/15 to-rose-600/5 border-rose-200/60 dark:from-rose-500/20 dark:to-rose-900/10 dark:border-rose-500/20",
  };

  const iconColors = {
    violet: "bg-violet-600 text-white shadow-violet-500/30",
    green: "bg-emerald-600 text-white shadow-emerald-500/30",
    amber: "bg-amber-500 text-white shadow-amber-500/30",
    cyan: "bg-cyan-600 text-white shadow-cyan-500/30",
    rose: "bg-rose-500 text-white shadow-rose-500/30",
  };

  return (
    <div
      className={clsx(
        "admin-stat-card relative overflow-hidden rounded-2xl border bg-gradient-to-br p-5 shadow-[0_8px_30px_rgb(40_25_80_/_5%)]",
        "bg-[var(--admin-card)]",
        gradients[gradient],
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--admin-muted)]">{label}</p>
          <p
            className={clsx(
              "mt-2 font-bold tracking-tight text-[var(--admin-text)]",
              large ? "text-3xl" : "text-2xl",
            )}
          >
            {value}
          </p>
          {hint && <p className="mt-1.5 text-xs text-[var(--admin-muted)]">{hint}</p>}
          {sparkline && sparkline.length >= 2 && <Sparkline data={sparkline} color={sparklineColor} />}
        </div>
        <div className={clsx("flex h-10 w-10 shrink-0 items-center justify-center rounded-xl shadow-lg", iconColors[gradient])}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

export function SectionHeader({ title, description }: { title: string; description: string }) {
  return (
    <div className="mb-6">
      <h1
        className="text-3xl font-semibold tracking-[-0.03em] text-[var(--admin-text)]"
        style={{ fontFamily: "'Source Serif 4', serif" }}
      >
        {title}
      </h1>
      <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-[var(--admin-muted)]">{description}</p>
    </div>
  );
}

export function EmptyChart({ message }: { message: string }) {
  return (
    <div className="flex h-[220px] flex-col items-center justify-center rounded-xl border border-dashed border-[var(--admin-border)] bg-[var(--admin-surface)] text-center">
      <div className="mb-2 h-12 w-12 rounded-full bg-[var(--admin-border)]/80" />
      <p className="text-sm text-[var(--admin-muted)]">{message}</p>
    </div>
  );
}
