export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export type HealthResponse = {
  status: string;
  service: string;
  database?: string;
  redis?: string;
};

export type DocumentSummary = {
  id: string;
  filename: string;
  status: string;
  file_size_bytes: number;
  chunk_count: number;
  category?: string | null;
  tags?: string[];
  sentiment?: string | null;
  created_at: string;
};

export type DocumentInsights = {
  id: string;
  status: string;
  summary: string | null;
  insights: string[];
  category: string | null;
  tags: string[];
  sentiment: string | null;
};

export type SummaryLength = "brief" | "standard" | "detailed";
export type SummaryTone = "neutral" | "professional" | "executive" | "plain";

export type DocumentCompareResult = {
  summary: string;
  similarities: string[];
  differences: string[];
  comparison_table: Array<{ aspect: string; values: Record<string, string> }>;
  recommendation: string | null;
  document_filenames: Record<string, string>;
};

export type DocumentListResponse = {
  items: DocumentSummary[];
  total: number;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Array<{
    chunk_id: string;
    document_id?: string | null;
    document_filename?: string | null;
    page_number: number | null;
    excerpt: string;
    score: number;
    source_index?: number | null;
  }>;
  suggested_followups: string[];
  created_at: string;
};

export type ChatSession = {
  id: string;
  document_id: string;
  document_ids: string[];
  title: string | null;
};

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? "Request failed");
  }
  return response.json();
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  return parseJson(response);
}

export async function listDocuments(): Promise<DocumentListResponse> {
  const response = await fetch(`${API_BASE}/documents`, { cache: "no-store" });
  return parseJson(response);
}

export async function uploadDocument(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<{ id: string; filename: string; status: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/documents/upload`);

    if (onProgress) {
      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
      });
    }

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const err = JSON.parse(xhr.responseText);
          reject(new Error(err.detail ?? "Upload failed"));
        } catch {
          reject(new Error("Upload failed"));
        }
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error")));

    const formData = new FormData();
    formData.append("file", file);
    xhr.send(formData);
  });
}

export async function getDocumentStatus(documentId: string) {
  const response = await fetch(`${API_BASE}/documents/${documentId}/status`, {
    cache: "no-store",
  });
  return parseJson<{ id: string; status: string; error_message?: string | null }>(response);
}

export async function deleteDocument(documentId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/documents/${documentId}`, {
    method: "DELETE",
  });
  if (!response.ok && response.status !== 404) {
    throw new Error("Failed to delete document");
  }
}

export async function createChatSession(
  documentIds: string[],
  signal?: AbortSignal,
): Promise<ChatSession> {
  const response = await fetch(`${API_BASE}/chat/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_ids: documentIds }),
    signal,
  });
  return parseJson(response);
}

export async function sendChatMessage(sessionId: string, question: string): Promise<ChatMessage> {
  const response = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return parseJson(response);
}

export function isAbortError(err: unknown): boolean {
  return err instanceof DOMException && err.name === "AbortError";
}

export async function streamChatMessage(
  sessionId: string,
  question: string,
  onToken: (token: string) => void,
  signal?: AbortSignal,
): Promise<string | null> {
  const response = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });

  if (!response.ok || !response.body) {
    throw new Error("Streaming request failed");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let title: string | null = null;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = JSON.parse(line.slice(6));
        if (payload.token) onToken(payload.token);
        if (payload.done && payload.title) title = payload.title;
      }
    }
  } finally {
    reader.releaseLock();
  }

  return title;
}

export async function getDocumentInsights(documentId: string): Promise<DocumentInsights> {
  const response = await fetch(`${API_BASE}/documents/${documentId}/insights`, {
    cache: "no-store",
  });
  return parseJson(response);
}

export async function regenerateDocumentInsights(
  documentId: string,
  options: {
    length?: SummaryLength;
    tone?: SummaryTone;
    focus_areas?: string[];
  },
): Promise<DocumentInsights> {
  const response = await fetch(`${API_BASE}/documents/${documentId}/insights/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options),
  });
  return parseJson(response);
}

export async function compareDocuments(
  documentIds: string[],
  focus?: string,
): Promise<DocumentCompareResult> {
  const response = await fetch(`${API_BASE}/documents/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_ids: documentIds, focus: focus || null }),
  });
  return parseJson(response);
}

export async function getChatHistory(sessionId: string) {
  const response = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages`, {
    cache: "no-store",
  });
  return parseJson<{ session_id: string; title: string | null; messages: ChatMessage[] }>(response);
}

/* ─── Platform metrics ───────────────────────────────────────── */

export type DocumentMetrics = {
  total: number;
  pending: number;
  processing: number;
  ready: number;
  failed: number;
  total_size_bytes: number;
  total_chunks: number;
};

export type StageMetrics = {
  stage: string;
  completed: number;
  failed: number;
  avg_duration_ms: number | null;
};

export type ProcessingMetrics = {
  total_jobs: number;
  started: number;
  completed: number;
  failed: number;
  avg_duration_ms: number | null;
  failure_rate: number;
  by_stage: StageMetrics[];
};

export type ProcessingJobRecord = {
  id: string;
  document_id: string;
  stage: string;
  status: string;
  duration_ms: number | null;
  error_message: string | null;
  created_at: string;
};

export type ProcessingHistory = {
  items: ProcessingJobRecord[];
  total: number;
  limit: number;
  offset: number;
};

export type StorageMetrics = {
  total_file_bytes: number;
  filesystem_bytes: number | null;
  total_chunks: number;
  total_chat_sessions: number;
  total_chat_messages: number;
  embedding_dimension: number;
};

export type RouteLatencyMetrics = {
  route: string;
  avg_duration_ms: number | null;
  p95_duration_ms: number | null;
  sample_count: number;
};

export type ChatMetrics = {
  total_requests: number;
  error_count: number;
  error_rate: number;
  avg_rag_duration_ms: number | null;
  avg_retrieval_duration_ms: number | null;
};

export type SystemMetrics = {
  avg_api_latency_ms: number | null;
  p95_api_latency_ms: number | null;
  api_request_samples: number;
  api_latency_by_route: RouteLatencyMetrics[];
  worker_queue_depth: number;
  documents_per_hour: number;
  document_failure_rate: number;
  processing_failure_rate: number;
  avg_processing_duration_ms: number | null;
  stage_avg_duration_ms: StageMetrics[];
  chat: ChatMetrics;
};

export type AIUsageByOperation = {
  operation: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
};

export type AIUsageByProvider = {
  provider: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
};

export type AIUsageMetrics = {
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  estimated_cost_usd: number;
  daily_request_count: number;
  daily_request_quota: number | null;
  daily_quota_remaining: number | null;
  by_operation: AIUsageByOperation[];
  by_provider: AIUsageByProvider[];
};

export type PlatformMetricsSnapshot = {
  documents: DocumentMetrics;
  processing: ProcessingMetrics;
  processingHistory: ProcessingHistory;
  storage: StorageMetrics;
  system: SystemMetrics;
  aiUsage: AIUsageMetrics;
  timeseries: MetricsTimeseries;
};

export type AIUsageTimeSeriesPoint = {
  label: string;
  requests: number;
  tokens: number;
  cost_usd: number;
};

export type ProcessingTimeSeriesPoint = {
  label: string;
  completed: number;
  failed: number;
};

export type MetricsTimeseries = {
  ai_usage: AIUsageTimeSeriesPoint[];
  api_latency_ms: number[];
  processing_jobs: ProcessingTimeSeriesPoint[];
};

async function fetchMetrics<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}/metrics${path}`, { cache: "no-store" });
  return parseJson(response);
}

export async function getDocumentMetrics(): Promise<DocumentMetrics> {
  return fetchMetrics("/documents");
}

export async function getProcessingMetrics(): Promise<ProcessingMetrics> {
  return fetchMetrics("/processing");
}

export async function getProcessingHistory(limit = 20): Promise<ProcessingHistory> {
  return fetchMetrics(`/processing/history?limit=${limit}`);
}

export async function getStorageMetrics(): Promise<StorageMetrics> {
  return fetchMetrics("/storage");
}

export async function getSystemMetrics(): Promise<SystemMetrics> {
  return fetchMetrics("/system");
}

export async function getAIUsageMetrics(): Promise<AIUsageMetrics> {
  return fetchMetrics("/ai-usage");
}

export async function getMetricsTimeseries(hours = 24): Promise<MetricsTimeseries> {
  return fetchMetrics(`/timeseries?hours=${hours}`);
}

export async function getPlatformMetricsSnapshot(): Promise<PlatformMetricsSnapshot> {
  const [documents, processing, processingHistory, storage, system, aiUsage, timeseries] = await Promise.all([
    getDocumentMetrics(),
    getProcessingMetrics(),
    getProcessingHistory(50),
    getStorageMetrics(),
    getSystemMetrics(),
    getAIUsageMetrics(),
    getMetricsTimeseries(),
  ]);
  return { documents, processing, processingHistory, storage, system, aiUsage, timeseries };
}
