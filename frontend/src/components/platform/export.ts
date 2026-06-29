function escapeCsvCell(value: string | number | null | undefined): string {
  const text = value == null ? "" : String(value);
  if (/[",\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

export function downloadCsv(filename: string, headers: string[], rows: Array<Array<string | number | null | undefined>>) {
  const lines = [
    headers.map(escapeCsvCell).join(","),
    ...rows.map((row) => row.map(escapeCsvCell).join(",")),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function exportProcessingJobsCsv(
  items: Array<{
    id: string;
    document_id: string;
    stage: string;
    status: string;
    duration_ms: number | null;
    error_message: string | null;
    created_at: string;
  }>,
) {
  downloadCsv(
    `processing-jobs-${new Date().toISOString().slice(0, 10)}.csv`,
    ["id", "document_id", "stage", "status", "duration_ms", "error_message", "created_at"],
    items.map((job) => [
      job.id,
      job.document_id,
      job.stage,
      job.status,
      job.duration_ms,
      job.error_message,
      job.created_at,
    ]),
  );
}

export function exportAiUsageCsv(
  rows: Array<{
    operation: string;
    requests: number;
    input_tokens: number;
    output_tokens: number;
    estimated_cost_usd: number;
  }>,
) {
  downloadCsv(
    `ai-usage-by-operation-${new Date().toISOString().slice(0, 10)}.csv`,
    ["operation", "requests", "input_tokens", "output_tokens", "estimated_cost_usd"],
    rows.map((row) => [
      row.operation,
      row.requests,
      row.input_tokens,
      row.output_tokens,
      row.estimated_cost_usd,
    ]),
  );
}

export function exportRouteLatencyCsv(
  rows: Array<{
    route: string;
    avg_duration_ms: number | null;
    p95_duration_ms: number | null;
    sample_count: number;
  }>,
) {
  downloadCsv(
    `api-latency-by-route-${new Date().toISOString().slice(0, 10)}.csv`,
    ["route", "avg_duration_ms", "p95_duration_ms", "sample_count"],
    rows.map((row) => [row.route, row.avg_duration_ms, row.p95_duration_ms, row.sample_count]),
  );
}

export function exportPlatformSnapshotCsv(snapshot: {
  documents: { total: number; ready: number; failed: number; total_size_bytes: number; total_chunks: number };
  aiUsage: { total_requests: number; total_input_tokens: number; total_output_tokens: number; estimated_cost_usd: number };
  processing: { total_jobs: number; completed: number; failed: number; failure_rate: number };
  storage: { total_file_bytes: number; total_chunks: number; total_chat_sessions: number; total_chat_messages: number };
  system: { avg_api_latency_ms: number | null; worker_queue_depth: number; documents_per_hour: number };
}) {
  downloadCsv(
    `platform-snapshot-${new Date().toISOString().slice(0, 10)}.csv`,
    ["metric", "value"],
    [
      ["documents_total", snapshot.documents.total],
      ["documents_ready", snapshot.documents.ready],
      ["documents_failed", snapshot.documents.failed],
      ["documents_size_bytes", snapshot.documents.total_size_bytes],
      ["documents_chunks", snapshot.documents.total_chunks],
      ["ai_total_requests", snapshot.aiUsage.total_requests],
      ["ai_input_tokens", snapshot.aiUsage.total_input_tokens],
      ["ai_output_tokens", snapshot.aiUsage.total_output_tokens],
      ["ai_estimated_cost_usd", snapshot.aiUsage.estimated_cost_usd],
      ["processing_total_jobs", snapshot.processing.total_jobs],
      ["processing_completed", snapshot.processing.completed],
      ["processing_failed", snapshot.processing.failed],
      ["processing_failure_rate", snapshot.processing.failure_rate],
      ["storage_file_bytes", snapshot.storage.total_file_bytes],
      ["storage_chunks", snapshot.storage.total_chunks],
      ["storage_chat_sessions", snapshot.storage.total_chat_sessions],
      ["storage_chat_messages", snapshot.storage.total_chat_messages],
      ["system_avg_api_latency_ms", snapshot.system.avg_api_latency_ms],
      ["system_worker_queue_depth", snapshot.system.worker_queue_depth],
      ["system_documents_per_hour", snapshot.system.documents_per_hour],
    ],
  );
}
