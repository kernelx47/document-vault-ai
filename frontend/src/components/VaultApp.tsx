"use client";

import { useEffect, useMemo, useState } from "react";

import {
  ChatMessage,
  createChatSession,
  DocumentSummary,
  getChatHistory,
  getDocumentStatus,
  listDocuments,
  sendChatMessage,
  streamChatMessage,
  uploadDocument,
} from "@/lib/api";

type UiMessage = ChatMessage & { streaming?: boolean };

export default function VaultApp() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const readyDocuments = useMemo(
    () => documents.filter((document) => document.status === "ready"),
    [documents],
  );

  async function refreshDocuments() {
    try {
      const response = await listDocuments();
      setDocuments(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    }
  }

  useEffect(() => {
    void refreshDocuments();
    const interval = window.setInterval(() => {
      void refreshDocuments();
    }, 5000);
    return () => window.clearInterval(interval);
  }, []);

  async function handleUpload(file: File) {
    setUploading(true);
    setError(null);
    try {
      const uploaded = await uploadDocument(file);
      await refreshDocuments();
      setSelectedIds([uploaded.id]);
      const poll = window.setInterval(async () => {
        const status = await getDocumentStatus(uploaded.id);
        if (status.status === "ready" || status.status === "failed") {
          window.clearInterval(poll);
          await refreshDocuments();
        }
      }, 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  function toggleDocument(documentId: string) {
    setSelectedIds((current) =>
      current.includes(documentId)
        ? current.filter((id) => id !== documentId)
        : [...current, documentId],
    );
  }

  async function ensureSession() {
    if (sessionId) return sessionId;
    if (selectedIds.length === 0) {
      throw new Error("Select at least one ready document.");
    }
    const session = await createChatSession(selectedIds);
    setSessionId(session.id);
    return session.id;
  }

  async function handleAsk(useStream: boolean) {
    if (!question.trim()) return;
    setLoading(true);
    setStreaming(useStream);
    setError(null);
    try {
      const activeSessionId = await ensureSession();
      const userMessage: UiMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: question.trim(),
        citations: [],
        suggested_followups: [],
        created_at: new Date().toISOString(),
      };
      setMessages((current) => [...current, userMessage]);
      setQuestion("");

      if (useStream) {
        const assistantId = crypto.randomUUID();
        setMessages((current) => [
          ...current,
          {
            id: assistantId,
            role: "assistant",
            content: "",
            citations: [],
            suggested_followups: [],
            created_at: new Date().toISOString(),
            streaming: true,
          },
        ]);
        await streamChatMessage(activeSessionId, userMessage.content, (token) => {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? { ...message, content: message.content + token }
                : message,
            ),
          );
        });
        const history = await getChatHistory(activeSessionId);
        setMessages(history.messages);
      } else {
        await sendChatMessage(activeSessionId, userMessage.content);
        const history = await getChatHistory(activeSessionId);
        setMessages(history.messages);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat request failed");
    } finally {
      setLoading(false);
      setStreaming(false);
    }
  }

  return (
    <main className="mx-auto grid min-h-screen max-w-6xl gap-6 px-6 py-10 lg:grid-cols-[1fr_1.2fr]">
      <section className="space-y-6">
        <header className="space-y-2">
          <p className="text-sm uppercase tracking-widest text-slate-400">Document Vault AI</p>
          <h1 className="text-3xl font-semibold">Upload. Process. Chat.</h1>
          <p className="text-slate-300">
            Select one or more ready documents and ask questions with citations.
          </p>
        </header>

        <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-5">
          <h2 className="mb-3 font-medium">Upload</h2>
          <input
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            disabled={uploading}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void handleUpload(file);
            }}
            className="block w-full text-sm text-slate-300"
          />
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-medium">Documents</h2>
            <button
              type="button"
              onClick={() => void refreshDocuments()}
              className="text-sm text-sky-400 hover:text-sky-300"
            >
              Refresh
            </button>
          </div>
          <div className="space-y-2">
            {documents.length === 0 && (
              <p className="text-sm text-slate-400">No documents yet. Upload a PDF or DOCX.</p>
            )}
            {documents.map((document) => (
              <label
                key={document.id}
                className="flex cursor-pointer items-center justify-between rounded-lg border border-slate-700 px-3 py-2"
              >
                <div>
                  <p className="font-medium">{document.filename}</p>
                  <p className="text-xs text-slate-400">{document.status}</p>
                </div>
                <input
                  type="checkbox"
                  checked={selectedIds.includes(document.id)}
                  disabled={document.status !== "ready"}
                  onChange={() => toggleDocument(document.id)}
                />
              </label>
            ))}
          </div>
          <p className="mt-3 text-xs text-slate-400">
            {readyDocuments.length} ready · {selectedIds.length} selected
          </p>
        </div>
      </section>

      <section className="flex min-h-[70vh] flex-col rounded-xl border border-slate-700 bg-slate-900/60 p-5">
        <h2 className="mb-4 font-medium">Chat</h2>
        {error && <p className="mb-3 text-sm text-amber-400">{error}</p>}
        <div className="flex-1 space-y-4 overflow-y-auto pr-2">
          {messages.length === 0 && (
            <p className="text-sm text-slate-400">
              Select ready documents, then ask a question. Try streaming for live tokens.
            </p>
          )}
          {messages.map((message) => (
            <div
              key={message.id}
              className={`rounded-lg px-4 py-3 ${
                message.role === "user" ? "bg-sky-950/70" : "bg-slate-800/80"
              }`}
            >
              <p className="mb-1 text-xs uppercase tracking-wide text-slate-400">{message.role}</p>
              <p className="whitespace-pre-wrap text-sm">{message.content}</p>
              {message.citations?.length > 0 && (
                <div className="mt-3 space-y-2">
                  {message.citations.map((citation) => (
                    <div key={citation.chunk_id} className="rounded border border-slate-700 p-2 text-xs">
                      <p className="text-slate-400">Page {citation.page_number ?? "?"} · score {citation.score}</p>
                      <p>{citation.excerpt}</p>
                    </div>
                  ))}
                </div>
              )}
              {message.suggested_followups?.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {message.suggested_followups.map((followup) => (
                    <button
                      key={followup}
                      type="button"
                      onClick={() => setQuestion(followup)}
                      className="rounded-full border border-slate-600 px-3 py-1 text-xs hover:border-sky-500"
                    >
                      {followup}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="mt-4 space-y-3 border-t border-slate-700 pt-4">
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask about your selected documents..."
            className="min-h-[96px] w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          />
          <div className="flex gap-3">
            <button
              type="button"
              disabled={loading || selectedIds.length === 0}
              onClick={() => void handleAsk(false)}
              className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
            >
              Ask
            </button>
            <button
              type="button"
              disabled={loading || selectedIds.length === 0}
              onClick={() => void handleAsk(true)}
              className="rounded-lg border border-sky-500 px-4 py-2 text-sm font-medium disabled:opacity-50"
            >
              {streaming ? "Streaming..." : "Stream"}
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
