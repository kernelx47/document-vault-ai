"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import clsx from "clsx";
import {
  ChatMessage,
  compareDocuments,
  createChatSession,
  DocumentCompareResult,
  DocumentInsights,
  DocumentSummary,
  getChatHistory,
  getDocumentInsights,
  getDocumentStatus,
  isAbortError,
  listDocuments,
  regenerateDocumentInsights,
  streamChatMessage,
  SummaryLength,
  SummaryTone,
  uploadDocument,
} from "@/lib/api";

/* ─── Icons (1.5px stroke, violet family) ────────────────────── */

function IconSidebar({ className }: { className?: string }) {
  return (
    <svg className={className} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M9 3v18" />
    </svg>
  );
}

function IconNewChat({ className }: { className?: string }) {
  return (
    <svg className={className} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
    </svg>
  );
}

function IconSend({ className }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
    </svg>
  );
}

function IconPlus({ className }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

function IconX({ className }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  );
}

function IconTrash({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14z" />
    </svg>
  );
}

function IconFile({ className }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

function IconCheck({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function IconStop({ className }: { className?: string }) {
  return (
    <svg className={className} width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="6" width="12" height="12" rx="1.5" />
    </svg>
  );
}

function IconLoader({ className }: { className?: string }) {
  return (
    <svg className={clsx("animate-spin", className)} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M21 12a9 9 0 11-6.219-8.56" />
    </svg>
  );
}

function IconUpload({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
    </svg>
  );
}

function BrandLogo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="vaultGrad" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop stopColor="#7c3aed" />
          <stop offset="1" stopColor="#a855f7" />
        </linearGradient>
        <linearGradient id="sparkGrad" x1="16" y1="4" x2="16" y2="28" gradientUnits="userSpaceOnUse">
          <stop stopColor="#c4b5fd" />
          <stop offset="1" stopColor="#ffffff" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="28" height="28" rx="8" fill="url(#vaultGrad)" />
      <path d="M16 7L16 11M16 21L16 25M7 16H11M21 16H25" stroke="url(#sparkGrad)" strokeWidth="1.5" strokeLinecap="round" opacity="0.5" />
      <path d="M10 13.5C10 11.015 12.686 9 16 9s6 2.015 6 4.5V17c0 .552-.448 1-1 1H11c-.552 0-1-.448-1-1v-3.5z" fill="white" fillOpacity="0.9" />
      <rect x="14.5" y="13" width="3" height="3.5" rx="1.5" fill="url(#vaultGrad)" />
      <path d="M16 15.5V17" stroke="url(#vaultGrad)" strokeWidth="1.2" strokeLinecap="round" />
      <path d="M11 18h10v2.5a2.5 2.5 0 01-2.5 2.5h-5A2.5 2.5 0 0111 20.5V18z" fill="white" fillOpacity="0.25" />
      <circle cx="24" cy="8" r="3" fill="#facc15" />
      <path d="M24 6.5v1.5h1.5" stroke="#a16207" strokeWidth="0.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function AiAvatar() {
  return (
    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[var(--electric-violet)] to-purple-500 shadow-sm shadow-purple-300/40">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
        <path d="M12 3l-1.5 4.5L6 9l4.5 1.5L12 15l1.5-4.5L18 9l-4.5-1.5L12 3z" fill="white" />
        <path d="M6 16l-1 3 3-1 2.5-2.5L8.5 13.5 6 16z" fill="white" opacity="0.6" />
        <path d="M18 16l1 3-3-1-2.5-2.5 2-2L18 16z" fill="white" opacity="0.6" />
      </svg>
    </div>
  );
}

const THINKING_STAGES = [
  { text: "Searching documents", icon: "🔍" },
  { text: "Finding relevant passages", icon: "📄" },
  { text: "Cross-referencing sources", icon: "🔗" },
  { text: "Analyzing context", icon: "🧠" },
  { text: "Crafting response", icon: "✍️" },
  { text: "Double-checking citations", icon: "✅" },
] as const;

const DOT_COLORS = [
  "var(--electric-violet)",
  "#8b5cf6",
  "#a78bfa",
] as const;

function useThinkingStage(active: boolean) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!active) { setIndex(0); return; }
    const id = window.setInterval(
      () => setIndex((i) => (i + 1) % THINKING_STAGES.length),
      2400,
    );
    return () => window.clearInterval(id);
  }, [active]);

  return THINKING_STAGES[index];
}

function DancingDots({ size = 6 }: { size?: number }) {
  return (
    <>
      <style>{`@keyframes vault-dot-dance{0%,100%{transform:translateY(0) scale(1);opacity:.4}50%{transform:translateY(-5px) scale(1.15);opacity:1}}`}</style>
      <span className="inline-flex items-center gap-[3px]">
        {DOT_COLORS.map((color, i) => (
          <span
            key={i}
            style={{
              width: size,
              height: size,
              borderRadius: "50%",
              backgroundColor: color,
              display: "inline-block",
              animation: "vault-dot-dance 1.2s ease-in-out infinite",
              animationDelay: `${i * 0.15}s`,
            }}
          />
        ))}
      </span>
    </>
  );
}

function ThinkingIndicator() {
  const stage = useThinkingStage(true);
  return (
    <div className="flex items-start gap-3 mb-6">
      <div className="mt-1"><AiAvatar /></div>
      <div className="pt-1">
        <div className="flex items-center gap-2.5 rounded-2xl bg-[var(--iris-haze)] px-4 py-2.5">
          <span className="text-sm">{stage.icon}</span>
          <span className="text-[14px] font-medium text-[var(--heather)]">{stage.text}</span>
          <DancingDots size={5} />
        </div>
      </div>
    </div>
  );
}

function InlineThinkingBar() {
  const stage = useThinkingStage(true);
  return (
    <div className="flex items-center gap-2 text-[13px] text-[var(--heather)]">
      <span>{stage.icon}</span>
      <span className="font-medium">{stage.text}</span>
      <DancingDots size={4} />
    </div>
  );
}

function isAssistantPending(msg: UiMessage) {
  return msg.role === "assistant" && msg.streaming === true && msg.content.trim().length === 0;
}

function citationAnchorId(messageId: string, sourceIndex: number) {
  return `cite-${messageId}-${sourceIndex}`;
}

function linkifySourceCitations(content: string, messageId: string) {
  return content.replace(/\[Source\s+(\d+)\]/gi, (_match, index: string) => {
    return `[Source ${index}](#${citationAnchorId(messageId, Number(index))})`;
  });
}

function highlightCitation(anchorId: string) {
  const chip = document.getElementById(anchorId);
  if (!chip) return;
  chip.scrollIntoView({ behavior: "smooth", block: "nearest" });
  chip.classList.add("cite-highlight");
  window.setTimeout(() => chip.classList.remove("cite-highlight"), 1800);
}

function AssistantMessageBody({
  messageId,
  content,
  citations,
  streaming = false,
}: {
  messageId: string;
  content: string;
  citations: ChatMessage["citations"];
  streaming?: boolean;
}) {
  const [expandedSource, setExpandedSource] = useState<number | null>(null);
  const linkedContent = useMemo(() => linkifySourceCitations(content, messageId), [content, messageId]);

  const openCitation = useCallback((sourceIndex: number) => {
    setExpandedSource(sourceIndex);
    highlightCitation(citationAnchorId(messageId, sourceIndex));
  }, [messageId]);

  const markdownComponents = useMemo<Components>(() => ({
    a: ({ href, children, ...props }) => {
      if (href?.startsWith(`#cite-${messageId}-`)) {
        const sourceIndex = Number(href.slice(href.lastIndexOf("-") + 1));
        return (
          <button
            type="button"
            className="inline-source-citation"
            onClick={() => openCitation(sourceIndex)}
          >
            {children}
          </button>
        );
      }
      return (
        <a href={href} {...props} target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      );
    },
  }), [messageId, openCitation]);

  const expandedCitation = expandedSource != null
    ? citations.find((citation) => citation.source_index === expandedSource)
    : undefined;

  return (
    <>
      <div className="prose max-w-none text-[15px] leading-[1.7]">
        <ReactMarkdown components={markdownComponents}>{linkedContent}</ReactMarkdown>
        {streaming && <span className="inline-block align-middle ml-1"><DancingDots size={4} /></span>}
      </div>

      {citations.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {citations.map((c) => {
            const sourceIndex = c.source_index;
            const isExpanded = sourceIndex != null && expandedSource === sourceIndex;
            return (
              <button
                key={c.chunk_id}
                type="button"
                id={sourceIndex != null ? citationAnchorId(messageId, sourceIndex) : undefined}
                title={c.excerpt}
                onClick={() => sourceIndex != null && openCitation(sourceIndex)}
                className={clsx(
                  "citation-chip inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition-colors",
                  isExpanded
                    ? "border-[var(--electric-violet)] bg-[var(--iris-haze)] text-[var(--deep-ink)]"
                    : "border-[var(--lavender-mist)] bg-[var(--pure-paper)] text-[var(--overcast)] hover:border-[var(--electric-violet)]/40 hover:bg-[var(--iris-haze)]",
                )}
              >
                <span className="font-medium text-[var(--electric-violet)]">[{sourceIndex ?? "—"}]</span>
                {c.document_filename && (
                  <span className="max-w-[140px] truncate text-[var(--heather)]">{c.document_filename}</span>
                )}
                <span>p.{c.page_number ?? "—"} · {(c.score * 100).toFixed(0)}%</span>
              </button>
            );
          })}
        </div>
      )}

      {expandedCitation && (
        <div className="mt-2 rounded-[var(--radius)] border border-[var(--lavender-mist)] bg-[var(--iris-haze)] px-3 py-2 text-xs text-[var(--heather)]">
          <p className="mb-1 font-medium text-[var(--deep-ink)]">
            Source {expandedCitation.source_index}
            {expandedCitation.document_filename ? ` · ${expandedCitation.document_filename}` : ""}
            {expandedCitation.page_number != null ? ` · p.${expandedCitation.page_number}` : ""}
          </p>
          <p className="leading-relaxed">{expandedCitation.excerpt}</p>
        </div>
      )}
    </>
  );
}

/* ─── Types ──────────────────────────────────────────────────── */

type UiMessage = ChatMessage & { streaming?: boolean };

interface LocalSession {
  id: string;
  serverSessionId: string | null;
  title: string;
  messages: UiMessage[];
  createdAt: number;
}

interface UploadItem {
  file: File;
  progress: number;
  status: "pending" | "uploading" | "processing" | "done" | "error";
  docId?: string;
  error?: string;
}

/* ─── Helpers ────────────────────────────────────────────────── */

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function groupSessionsByDate(sessions: LocalSession[]) {
  const now = Date.now();
  const groups: { label: string; items: LocalSession[] }[] = [];
  const buckets: [string, number][] = [
    ["Today", 86_400_000],
    ["Yesterday", 172_800_000],
    ["Previous 7 Days", 604_800_000],
    ["Previous 30 Days", 2_592_000_000],
  ];
  let remaining = [...sessions];
  for (const [label, max] of buckets) {
    const match = remaining.filter((s) => now - s.createdAt < max);
    remaining = remaining.filter((s) => now - s.createdAt >= max);
    if (match.length) groups.push({ label, items: match });
  }
  if (remaining.length) groups.push({ label: "Older", items: remaining });
  return groups;
}

/* ─── Main Component ─────────────────────────────────────────── */

export default function VaultApp() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [sessions, setSessions] = useState<LocalSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [queuedCount, setQueuedCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [activeInsights, setActiveInsights] = useState<DocumentInsights | null>(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [summaryLength, setSummaryLength] = useState<SummaryLength>("standard");
  const [summaryTone, setSummaryTone] = useState<SummaryTone>("professional");
  const [focusAreas, setFocusAreas] = useState("");
  const [compareFocus, setCompareFocus] = useState("");
  const [comparing, setComparing] = useState(false);
  const [compareResult, setCompareResult] = useState<DocumentCompareResult | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const cancelledRef = useRef(false);
  const messageQueueRef = useRef<string[]>([]);
  const activeRequestRef = useRef<{ sessionId: string; assistantId: string } | null>(null);

  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeSessionId) ?? null,
    [sessions, activeSessionId],
  );
  const readyDocs = useMemo(() => documents.filter((d) => d.status === "ready"), [documents]);
  const sessionGroups = useMemo(() => groupSessionsByDate(sessions), [sessions]);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }, [question]);

  const refreshDocuments = useCallback(async () => {
    try { setDocuments((await listDocuments()).items); } catch { /* retry */ }
  }, []);

  useEffect(() => {
    void refreshDocuments();
    const iv = setInterval(() => void refreshDocuments(), 5000);
    return () => clearInterval(iv);
  }, [refreshDocuments]);

  async function loadDocumentInsights(documentId: string) {
    setActiveDocId(documentId);
    setInsightsLoading(true);
    setCompareResult(null);
    try {
      setActiveInsights(await getDocumentInsights(documentId));
    } catch {
      setActiveInsights(null);
    } finally {
      setInsightsLoading(false);
    }
  }

  function toggleDocSelection(documentId: string) {
    setSelectedDocIds((prev) =>
      prev.includes(documentId)
        ? prev.filter((id) => id !== documentId)
        : [...prev, documentId],
    );
  }

  async function handleRegenerateInsights() {
    if (!activeDocId) return;
    setRegenerating(true);
    setError(null);
    try {
      const focus = focusAreas
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
      setActiveInsights(
        await regenerateDocumentInsights(activeDocId, {
          length: summaryLength,
          tone: summaryTone,
          focus_areas: focus,
        }),
      );
      await refreshDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to regenerate insights");
    } finally {
      setRegenerating(false);
    }
  }

  async function handleCompareDocuments() {
    if (selectedDocIds.length < 2) return;
    setComparing(true);
    setError(null);
    try {
      setCompareResult(
        await compareDocuments(selectedDocIds, compareFocus.trim() || undefined),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Comparison failed");
    } finally {
      setComparing(false);
    }
  }

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeSession?.messages, sending]);

  /* ─── Upload ───────────────────────────────────────────────── */

  function addFiles(files: FileList | File[]) {
    const items: UploadItem[] = Array.from(files).map((f) => ({ file: f, progress: 0, status: "pending" }));
    setUploads((prev) => [...prev, ...items]);
    setShowUploadModal(true);
    for (const item of items) void processUpload(item);
  }

  async function processUpload(item: UploadItem) {
    setUploads((p) => p.map((u) => (u.file === item.file ? { ...u, status: "uploading" } : u)));
    try {
      const result = await uploadDocument(item.file, (pct) => {
        setUploads((p) => p.map((u) => (u.file === item.file ? { ...u, progress: pct } : u)));
      });
      setUploads((p) => p.map((u) => u.file === item.file ? { ...u, status: "processing", progress: 100, docId: result.id } : u));
      await refreshDocuments();
      const poll = setInterval(async () => {
        try {
          const s = await getDocumentStatus(result.id);
          if (s.status === "ready" || s.status === "failed") {
            clearInterval(poll);
            setUploads((p) => p.map((u) => u.file === item.file ? { ...u, status: s.status === "ready" ? "done" : "error", error: s.error_message ?? "Failed" } : u));
            await refreshDocuments();
          }
        } catch { /* retry */ }
      }, 3000);
    } catch (err) {
      setUploads((p) => p.map((u) => u.file === item.file ? { ...u, status: "error", error: err instanceof Error ? err.message : "Failed" } : u));
    }
  }

  /* ─── Sessions ─────────────────────────────────────────────── */

  function startNewChat() {
    handleCancel();
    messageQueueRef.current = [];
    syncQueuedCount();
    setError(null);
    const s: LocalSession = { id: crypto.randomUUID(), serverSessionId: null, title: "New chat", messages: [], createdAt: Date.now() };
    setSessions((p) => [s, ...p]);
    setActiveSessionId(s.id);
    setQuestion("");
    setTimeout(() => textareaRef.current?.focus(), 50);
  }

  function deleteSession(id: string) {
    setSessions((p) => p.filter((s) => s.id !== id));
    if (activeSessionId === id) setActiveSessionId(null);
  }

  /* ─── Chat ─────────────────────────────────────────────────── */

  function syncQueuedCount() {
    setQueuedCount(messageQueueRef.current.length);
  }

  function enqueueMessage(q: string) {
    messageQueueRef.current.push(q);
    syncQueuedCount();
    setQuestion("");
  }

  function handleCancel() {
    cancelledRef.current = true;
    abortControllerRef.current?.abort();
  }

  function finalizeAssistantMessage(sessionId: string, assistantId: string, stopped: boolean) {
    setSessions((p) => p.map((s) => {
      if (s.id !== sessionId) return s;
      return {
        ...s,
        messages: s.messages.map((m) => {
          if (m.id !== assistantId) return m;
          const content = m.content.trim();
          if (stopped && !content) {
            return { ...m, content: "Response stopped.", streaming: false };
          }
          return { ...m, streaming: false };
        }),
      };
    }));
  }

  async function runChatMessage(q: string) {
    setError(null);
    setSending(true);
    cancelledRef.current = false;

    const ac = new AbortController();
    abortControllerRef.current = ac;

    let current = activeSession;
    if (!current) {
      if (readyDocs.length === 0) {
        setError("Upload and process at least one document first.");
        setSending(false);
        abortControllerRef.current = null;
        return;
      }
      const s: LocalSession = {
        id: crypto.randomUUID(),
        serverSessionId: null,
        title: "New chat",
        messages: [],
        createdAt: Date.now(),
      };
      setSessions((p) => [s, ...p]);
      setActiveSessionId(s.id);
      current = s;
    }

    const sid = current.id;
    const aId = crypto.randomUUID();
    activeRequestRef.current = { sessionId: sid, assistantId: aId };

    const userMsg: UiMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: q,
      citations: [],
      suggested_followups: [],
      created_at: new Date().toISOString(),
    };
    const aiMsg: UiMessage = {
      id: aId,
      role: "assistant",
      content: "",
      citations: [],
      suggested_followups: [],
      created_at: new Date().toISOString(),
      streaming: true,
    };

    setSessions((p) => p.map((s) => s.id === sid ? {
      ...s,
      messages: [...s.messages, userMsg, aiMsg],
    } : s));

    let serverSid = current.serverSessionId;

    try {
      if (!serverSid) {
        if (readyDocs.length === 0) {
          setSessions((p) => p.map((s) => s.id === sid ? {
            ...s,
            messages: s.messages.filter((m) => m.id !== userMsg.id && m.id !== aId),
          } : s));
          setError("No documents ready.");
          return;
        }
        const res = await createChatSession(readyDocs.map((d) => d.id), ac.signal);
        serverSid = res.id;
        setSessions((p) => p.map((s) => (s.id === sid ? { ...s, serverSessionId: serverSid } : s)));
      }

      if (cancelledRef.current) return;

      let gotTokens = false;
      const generatedTitle = await streamChatMessage(serverSid!, q, (token) => {
        gotTokens = true;
        setSessions((p) => p.map((s) => s.id === sid ? {
          ...s,
          messages: s.messages.map((m) => m.id === aId ? { ...m, content: m.content + token } : m),
        } : s));
      }, ac.signal);

      if (cancelledRef.current) return;

      if (generatedTitle) {
        setSessions((p) => p.map((s) => (s.id === sid ? { ...s, title: generatedTitle } : s)));
      }

      if (!gotTokens) {
        setSessions((p) => p.map((s) => s.id === sid ? {
          ...s,
          messages: s.messages.map((m) => m.id === aId ? {
            ...m,
            content: "I couldn't generate a response. Please try again.",
            streaming: false,
          } : m),
        } : s));
      } else {
        try {
          const h = await getChatHistory(serverSid!);
          if (h.messages.length > 0) {
            setSessions((p) => p.map((s) => (s.id === sid ? {
              ...s,
              messages: h.messages,
              title: h.title ?? s.title,
            } : s)));
          }
        } catch { /* keep local */ }
      }
    } catch (err) {
      if (cancelledRef.current || isAbortError(err)) {
        return;
      }
      setSessions((p) => p.map((s) => s.id === sid ? {
        ...s,
        messages: s.messages.map((m) => m.id === aId ? {
          ...m,
          content: `Error: ${err instanceof Error ? err.message : "Something went wrong"}`,
          streaming: false,
        } : m),
      } : s));
    } finally {
      const req = activeRequestRef.current;
      abortControllerRef.current = null;
      activeRequestRef.current = null;

      if (req) {
        if (cancelledRef.current) {
          finalizeAssistantMessage(req.sessionId, req.assistantId, true);
        } else {
          setSessions((p) => p.map((s) => s.id === req.sessionId ? {
            ...s,
            messages: s.messages.map((m) => m.id === req.assistantId ? { ...m, streaming: false } : m),
          } : s));
        }
      }

      const next = messageQueueRef.current.shift();
      syncQueuedCount();

      if (next) {
        void runChatMessage(next);
      } else {
        setSending(false);
      }
    }
  }

  function handleSend() {
    const q = question.trim();
    if (!q) return;

    if (sending) {
      enqueueMessage(q);
      return;
    }

    setQuestion("");
    void runChatMessage(q);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void handleSend(); }
  }

  /* ─── Drag & drop ──────────────────────────────────────────── */
  function handleDragOver(e: React.DragEvent) { e.preventDefault(); setIsDragging(true); }
  function handleDragLeave(e: React.DragEvent) { e.preventDefault(); if (e.currentTarget === e.target) setIsDragging(false); }
  function handleDrop(e: React.DragEvent) { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files); }

  /* ─── Input box (render helper — NOT a component) ──────────── */
  const inputBox = (autoFocus?: boolean) => (
    <div className="relative rounded-[var(--radius-lg)] border border-[var(--lavender-mist)] bg-[var(--pure-paper)] shadow-sm">
      {/* Thinking bar — shows above textarea when AI is working */}
      {sending && (
        <div className="flex items-center justify-between gap-2 border-b border-[var(--lavender-mist)] bg-[var(--iris-haze)]/60 px-4 py-2">
          <InlineThinkingBar />
          <button
            type="button"
            onClick={handleCancel}
            className="flex shrink-0 items-center gap-1.5 rounded-full border border-[var(--lavender-mist)] bg-[var(--pure-paper)] px-3 py-1 text-xs font-medium text-[var(--heather)] transition-colors hover:border-[var(--electric-violet)] hover:text-[var(--electric-violet)]"
          >
            <IconStop className="h-2.5 w-2.5" />
            Stop
          </button>
        </div>
      )}
      <textarea
        ref={textareaRef}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={sending ? "Type a follow-up — it'll be queued automatically…" : "What would you like to discover…"}
        rows={1}
        autoFocus={autoFocus}
        className="w-full resize-none bg-transparent px-4 pb-11 pt-3.5 text-[15px] text-[var(--deep-ink)] placeholder:text-[var(--mist)] focus:outline-none"
        style={{ maxHeight: "200px", letterSpacing: "0.01em" }}
      />
      <div className="absolute bottom-2.5 left-3 right-3 flex items-center justify-between">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowUploadModal(true)}
            className="rounded-full p-1.5 text-[var(--mist)] transition-colors hover:bg-[var(--lavender-mist)] hover:text-[var(--heather)]"
            title="Attach files"
          >
            <IconPlus className="h-4 w-4" />
          </button>
          {/* Queue badge */}
          {queuedCount > 0 && (
            <span className="ml-1 flex items-center gap-1.5 rounded-full bg-[var(--iris-haze)] px-2.5 py-1 text-[11px] font-medium text-[var(--electric-violet)]">
              <IconLoader className="h-3 w-3" />
              {queuedCount} queued
            </span>
          )}
        </div>
        {sending ? (
          <button
            onClick={handleCancel}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--deep-ink)] text-white shadow-sm transition-all hover:bg-[var(--midnight-plum)]"
            title="Stop generating"
          >
            <IconStop />
          </button>
        ) : (
          <button
            onClick={() => void handleSend()}
            disabled={!question.trim()}
            className={clsx(
              "flex h-8 w-8 items-center justify-center rounded-full transition-all",
              question.trim()
                ? "bg-[var(--electric-violet)] text-white shadow-sm shadow-[var(--electric-violet)]/25 hover:opacity-90"
                : "bg-[var(--lavender-mist)] text-[var(--mist)] cursor-not-allowed",
            )}
            title="Send message"
          >
            <IconSend />
          </button>
        )}
      </div>
    </div>
  );

  /* ─── Render ───────────────────────────────────────────────── */

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--iris-haze)]" onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}>

      {/* Drag overlay */}
      {isDragging && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--midnight-plum)]/60 backdrop-blur-sm">
          <div className="rounded-[var(--radius-lg)] border-2 border-dashed border-[var(--electric-violet)]/40 bg-[var(--pure-paper)]/90 p-14 text-center shadow-xl">
            <IconUpload className="mx-auto mb-3 h-10 w-10 text-[var(--electric-violet)]" />
            <p className="text-base font-medium text-[var(--deep-ink)]">Drop files to upload</p>
            <p className="mt-1 text-sm text-[var(--overcast)]">PDF, DOCX</p>
          </div>
        </div>
      )}

      {/* ── Sidebar ── */}
      <aside className={clsx("flex flex-col bg-[var(--pure-paper)] border-r border-[var(--lavender-mist)] transition-all duration-200 ease-in-out overflow-hidden", sidebarOpen ? "w-[260px]" : "w-0")}>
        <div className="flex min-w-[260px] flex-col h-full">

          {/* Top row */}
          <div className="flex items-center justify-between px-3 py-3">
            <button onClick={() => setSidebarOpen(false)} className="rounded-[var(--radius)] p-1.5 text-[var(--heather)] hover:bg-[var(--iris-haze)]" title="Close sidebar">
              <IconSidebar />
            </button>
            <button onClick={startNewChat} className="rounded-[var(--radius)] p-1.5 text-[var(--heather)] hover:bg-[var(--iris-haze)]" title="New chat">
              <IconNewChat />
            </button>
          </div>

          {/* Conversations */}
          <nav className="flex-1 overflow-y-auto px-2 pb-2">
            {sessionGroups.length === 0 ? (
              <p className="px-3 py-8 text-center text-sm text-[var(--mist)]">No conversations yet</p>
            ) : (
              sessionGroups.map((g) => (
                <div key={g.label} className="mt-5 first:mt-0">
                  <p className="px-3 pb-1 text-[11px] font-medium uppercase tracking-[0.06em] text-[var(--mist)]">{g.label}</p>
                  {g.items.map((s) => (
                    <div
                      key={s.id}
                      onClick={() => setActiveSessionId(s.id)}
                      className={clsx(
                        "group relative flex cursor-pointer items-center rounded-[var(--radius)] px-3 py-2 text-[14px] transition-colors",
                        activeSessionId === s.id
                          ? "bg-[var(--iris-haze)] text-[var(--deep-ink)]"
                          : "text-[var(--heather)] hover:bg-[var(--iris-haze)]",
                      )}
                    >
                      <span className="flex-1 truncate">{s.title}</span>
                      <button
                        onClick={(e) => { e.stopPropagation(); deleteSession(s.id); }}
                        className="shrink-0 rounded-md p-1 text-[var(--mist)] opacity-0 transition-opacity hover:text-[var(--danger)] group-hover:opacity-100"
                      >
                        <IconTrash />
                      </button>
                    </div>
                  ))}
                </div>
              ))
            )}
          </nav>

          {/* Bottom */}
          <div className="space-y-0.5 border-t border-[var(--lavender-mist)] px-3 py-3">
            <button
              onClick={() => setShowUploadModal(true)}
              className="flex w-full items-center gap-2 rounded-[var(--radius)] px-3 py-2 text-[14px] text-[var(--heather)] transition-colors hover:bg-[var(--iris-haze)]"
            >
              <IconFile />
              <span className="flex-1 text-left">Documents</span>
              {readyDocs.length > 0 && (
                <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-[var(--electric-violet)] px-1.5 text-[11px] font-medium text-white">
                  {readyDocs.length}
                </span>
              )}
            </button>
            <Link
              href="/platform"
              className="flex w-full items-center gap-2 rounded-[var(--radius)] px-3 py-2 text-[14px] text-[var(--heather)] transition-colors hover:bg-[var(--iris-haze)] hover:text-[var(--deep-ink)]"
            >
              <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 3v18h18" />
                <path d="M7 14l4-4 4 4 5-6" />
              </svg>
              <span className="flex-1 text-left">Insights dashboard</span>
            </Link>
          </div>
        </div>
      </aside>

      {/* ── Main ── */}
      <main className="flex flex-1 flex-col">

        {/* Top bar */}
        <div className="flex items-center h-12 px-4">
          {!sidebarOpen && (
            <>
              <button onClick={() => setSidebarOpen(true)} className="rounded-[var(--radius)] p-1.5 text-[var(--heather)] hover:bg-[var(--lavender-mist)]" title="Open sidebar">
                <IconSidebar />
              </button>
              <button onClick={startNewChat} className="ml-1 rounded-[var(--radius)] p-1.5 text-[var(--heather)] hover:bg-[var(--lavender-mist)]" title="New chat">
                <IconNewChat />
              </button>
            </>
          )}
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <BrandLogo size={24} />
            <span className="font-semibold tracking-[-0.02em] text-[var(--deep-ink)]" style={{ fontFamily: "'Source Serif 4', serif" }}>
              Vault<span className="bg-gradient-to-r from-[var(--electric-violet)] to-purple-500 bg-clip-text text-transparent">Mind</span>
            </span>
          </div>
          <div className="flex-1" />
          {readyDocs.length > 0 && (
            <span className="text-xs text-[var(--overcast)]">{readyDocs.length} doc{readyDocs.length !== 1 ? "s" : ""}</span>
          )}
        </div>

        {/* Content */}
        {!activeSession && !sending ? (
          <div className="flex flex-1 flex-col items-center justify-center px-4 pb-40">
            <div className="mb-4 flex items-center justify-center"><BrandLogo size={40} /></div>
            <h1 className="mb-2 text-[28px] font-medium tracking-[-0.03em] text-[var(--deep-ink)]" style={{ fontFamily: "'Source Serif 4', serif" }}>
              Your documents, <span className="bg-gradient-to-r from-[var(--electric-violet)] to-purple-500 bg-clip-text text-transparent">decoded</span>.
            </h1>
            <p className="mb-8 text-[15px] text-[var(--overcast)]">
              Ask a question &mdash; get answers backed by every page
            </p>
            <div className="w-full max-w-[640px]">
              {inputBox(true)}
              {error && <p className="mt-3 rounded-[var(--radius)] bg-[var(--danger-bg)] px-4 py-2 text-sm text-[var(--danger)]">{error}</p>}
              <p className="mt-3 text-center text-xs text-[var(--mist)]">
                Instantly searches across {readyDocs.length} document{readyDocs.length !== 1 ? "s" : ""} in your vault
              </p>
            </div>
          </div>
        ) : activeSession ? (
          <>
            <div className="flex-1 overflow-y-auto">
              {activeSession.messages.length === 0 && !sending ? (
                <div className="flex h-full flex-col items-center justify-center pb-40">
                  <div className="mb-3 flex items-center justify-center"><BrandLogo size={36} /></div>
                  <h2 className="text-[28px] font-medium tracking-[-0.03em] text-[var(--deep-ink)]" style={{ fontFamily: "'Source Serif 4', serif" }}>
                    Ready when you are.
                  </h2>
                </div>
              ) : (
                <div className="mx-auto max-w-[700px] px-4 py-6">
                  {activeSession.messages.map((msg) => {
                    if (isAssistantPending(msg)) {
                      return <ThinkingIndicator key={msg.id} />;
                    }

                    return (
                      <div key={msg.id} className="mb-6">
                        {msg.role === "user" ? (
                          <div className="flex justify-end">
                            <div className="max-w-[85%] rounded-[20px] bg-[var(--electric-violet)] px-5 py-3 text-[15px] leading-[1.6] text-white">
                              {msg.content}
                            </div>
                          </div>
                        ) : (
                          <div className="flex gap-3">
                            <div className="mt-1"><AiAvatar /></div>
                            <div className="min-w-0 flex-1 pt-1">
                              <AssistantMessageBody
                                messageId={msg.id}
                                content={msg.content}
                                citations={msg.citations ?? []}
                                streaming={msg.streaming && msg.content.trim().length > 0}
                              />

                              {msg.suggested_followups?.length > 0 && (
                                <div className="mt-3 flex flex-wrap gap-1.5">
                                  {msg.suggested_followups.map((f) => (
                                    <button key={f} onClick={() => setQuestion(f)} className="rounded-full border border-[var(--lavender-mist)] px-3.5 py-1.5 text-[13px] text-[var(--heather)] transition-colors hover:border-[var(--electric-violet)] hover:text-[var(--electric-violet)]">
                                      {f}
                                    </button>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                  <div ref={chatEndRef} />
                </div>
              )}
            </div>

            {/* Input */}
            <div className="px-4 pb-4 pt-2">
              <div className="mx-auto max-w-[700px]">
                {error && <p className="mb-2 rounded-[var(--radius)] bg-[var(--danger-bg)] px-4 py-2 text-sm text-[var(--danger)]">{error}</p>}
                {inputBox()}
                <p className="mt-2 text-center text-xs text-[var(--mist)]">
                  AI-assisted insights &mdash; always verify critical details.
                </p>
              </div>
            </div>
          </>
        ) : null}
      </main>

      {/* ── Upload Modal ── */}
      {showUploadModal && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-[var(--midnight-plum)]/40 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-lg rounded-[var(--radius-lg)] bg-[var(--pure-paper)] shadow-xl shadow-[var(--deep-ink)]/10">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[var(--lavender-mist)] px-5 py-4">
              <h3 className="text-base font-semibold text-[var(--deep-ink)]" style={{ fontFamily: "'Source Serif 4', serif" }}>Your Vault</h3>
              <button onClick={() => { setShowUploadModal(false); setUploads((p) => p.filter((u) => u.status !== "done" && u.status !== "error")); }} className="rounded-full p-1 text-[var(--mist)] hover:bg-[var(--iris-haze)] hover:text-[var(--heather)]">
                <IconX />
              </button>
            </div>

            <div className="p-5">
              {/* Drop zone */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className="cursor-pointer rounded-[var(--radius-lg)] border-2 border-dashed border-[var(--lavender-mist)] p-8 text-center transition-colors hover:border-[var(--electric-violet)]/40 hover:bg-[var(--iris-haze)]"
              >
                <IconUpload className="mx-auto mb-2 text-[var(--mist)]" />
                <p className="text-sm text-[var(--deep-ink)]">
                  <span className="font-medium text-[var(--electric-violet)]">Click to browse</span> or drag and drop
                </p>
                <p className="mt-1 text-xs text-[var(--overcast)]">PDF, DOCX — multiple files</p>
                <input ref={fileInputRef} type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" multiple className="hidden" onChange={(e) => { if (e.target.files?.length) addFiles(e.target.files); e.target.value = ""; }} />
              </div>

              {/* Upload items */}
              {uploads.length > 0 && (
                <div className="mt-3 max-h-40 space-y-1.5 overflow-y-auto">
                  {uploads.map((u, i) => (
                    <div key={i} className="flex items-center gap-3 rounded-[var(--radius)] border border-[var(--lavender-mist)] px-3 py-2.5">
                      <IconFile className="shrink-0 text-[var(--mist)]" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm text-[var(--deep-ink)]">{u.file.name}</p>
                        {u.status === "uploading" && (
                          <div className="mt-1 h-1.5 rounded-full bg-[var(--lavender-mist)]">
                            <div className="h-full rounded-full bg-[var(--electric-violet)] transition-all" style={{ width: `${u.progress}%` }} />
                          </div>
                        )}
                        {u.status === "processing" && <p className="mt-0.5 text-xs text-[var(--warning)]">Processing…</p>}
                        {u.status === "done" && <p className="mt-0.5 flex items-center gap-1 text-xs text-[var(--success)]"><IconCheck /> Ready</p>}
                        {u.status === "error" && <p className="mt-0.5 text-xs text-[var(--danger)]">{u.error}</p>}
                        {u.status === "pending" && <p className="mt-0.5 text-xs text-[var(--mist)]">Queued</p>}
                      </div>
                      <span className="text-xs text-[var(--overcast)]">{formatFileSize(u.file.size)}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Existing documents */}
              {documents.length > 0 && (
                <div className="mt-4 border-t border-[var(--lavender-mist)] pt-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-[var(--mist)]">
                      Uploaded documents
                    </p>
                    {selectedDocIds.length >= 2 && (
                      <button
                        onClick={() => void handleCompareDocuments()}
                        disabled={comparing}
                        className="rounded-full bg-[var(--electric-violet)] px-3 py-1 text-[11px] font-medium text-white disabled:opacity-60"
                      >
                        {comparing ? "Comparing…" : `Compare ${selectedDocIds.length}`}
                      </button>
                    )}
                  </div>
                  {selectedDocIds.length >= 2 && (
                    <input
                      value={compareFocus}
                      onChange={(e) => setCompareFocus(e.target.value)}
                      placeholder="Comparison focus (optional): e.g. coverage limits"
                      className="mb-2 w-full rounded-[var(--radius)] border border-[var(--lavender-mist)] px-3 py-2 text-xs text-[var(--deep-ink)]"
                    />
                  )}
                  <div className="max-h-48 space-y-1 overflow-y-auto">
                    {documents.map((doc) => (
                      <div
                        key={doc.id}
                        className={clsx(
                          "flex items-center gap-2.5 rounded-[var(--radius)] px-3 py-2 hover:bg-[var(--iris-haze)]",
                          activeDocId === doc.id && "bg-[var(--iris-haze)]",
                        )}
                      >
                        <input
                          type="checkbox"
                          checked={selectedDocIds.includes(doc.id)}
                          disabled={doc.status !== "ready"}
                          onChange={() => toggleDocSelection(doc.id)}
                          className="shrink-0 accent-[var(--electric-violet)]"
                        />
                        <button
                          type="button"
                          onClick={() => doc.status === "ready" && void loadDocumentInsights(doc.id)}
                          className="flex min-w-0 flex-1 items-center gap-2 text-left"
                        >
                          <IconFile className="shrink-0 text-[var(--mist)]" />
                          <div className="min-w-0 flex-1">
                            <span className="block truncate text-sm text-[var(--deep-ink)]">{doc.filename}</span>
                            {doc.category && (
                              <span className="text-[11px] text-[var(--overcast)]">{doc.category}</span>
                            )}
                          </div>
                        </button>
                        <span className={clsx("text-xs", doc.status === "ready" ? "text-[var(--success)]" : doc.status === "processing" ? "text-[var(--warning)]" : doc.status === "failed" ? "text-[var(--danger)]" : "text-[var(--overcast)]")}>
                          {doc.status === "ready" ? "Ready" : doc.status === "processing" ? "Processing" : doc.status === "failed" ? "Failed" : "Uploaded"}
                        </span>
                      </div>
                    ))}
                  </div>

                  {insightsLoading && (
                    <p className="mt-3 text-xs text-[var(--overcast)]">Loading insights…</p>
                  )}

                  {activeInsights && !insightsLoading && (
                    <div className="mt-3 rounded-[var(--radius-lg)] border border-[var(--lavender-mist)] bg-[var(--iris-haze)]/40 p-3">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        {activeInsights.category && (
                          <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-medium text-[var(--electric-violet)]">
                            {activeInsights.category}
                          </span>
                        )}
                        {activeInsights.sentiment && (
                          <span className="rounded-full bg-white px-2 py-0.5 text-[11px] text-[var(--heather)]">
                            {activeInsights.sentiment}
                          </span>
                        )}
                        {activeInsights.tags?.map((tag) => (
                          <span key={tag} className="rounded-full border border-[var(--lavender-mist)] px-2 py-0.5 text-[11px] text-[var(--overcast)]">
                            {tag}
                          </span>
                        ))}
                      </div>
                      {activeInsights.summary && (
                        <p className="text-sm leading-relaxed text-[var(--deep-ink)]">{activeInsights.summary}</p>
                      )}
                      {activeInsights.insights.length > 0 && (
                        <ul className="mt-2 space-y-1 text-xs text-[var(--heather)]">
                          {activeInsights.insights.map((item) => (
                            <li key={item}>• {item}</li>
                          ))}
                        </ul>
                      )}

                      <div className="mt-3 border-t border-[var(--lavender-mist)] pt-3">
                        <p className="mb-2 text-[11px] font-medium uppercase tracking-[0.06em] text-[var(--mist)]">
                          Customize summary
                        </p>
                        <div className="grid grid-cols-2 gap-2">
                          <select
                            value={summaryLength}
                            onChange={(e) => setSummaryLength(e.target.value as SummaryLength)}
                            className="rounded-[var(--radius)] border border-[var(--lavender-mist)] px-2 py-1.5 text-xs"
                          >
                            <option value="brief">Brief</option>
                            <option value="standard">Standard</option>
                            <option value="detailed">Detailed</option>
                          </select>
                          <select
                            value={summaryTone}
                            onChange={(e) => setSummaryTone(e.target.value as SummaryTone)}
                            className="rounded-[var(--radius)] border border-[var(--lavender-mist)] px-2 py-1.5 text-xs"
                          >
                            <option value="neutral">Neutral</option>
                            <option value="professional">Professional</option>
                            <option value="executive">Executive</option>
                            <option value="plain">Plain language</option>
                          </select>
                        </div>
                        <input
                          value={focusAreas}
                          onChange={(e) => setFocusAreas(e.target.value)}
                          placeholder="Focus areas (comma-separated)"
                          className="mt-2 w-full rounded-[var(--radius)] border border-[var(--lavender-mist)] px-2 py-1.5 text-xs"
                        />
                        <button
                          onClick={() => void handleRegenerateInsights()}
                          disabled={regenerating}
                          className="mt-2 rounded-full border border-[var(--electric-violet)] px-3 py-1 text-xs font-medium text-[var(--electric-violet)] disabled:opacity-60"
                        >
                          {regenerating ? "Regenerating…" : "Regenerate insights"}
                        </button>
                      </div>
                    </div>
                  )}

                  {compareResult && (
                    <div className="mt-3 rounded-[var(--radius-lg)] border border-[var(--lavender-mist)] p-3">
                      <p className="mb-2 text-sm font-medium text-[var(--deep-ink)]">Comparison</p>
                      <p className="text-sm text-[var(--heather)]">{compareResult.summary}</p>
                      {compareResult.differences.length > 0 && (
                        <ul className="mt-2 space-y-1 text-xs text-[var(--heather)]">
                          {compareResult.differences.map((item) => (
                            <li key={item}>• {item}</li>
                          ))}
                        </ul>
                      )}
                      {compareResult.comparison_table.length > 0 && (
                        <div className="mt-3 overflow-x-auto">
                          <table className="w-full text-left text-xs">
                            <thead>
                              <tr className="border-b border-[var(--lavender-mist)]">
                                <th className="py-1 pr-2 font-medium text-[var(--overcast)]">Aspect</th>
                                {Object.entries(compareResult.document_filenames).map(([id, name]) => (
                                  <th key={id} className="py-1 pr-2 font-medium text-[var(--overcast)]">{name}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {compareResult.comparison_table.map((row) => (
                                <tr key={row.aspect} className="border-b border-[var(--lavender-mist)]/60">
                                  <td className="py-1.5 pr-2 font-medium text-[var(--deep-ink)]">{row.aspect}</td>
                                  {Object.keys(compareResult.document_filenames).map((id) => (
                                    <td key={id} className="py-1.5 pr-2 text-[var(--heather)]">
                                      {row.values[id] ?? "—"}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                      {compareResult.recommendation && (
                        <p className="mt-2 text-xs text-[var(--electric-violet)]">{compareResult.recommendation}</p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="flex justify-end border-t border-[var(--lavender-mist)] px-5 py-3">
              <button onClick={() => { setShowUploadModal(false); setUploads([]); }} className="rounded-full bg-[var(--electric-violet)] px-5 py-2 text-sm font-medium text-white shadow-sm shadow-[var(--electric-violet)]/25 transition-opacity hover:opacity-90">
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
