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
  created_at: string;
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
): Promise<void> {
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
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function getChatHistory(sessionId: string) {
  const response = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages`, {
    cache: "no-store",
  });
  return parseJson<{ messages: ChatMessage[] }>(response);
}
