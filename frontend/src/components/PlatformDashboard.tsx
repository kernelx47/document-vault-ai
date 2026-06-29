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
  Download,
  FileStack,
  Gauge,
  LayoutDashboard,
  Loader2,
  Moon,
  RefreshCw,
  Sun,
} from "lucide-react";
import { PlatformMetricsSnapshot, getPlatformMetricsSnapshot } from "@/lib/api";
import {
  DocumentsPanel,
  OverviewPanel,
  ProcessingPanel,
  StoragePanel,
  SystemPanel,
  UsagePanel,
} from "./platform/Panels";
import { exportPlatformSnapshotCsv } from "./platform/export";
import { useAdminTheme } from "./platform/useAdminTheme";

type PlatformSection = "overview" | "usage" | "documents" | "processing" | "storage" | "system";

const NAV_ITEMS: { id: PlatformSection; label: string; icon: typeof Gauge; description: string }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard, description: "Executive summary" },
  { id: "usage", label: "Usage", icon: Gauge, description: "AI tokens & cost" },
  { id: "documents", label: "Documents", icon: FileStack, description: "Vault inventory" },
  { id: "processing", label: "Processing", icon: Cpu, description: "Ingestion pipeline" },
  { id: "storage", label: "Storage", icon: Database, description: "Data footprint" },
  { id: "system", label: "System", icon: Activity, description: "Performance" },
];

const SECTION_META: Record<PlatformSection, { title: string; breadcrumb: string }> = {
  overview: { title: "Overview", breadcrumb: "Dashboard" },
  usage: { title: "Usage", breadcrumb: "AI Usage" },
  documents: { title: "Documents", breadcrumb: "Document Stats" },
  processing: { title: "Processing", breadcrumb: "Pipeline Metrics" },
  storage: { title: "Storage", breadcrumb: "Data Storage" },
  system: { title: "System", breadcrumb: "Performance" },
};

export default function PlatformDashboard() {
  const { theme, toggleTheme, mounted } = useAdminTheme();
  const [section, setSection] = useState<PlatformSection>("overview");
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

  const meta = SECTION_META[section];

  return (
    <div className="admin-shell flex h-screen w-screen overflow-hidden" data-theme={mounted ? theme : "light"}>
      <aside className="admin-sidebar relative flex w-[260px] shrink-0 flex-col overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(124,58,237,0.18),transparent_55%)]" />

        <div className="relative border-b border-white/10 px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-violet-700 shadow-lg shadow-violet-900/40">
              <BarChart3 className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Admin Console</p>
              <p className="text-[11px] text-violet-200/70">VaultMind</p>
            </div>
          </div>
        </div>

        <nav className="relative flex-1 overflow-y-auto px-3 py-4">
          <p className="px-3 pb-2 text-[10px] font-bold uppercase tracking-[0.12em] text-violet-300/50">Analytics</p>
          {NAV_ITEMS.map(({ id, label, icon: Icon, description }) => (
            <button
              key={id}
              type="button"
              onClick={() => setSection(id)}
              className={clsx(
                "group mb-1 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-all duration-200",
                section === id
                  ? "bg-white/10 text-white shadow-inner shadow-white/5 ring-1 ring-white/10"
                  : "text-violet-100/70 hover:bg-white/5 hover:text-white",
              )}
            >
              <div
                className={clsx(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-colors",
                  section === id ? "bg-violet-500/30 text-violet-100" : "bg-white/5 text-violet-200/60 group-hover:bg-white/10",
                )}
              >
                <Icon className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-[13px] font-medium leading-tight">{label}</p>
                <p className="truncate text-[10px] text-violet-200/45">{description}</p>
              </div>
            </button>
          ))}
        </nav>

        <div className="relative space-y-1 border-t border-white/10 p-3">
          <button
            type="button"
            onClick={toggleTheme}
            className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-[13px] text-violet-100/70 transition-colors hover:bg-white/5 hover:text-white"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </button>
          <Link
            href="/"
            className="flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-[13px] text-violet-100/70 transition-colors hover:bg-white/5 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to chat
          </Link>
        </div>
      </aside>

      <main className="admin-main relative flex min-w-0 flex-1 flex-col">
        <div className="pointer-events-none absolute inset-0 admin-grid-bg opacity-60" />

        <header className="relative z-10 flex h-16 shrink-0 items-center justify-between border-b border-[var(--admin-border)] bg-[var(--admin-header)] px-8 backdrop-blur-xl">
          <div>
            <div className="flex items-center gap-2 text-xs text-[var(--admin-muted)]">
              <span>Platform</span>
              <span>/</span>
              <span className="font-medium">{meta.breadcrumb}</span>
            </div>
            <div className="mt-0.5 flex items-center gap-3">
              <h2 className="text-lg font-semibold text-[var(--admin-text)]">{meta.title}</h2>
              <span className="admin-live-pulse inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Live
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            {lastUpdated && (
              <p className="hidden text-[11px] text-[var(--admin-muted)] lg:block">
                Updated {lastUpdated.toLocaleTimeString()} · auto 30s
              </p>
            )}
            {data && (
              <button
                type="button"
                onClick={() => exportPlatformSnapshotCsv(data)}
                className="hidden items-center gap-2 rounded-xl border border-[var(--admin-border)] bg-[var(--admin-card)] px-3 py-2 text-xs font-semibold text-[var(--admin-muted)] shadow-sm transition-all hover:border-violet-400 hover:text-violet-600 sm:flex"
              >
                <Download className="h-3.5 w-3.5" />
                Export snapshot
              </button>
            )}
            <button
              type="button"
              onClick={toggleTheme}
              className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--admin-border)] bg-[var(--admin-card)] text-[var(--admin-muted)] transition-all hover:border-violet-400 hover:text-violet-600 lg:hidden"
              title="Toggle theme"
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <button
              type="button"
              onClick={() => void loadMetrics(true)}
              disabled={refreshing}
              className="flex items-center gap-2 rounded-xl border border-[var(--admin-border)] bg-[var(--admin-card)] px-4 py-2 text-xs font-semibold text-[var(--admin-muted)] shadow-sm transition-all hover:border-violet-400 hover:text-violet-700 hover:shadow-md disabled:opacity-60"
            >
              {refreshing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              Refresh
            </button>
          </div>
        </header>

        <div className="relative z-10 flex-1 overflow-y-auto px-8 py-8">
          {loading && !data ? (
            <div className="flex h-full flex-col items-center justify-center gap-4">
              <div className="relative">
                <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-violet-500 to-violet-700 opacity-20" />
                <Loader2 className="absolute inset-0 m-auto h-7 w-7 animate-spin text-violet-600" />
              </div>
              <p className="text-sm font-medium text-[var(--admin-muted)]">Loading analytics…</p>
            </div>
          ) : error && !data ? (
            <div className="mx-auto max-w-md rounded-2xl border border-red-200 bg-[var(--admin-card)] p-8 text-center shadow-xl">
              <p className="text-sm text-[var(--danger)]">{error}</p>
              <button
                type="button"
                onClick={() => void loadMetrics()}
                className="mt-4 rounded-xl bg-gradient-to-r from-violet-600 to-violet-700 px-5 py-2 text-sm font-semibold text-white shadow-lg shadow-violet-500/25"
              >
                Retry
              </button>
            </div>
          ) : data ? (
            <div className="admin-content-enter mx-auto max-w-[1400px]">
              {error && (
                <p className="mb-6 rounded-xl border border-red-200 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-400">
                  Refresh failed: {error}
                </p>
              )}
              {section === "overview" && <OverviewPanel data={data} />}
              {section === "usage" && <UsagePanel data={data.aiUsage} timeseries={data.timeseries} />}
              {section === "documents" && <DocumentsPanel data={data.documents} />}
              {section === "processing" && (
                <ProcessingPanel metrics={data.processing} history={data.processingHistory} />
              )}
              {section === "storage" && <StoragePanel data={data.storage} />}
              {section === "system" && <SystemPanel data={data.system} timeseries={data.timeseries} />}
            </div>
          ) : null}
        </div>
      </main>
    </div>
  );
}
