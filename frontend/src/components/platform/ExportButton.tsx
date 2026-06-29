"use client";

import { Download } from "lucide-react";
import clsx from "clsx";

export function ExportButton({
  onClick,
  label = "Export CSV",
  compact,
}: {
  onClick: () => void;
  label?: string;
  compact?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-lg border text-xs font-semibold transition-all",
        compact
          ? "border-[var(--admin-border)] bg-[var(--admin-card)] px-2.5 py-1 text-[var(--admin-muted)] hover:border-violet-400 hover:text-violet-600"
          : "border-[var(--admin-border)] bg-[var(--admin-card)] px-3 py-1.5 text-[var(--admin-muted)] hover:border-violet-400 hover:text-violet-600 hover:shadow-sm",
      )}
    >
      <Download className="h-3.5 w-3.5" />
      {label}
    </button>
  );
}
