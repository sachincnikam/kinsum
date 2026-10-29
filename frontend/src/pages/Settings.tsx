import { useId, useState, type FormEvent } from "react";
import { send, type Member } from "../api";
import { inputClass, primaryButton } from "../components/Modal";
import { RecoverySettings } from "../components/RecoverySettings";

export function Settings({ me, onNewRecoveryKey }: { me: Member; onNewRecoveryKey: (key: string) => void }) {
  return (
    <div className="flex max-w-2xl flex-col gap-5">
      <ChangePasscode />
      {me.access === "household" && <RecoverySettings onNewKey={onNewRecoveryKey} />}
    </div>
  );
}

function ChangePasscode() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [again, setAgain] = useState("");
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const ids = { current: useId(), next: useId(), again: useId(), message: useId() };

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (next !== again) return setMessage({ ok: false, text: "The two new passcodes do not match." });
    setBusy(true);
    try {
      await send("POST", "/api/lock/change-passcode", { current, new: next });
      setCurrent("");
      setNext("");
      setAgain("");
      setMessage({ ok: true, text: "Passcode changed. Use the new one next time you unlock." });
    } catch (err) {
      setMessage({ ok: false, text: (err as Error).message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-6">
      <h2 className="m-0 text-lg font-semibold">Your passcode</h2>
      <form onSubmit={submit} className="flex flex-col gap-3" aria-describedby={message ? ids.message : undefined}>
        <div className="grid gap-3 sm:grid-cols-3">
          <label htmlFor={ids.current} className="flex flex-col gap-1.5 text-sm font-medium">
            Current passcode
            <input id={ids.current} type="password" autoComplete="current-password" required value={current}
              onChange={(e) => setCurrent(e.target.value)} className={inputClass} />
          </label>
          <label htmlFor={ids.next} className="flex flex-col gap-1.5 text-sm font-medium">
            New passcode
            <input id={ids.next} type="password" autoComplete="new-password" required minLength={6} value={next}
              onChange={(e) => setNext(e.target.value)} className={inputClass} />
          </label>
          <label htmlFor={ids.again} className="flex flex-col gap-1.5 text-sm font-medium">
            New passcode again
            <input id={ids.again} type="password" autoComplete="new-password" required value={again}
              onChange={(e) => setAgain(e.target.value)} className={inputClass} />
          </label>
        </div>
        <div>
          <button type="submit" disabled={busy} className={primaryButton}>
            Change passcode
          </button>
        </div>
        {message && (
          <p id={ids.message} role={message.ok ? "status" : "alert"}
            className={"m-0 text-[13px] font-medium " + (message.ok ? "text-income" : "text-over")}>
            {message.text}
          </p>
        )}
      </form>
    </section>
  );
}
