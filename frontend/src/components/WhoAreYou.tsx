import { useId, useState, type FormEvent } from "react";
import { send, type Member } from "../api";
import { LogoMark, Wordmark } from "./Logo";
import { inputClass, primaryButton } from "./Modal";

// Shown once to a passcode that was set up before Kinsum had household members.
export function WhoAreYou({ onDone }: { onDone: (me: Member) => void }) {
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const ids = { name: useId(), error: useId() };

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const body = await send<{ member: Member }>("POST", "/api/me", { name });
      onDone(body.member);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

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
          <h1 className="m-0 text-xl font-semibold tracking-tight">What's your name?</h1>
          <p className="m-0 text-sm leading-relaxed text-muted">
            Kinsum now keeps track of family members. You'll be the first one, with access to the whole household. You
            can add everyone else under Household &amp; accounts.
          </p>
        </div>
        <label htmlFor={ids.name} className="flex flex-col gap-1.5 text-sm font-medium">
          Your name
          <input id={ids.name} autoComplete="given-name" autoFocus required maxLength={60} value={name}
            onChange={(e) => setName(e.target.value)} className={inputClass} />
        </label>
        {error && (
          <p id={ids.error} role="alert" className="m-0 text-[13px] font-medium text-over">
            {error}
          </p>
        )}
        <button type="submit" disabled={busy} className={primaryButton}>
          Continue
        </button>
      </form>
    </main>
  );
}
