"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import { BrandLogo } from "@/components/BrandLogo";
import {
  Activity,
  ArrowLeft,
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

const SECTION_META: Record<PlatformSection, { title: string; description: string }> = {
  overview: { title: "Overview", description: "High-level platform summary" },
  usage: { title: "Usage", description: "AI tokens, requests, and cost" },
  documents: { title: "Documents", description: "Vault inventory and status" },
  processing: { title: "Processing", description: "Ingestion pipeline metrics" },
  storage: { title: "Storage", description: "Files, chunks, and footprint" },
  system: { title: "System", description: "API latency and RAG health" },
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
    <div
      className="admin-shell flex h-screen w-screen overflow-hidden"
      data-theme={mounted ? theme : "light"}
    >
      <aside className="admin-sidebar flex w-[260px] shrink-0 flex-col overflow-hidden">
        <div className="flex items-center gap-2.5 border-b border-[var(--admin-border)] px-4 py-4">
          <BrandLogo size={36} />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-[var(--admin-text)]">VaultMind</p>
            <p className="text-[11px] text-[var(--admin-subtle)]">Insights</p>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-3">
          <p className="px-3 pb-1 text-[11px] font-medium uppercase tracking-[0.06em] text-[var(--admin-subtle)]">
            Analytics
          </p>
          {NAV_ITEMS.map(({ id, label, icon: Icon, description }) => (
            <button
              key={id}
              type="button"
              onClick={() => setSection(id)}
              className={clsx(
                "mb-0.5 flex w-full items-center gap-2.5 rounded-[var(--radius)] px-3 py-2 text-left transition-colors",
                section === id
                  ? "bg-[var(--admin-nav-active)] text-[var(--admin-text)]"
                  : "text-[var(--admin-muted)] hover:bg-[var(--admin-nav-hover)] hover:text-[var(--admin-text)]",
              )}
            >
              <Icon className="h-[18px] w-[18px] shrink-0 opacity-70" />
              <div className="min-w-0">
                <p className="truncate text-[14px] leading-tight">{label}</p>
                <p className="truncate text-[11px] text-[var(--admin-subtle)]">{description}</p>
              </div>
            </button>
          ))}
        </nav>

        <div className="space-y-0.5 border-t border-[var(--admin-border)] px-3 py-3">
          <button
            type="button"
            onClick={toggleTheme}
            className="flex w-full items-center gap-2 rounded-[var(--radius)] px-3 py-2 text-[14px] text-[var(--admin-muted)] transition-colors hover:bg-[var(--admin-nav-hover)] hover:text-[var(--admin-text)]"
          >
            {theme === "dark" ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </button>
          <Link
            href="/"
            className="flex items-center gap-2 rounded-[var(--radius)] px-3 py-2 text-[14px] text-[var(--admin-muted)] transition-colors hover:bg-[var(--admin-nav-hover)] hover:text-[var(--admin-text)]"
          >
            <ArrowLeft className="h-[18px] w-[18px]" />
            Back to chat
          </Link>
        </div>
      </aside>

      <main className="admin-main flex min-w-0 flex-1 flex-col">
        <header className="admin-header flex h-14 shrink-0 items-center justify-between gap-4 px-6">
          <div className="min-w-0">
            <h1
              className="truncate text-[15px] font-semibold tracking-[-0.01em] text-[var(--admin-text)]"
              style={{ fontFamily: "'Source Serif 4', serif" }}
            >
              {meta.title}
            </h1>
            <p className="mt-0.5 truncate text-xs text-[var(--admin-subtle)]">{meta.description}</p>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <span className="admin-live-pulse hidden items-center gap-1.5 rounded-full bg-[var(--admin-nav-active)] px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-[var(--admin-muted)] sm:inline-flex">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--success)]" />
              Live
            </span>
            {lastUpdated && (
              <p className="hidden text-[11px] text-[var(--admin-subtle)] xl:block">
                {lastUpdated.toLocaleTimeString()}
              </p>
            )}
            {data && (
              <button
                type="button"
                onClick={() => exportPlatformSnapshotCsv(data)}
                className="admin-btn hidden items-center gap-1.5 rounded-[var(--radius)] px-3 py-1.5 text-xs font-medium sm:flex"
              >
                <Download className="h-3.5 w-3.5" />
                Export
              </button>
            )}
            <button
              type="button"
              onClick={toggleTheme}
              className="admin-btn flex h-8 w-8 items-center justify-center rounded-[var(--radius)] lg:hidden"
              title={theme === "dark" ? "Light mode" : "Dark mode"}
            >
              {theme === "dark" ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
            </button>
            <button
              type="button"
              onClick={() => void loadMetrics(true)}
              disabled={refreshing}
              className="admin-btn flex items-center gap-1.5 rounded-[var(--radius)] px-3 py-1.5 text-xs font-medium disabled:opacity-60"
            >
              {refreshing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              Refresh
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          {loading && !data ? (
            <div className="flex h-full flex-col items-center justify-center gap-3">
              <Loader2 className="h-7 w-7 animate-spin text-[var(--electric-violet)]" />
              <p className="text-sm text-[var(--admin-subtle)]">Loading analytics…</p>
            </div>
          ) : error && !data ? (
            <div className="mx-auto max-w-md rounded-[var(--radius-lg)] border border-[var(--admin-border)] bg-[var(--admin-card)] p-8 text-center">
              <p className="text-sm text-[var(--danger)]">{error}</p>
              <button
                type="button"
                onClick={() => void loadMetrics()}
                className="mt-4 rounded-[var(--radius)] bg-[var(--electric-violet)] px-5 py-2 text-sm font-medium text-white hover:opacity-90"
              >
                Retry
              </button>
            </div>
          ) : data ? (
            <div className="admin-content-enter mx-auto max-w-[1400px]">
              {error && (
                <p className="mb-6 rounded-[var(--radius)] border border-red-200 bg-[var(--danger-bg)] px-4 py-3 text-sm text-[var(--danger)]">
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
