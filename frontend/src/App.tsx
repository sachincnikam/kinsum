import { useEffect, useState } from "react";
import { MENU, Sidebar, type PageId } from "./components/Sidebar";
import { TopIcons } from "./components/TopIcons";

type Health = { status: string; version: string; ai_enabled: boolean };

const TITLES: Partial<Record<PageId, string>> = {
  import: "Import statements",
  ask: "Ask Kinsum",
  inbox: "Inbox",
};

function pageTitle(id: PageId): string {
  for (const g of MENU) for (const i of g.items) if (i.id === id) return i.label;
  return TITLES[id] ?? "Kinsum";
}

export default function App() {
  const [page, setPage] = useState<PageId>("dashboard");
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setError(true));
  }, []);

  return (
    <div className="flex min-h-full">
      <Sidebar active={page} onNavigate={setPage} />
      <main className="flex min-w-0 flex-1 flex-col gap-5 px-8 py-6">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="m-0 text-2xl font-semibold tracking-tight">{pageTitle(page)}</h1>
          <TopIcons active={page} inboxCount={0} onNavigate={setPage} />
        </header>

        {page === "dashboard" ? (
          <section className="flex max-w-2xl flex-col gap-3 rounded-xl border border-border bg-surface p-6">
            <h2 className="m-0 text-lg font-semibold">Welcome to Kinsum</h2>
            <p className="m-0 text-sm leading-relaxed text-muted">
              Your family's money, added up — privately, on this laptop. This is the starter version: the next steps add
              the passcode, household members, accounts and statement import.
            </p>
            <div className="mt-1 flex flex-wrap gap-2 text-[13px]">
              <span className="rounded-full bg-page px-3 py-1">
                Backend:{" "}
                {error ? (
                  <strong className="text-over">not reachable</strong>
                ) : health ? (
                  <strong className="text-income">running · v{health.version}</strong>
                ) : (
                  "checking…"
                )}
              </span>
              {health && (
                <span className="rounded-full bg-page px-3 py-1">
                  AI: <strong>{health.ai_enabled ? "key set" : "off (no key)"}</strong>
                </span>
              )}
            </div>
          </section>
        ) : (
          <section className="rounded-xl border border-dashed border-border bg-surface p-6 text-sm text-muted">
            {pageTitle(page)} is coming in a later step of the build plan.
          </section>
        )}
      </main>
    </div>
  );
}
