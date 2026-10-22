import { useEffect, useId, useState, type FormEvent } from "react";
import { api, postJson } from "../api";

// Settings → Recovery key: shows when the current key was made and makes a new one.
export function RecoverySettings({ onNewKey }: { onNewKey: (recoveryKey: string) => void }) {
  const [created, setCreated] = useState<string | null | undefined>(undefined);
  const [passcode, setPasscode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const ids = { passcode: useId(), error: useId() };

  useEffect(() => {
    api("/api/lock/recovery-key")
      .then((r) => (r.ok ? r.json() : { created: null }))
      .then((body) => setCreated(body.created))
      .catch(() => setCreated(null));
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const response = await postJson("/api/lock/recovery-key", { passcode });
      const body = await response.json().catch(() => ({}));
      if (response.ok) {
        setPasscode("");
        onNewKey(body.recovery_key);
      } else if (response.status !== 423) {
        setError(body.detail ?? "Something went wrong. Try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  const madeOn = created
    ? new Date(created + "T00:00:00").toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })
    : null;

  return (
    <section className="flex max-w-2xl flex-col gap-3 rounded-xl border border-border bg-surface p-6">
      <h2 className="m-0 text-lg font-semibold">Recovery key</h2>
      <p className="m-0 text-sm leading-relaxed text-muted">
        {created === undefined
          ? "Checking…"
          : madeOn
            ? `Your current recovery key was made on ${madeOn}. If you've lost the printout, make a new one; the old key then stops working.`
            : "You don't have a recovery key yet. Make one now: without it, a forgotten passcode means your data can't be opened."}
      </p>
      <form onSubmit={submit} className="flex flex-wrap items-end gap-3" aria-describedby={error ? ids.error : undefined}>
        <label htmlFor={ids.passcode} className="flex flex-col gap-1.5 text-sm font-medium">
          Your passcode
          <input
            id={ids.passcode}
            type="password"
            autoComplete="current-password"
            required
            value={passcode}
            onChange={(e) => setPasscode(e.target.value)}
            disabled={busy}
            className="min-h-[44px] w-64 rounded-lg border border-border bg-surface px-3 text-base outline-none focus-visible:border-primary"
          />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="min-h-[44px] cursor-pointer rounded-lg bg-primary px-4 text-sm font-semibold text-white transition-colors duration-200 hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {madeOn ? "Make a new recovery key" : "Make a recovery key"}
        </button>
      </form>
      {error && (
        <p id={ids.error} role="alert" className="m-0 text-[13px] font-medium text-over">
          {error}
        </p>
      )}
    </section>
  );
}
