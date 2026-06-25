import VaultApp from "@/components/VaultApp";
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
    <div>
      <div className="border-b border-slate-800 px-6 py-3 text-sm text-slate-400">
        API status:{" "}
        <span className={apiStatus === "ok" ? "text-emerald-400" : "text-amber-400"}>{apiStatus}</span>
      </div>
      <VaultApp />
    </div>
  );
}
