import { useEffect, useId, useState, type FormEvent } from "react";
import { postJson } from "../api";
import { Icon } from "./Icon";
import { LogoMark, Wordmark } from "./Logo";

const MIN_PASSCODE = 6;

type Props = {
  mode: "setup" | "locked";
  notice?: string;
  retryAfter: number;
  // Setup and recovery hand back a recovery key for the person to print.
  onUnlocked: (recoveryKey?: string) => void;
};

type View = "setup" | "unlock" | "recover";

const HEADINGS: Record<View, { title: string; intro: string }> = {
  setup: {
    title: "Choose a passcode",
    intro:
      "Kinsum encrypts everything on this laptop with this passcode. Next you'll get a recovery key to print, in case you ever forget it.",
  },
  unlock: { title: "Kinsum is locked", intro: "Enter your passcode to open your family's money." },
  recover: {
    title: "Use your recovery key",
    intro: "Type the recovery key you printed when you set up Kinsum, then choose a new passcode.",
  },
};

export function LockScreen({ mode, notice, retryAfter, onUnlocked }: Props) {
  const [view, setView] = useState<View>(mode === "setup" ? "setup" : "unlock");
  const [recoveryKey, setRecoveryKey] = useState("");
  const [passcode, setPasscode] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [wait, setWait] = useState(retryAfter);
  const ids = { key: useId(), passcode: useId(), confirm: useId(), error: useId() };
  const choosing = view !== "unlock"; // setting a new passcode, so ask for it twice

  useEffect(() => setView(mode === "setup" ? "setup" : "unlock"), [mode]);
  useEffect(() => setWait(retryAfter), [retryAfter]);
  useEffect(() => {
    if (wait <= 0) return;
    const t = setTimeout(() => setWait((w) => w - 1), 1000);
    return () => clearTimeout(t);
  }, [wait]);

  function switchTo(next: View) {
    setView(next);
    setError("");
    setPasscode("");
    setConfirm("");
    setRecoveryKey("");
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (choosing && passcode.length < MIN_PASSCODE) return setError(`Use at least ${MIN_PASSCODE} characters.`);
    if (choosing && passcode !== confirm) return setError("The two passcodes do not match.");

    setBusy(true);
    try {
      const response =
        view === "setup"
          ? await postJson("/api/lock/setup", { passcode })
          : view === "recover"
            ? await postJson("/api/lock/recover", { recovery_key: recoveryKey, new_passcode: passcode })
            : await postJson("/api/lock/unlock", { passcode });
      const body = await response.json().catch(() => ({}));
      if (response.ok) {
        switchTo(view);
        onUnlocked(body.recovery_key);
        return;
      }
      setError(body.detail ?? "Something went wrong. Try again.");
      if (body.retry_after_seconds) setWait(body.retry_after_seconds);
      if (view === "unlock") setPasscode("");
    } catch {
      setError("Kinsum is not running. Start it with start.bat and try again.");
    } finally {
      setBusy(false);
    }
  }

  const blocked = view !== "setup" && wait > 0;
  const inputClass =
    "min-h-[44px] rounded-lg border border-border bg-surface px-3 text-base outline-none focus-visible:border-primary";

  return (
    <main className="flex min-h-full items-center justify-center p-6">
      <form
        onSubmit={submit}
        className="flex w-full max-w-sm flex-col gap-4 rounded-xl border border-border bg-surface p-7"
        aria-describedby={error ? ids.error : undefined}
      >
        <div className="flex items-center gap-2.5">
          <LogoMark />
          <Wordmark />
        </div>

        <div className="flex flex-col gap-1.5">
          <h1 className="m-0 flex items-center gap-2 text-xl font-semibold tracking-tight">
            <Icon name="lock" size={20} />
            {HEADINGS[view].title}
          </h1>
          <p className="m-0 text-sm leading-relaxed text-muted">{HEADINGS[view].intro}</p>
        </div>

        {notice && view === "unlock" && (
          <p role="status" className="m-0 rounded-lg bg-page px-3 py-2 text-[13px] text-muted">
            {notice}
          </p>
        )}

        {view === "recover" && (
          <label htmlFor={ids.key} className="flex flex-col gap-1.5 text-sm font-medium">
            Recovery key
            <input
              id={ids.key}
              type="text"
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck={false}
              autoFocus
              required
              placeholder="XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"
              value={recoveryKey}
              onChange={(e) => setRecoveryKey(e.target.value)}
              disabled={busy || blocked}
              className={inputClass + " amount uppercase placeholder:normal-case placeholder:text-muted/60"}
            />
          </label>
        )}

        <label htmlFor={ids.passcode} className="flex flex-col gap-1.5 text-sm font-medium">
          {view === "recover" ? "New passcode" : "Passcode"}
          <input
            id={ids.passcode}
            type="password"
            autoComplete={choosing ? "new-password" : "current-password"}
            autoFocus={view !== "recover"}
            required
            value={passcode}
            onChange={(e) => setPasscode(e.target.value)}
            disabled={busy || blocked}
            className={inputClass}
          />
        </label>
        {choosing && (
          <label htmlFor={ids.confirm} className="flex flex-col gap-1.5 text-sm font-medium">
            Type it again
            <input
              id={ids.confirm}
              type="password"
              autoComplete="new-password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              disabled={busy || blocked}
              className={inputClass}
            />
          </label>
        )}

        {(error || blocked) && (
          <p id={ids.error} role="alert" className="m-0 text-[13px] font-medium text-over">
            {blocked ? `Too many wrong tries. Try again in ${wait} s.` : error}
          </p>
        )}

        <button
          type="submit"
          disabled={busy || blocked}
          className="min-h-[44px] cursor-pointer rounded-lg bg-primary text-sm font-semibold text-white transition-colors duration-200 hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy
            ? "Opening…"
            : view === "setup"
              ? "Set passcode and continue"
              : view === "recover"
                ? "Reset passcode and unlock"
                : "Unlock"}
        </button>

        {view !== "setup" && (
          <button
            type="button"
            onClick={() => switchTo(view === "unlock" ? "recover" : "unlock")}
            className="cursor-pointer self-center rounded text-[13px] font-medium text-primary underline-offset-2 hover:underline"
          >
            {view === "unlock" ? "Forgot passcode?" : "Back to passcode"}
          </button>
        )}
      </form>
    </main>
  );
}
