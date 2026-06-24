import { fetchHealth } from "@/lib/api";

export default async function HomePage() {
  let apiStatus = "unreachable";

  try {
    const health = await fetchHealth();
    apiStatus = health.status;
  } catch {
    apiStatus = "unreachable";
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-8 px-6 py-16">
      <header className="space-y-2">
        <p className="text-sm uppercase tracking-widest text-slate-400">Document Vault AI</p>
        <h1 className="text-4xl font-semibold">Upload. Process. Chat.</h1>
        <p className="text-slate-300">
          Frontend scaffold connected to the FastAPI backend. Document upload and chat UI will
          land in the next phases.
        </p>
      </header>

      <section className="rounded-xl border border-slate-700 bg-slate-900/60 p-6">
        <h2 className="mb-2 text-lg font-medium">API status</h2>
        <p className="text-slate-300">
          Backend health:{" "}
          <span className={apiStatus === "ok" ? "text-emerald-400" : "text-amber-400"}>
            {apiStatus}
          </span>
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-700 p-5">
          <h3 className="font-medium">Documents</h3>
          <p className="mt-2 text-sm text-slate-400">Upload and processing UI coming soon.</p>
        </div>
        <div className="rounded-xl border border-slate-700 p-5">
          <h3 className="font-medium">Chat</h3>
          <p className="mt-2 text-sm text-slate-400">RAG chat interface coming soon.</p>
        </div>
      </section>
    </main>
  );
}
