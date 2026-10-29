import { useCallback, useEffect, useRef, useState } from "react";
import { api, getJson, getLockStatus, setLockedHandler, type LockState, type Member } from "./api";
import { LockScreen } from "./components/LockScreen";
import { RecoveryKeySheet } from "./components/RecoveryKeySheet";
import { MENU, Sidebar, type PageId } from "./components/Sidebar";
import { TopIcons } from "./components/TopIcons";
import { WhoAreYou } from "./components/WhoAreYou";
import { Household } from "./pages/Household";
import { Settings } from "./pages/Settings";

type Health = { status: string; version: string; ai_enabled: boolean };

const TITLES: Partial<Record<PageId, string>> = {
  import: "Import statements",
  ask: "Ask Kinsum",
  inbox: "Inbox",
};

// How often the open app re-checks whether the server has locked, and tells it someone is active.
const STATUS_EVERY_MS = 15_000;
const PING_EVERY_MS = 60_000;

function pageTitle(id: PageId): string {
  for (const g of MENU) for (const i of g.items) if (i.id === id) return i.label;
  return TITLES[id] ?? "Kinsum";
}

export default function App() {
  const [lock, setLock] = useState<LockState | "loading" | "offline">("loading");
  const [notice, setNotice] = useState("");
  const [retryAfter, setRetryAfter] = useState(0);
  // A recovery key waiting to be printed, and why it was made.
  const [sheet, setSheet] = useState<{ key: string; reason: "setup" | "recovered" | "replaced" } | null>(null);
  // Who is signed in: undefined while loading, null for a passcode from before members existed.
  const [me, setMe] = useState<Member | null | undefined>(undefined);
  const idleMinutes = useRef(10);

  const refresh = useCallback(async () => {
    try {
      const status = await getLockStatus();
      idleMinutes.current = status.idle_lock_minutes;
      setRetryAfter(status.retry_after_seconds);
      setLock((prev) => {
        if (prev === "unlocked" && status.state === "locked") {
          const m = status.idle_lock_minutes;
          setNotice(`Kinsum locked itself after ${m} minute${m === 1 ? "" : "s"} without use.`);
        }
        return status.state;
      });
    } catch {
      setLock("offline");
    }
  }, []);

  useEffect(() => {
    setLockedHandler(() => setLock("locked"));
    refresh();
  }, [refresh]);

  // While unlocked: notice when the server locks (idle timeout, another window), and report activity.
  useEffect(() => {
    if (lock !== "unlocked") return;
    let lastPing = Date.now();
    const onActivity = () => {
      if (Date.now() - lastPing < PING_EVERY_MS) return;
      lastPing = Date.now();
      api("/api/lock/ping", { method: "POST" }).catch(() => {});
    };
    const onVisible = () => document.visibilityState === "visible" && refresh();
    const events = ["pointerdown", "keydown", "wheel", "pointermove"] as const;
    events.forEach((e) => window.addEventListener(e, onActivity, { passive: true }));
    document.addEventListener("visibilitychange", onVisible);
    const timer = setInterval(refresh, STATUS_EVERY_MS);
    return () => {
      events.forEach((e) => window.removeEventListener(e, onActivity));
      document.removeEventListener("visibilitychange", onVisible);
      clearInterval(timer);
    };
  }, [lock, refresh]);

  // Never keep a recovery key or anyone's details on screen behind the lock.
  useEffect(() => {
    if (lock !== "unlocked") {
      setSheet(null);
      setMe(undefined);
      return;
    }
    getJson<{ member: Member | null }>("/api/me")
      .then((body) => setMe(body.member))
      .catch(() => {});
  }, [lock]);

  const lockNow = useCallback(async () => {
    setNotice("");
    setLock("locked");
    await api("/api/lock/lock", { method: "POST" }).catch(() => {});
  }, []);

  if (lock === "loading") return null;
  if (lock === "offline") {
    return (
      <main className="flex min-h-full items-center justify-center p-6 text-sm text-muted">
        <p role="alert">Kinsum is not running. Start it with start.bat, then reload this page.</p>
      </main>
    );
  }
  if (lock !== "unlocked") {
    return (
      <LockScreen
        mode={lock}
        notice={notice}
        retryAfter={retryAfter}
        onUnlocked={(recoveryKey) => {
          setNotice("");
          if (recoveryKey) setSheet({ key: recoveryKey, reason: lock === "setup" ? "setup" : "recovered" });
          setLock("unlocked");
        }}
      />
    );
  }
  if (sheet) return <RecoveryKeySheet recoveryKey={sheet.key} reason={sheet.reason} onDone={() => setSheet(null)} />;
  if (me === undefined) return null;
  if (me === null) return <WhoAreYou onDone={setMe} />;
  return <Home me={me} onLock={lockNow} onNewRecoveryKey={(key) => setSheet({ key, reason: "replaced" })} />;
}

function Home({
  me,
  onLock,
  onNewRecoveryKey,
}: {
  me: Member;
  onLock: () => void;
  onNewRecoveryKey: (key: string) => void;
}) {
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
      <Sidebar active={page} me={me} onNavigate={setPage} onLock={onLock} />
      <main className="flex min-w-0 flex-1 flex-col gap-5 px-8 py-6">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="m-0 text-2xl font-semibold tracking-tight">{pageTitle(page)}</h1>
          <TopIcons active={page} inboxCount={0} onNavigate={setPage} />
        </header>

        {page === "dashboard" ? (
          <section className="flex max-w-2xl flex-col gap-3 rounded-xl border border-border bg-surface p-6">
            <h2 className="m-0 text-lg font-semibold">Welcome to Kinsum</h2>
            <p className="m-0 text-sm leading-relaxed text-muted">
              Your family's money, added up — privately, on this laptop. Your data is encrypted and locked behind your
              passcode. Next, add your family and accounts under Household &amp; accounts; statement import comes after
              that.
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
        ) : page === "household" ? (
          <Household me={me} />
        ) : page === "settings" ? (
          <Settings me={me} onNewRecoveryKey={onNewRecoveryKey} />
        ) : (
          <section className="rounded-xl border border-dashed border-border bg-surface p-6 text-sm text-muted">
            {pageTitle(page)} is coming in a later step of the build plan.
          </section>
        )}
      </main>
    </div>
  );
}
