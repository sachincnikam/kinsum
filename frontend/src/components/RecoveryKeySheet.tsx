import { useId, useState } from "react";
import { LogoMark, Wordmark } from "./Logo";

type Props = {
  recoveryKey: string;
  // Why a key is being shown: first setup, after using the old key, or made in Settings.
  reason: "setup" | "recovered" | "replaced";
  onDone: () => void;
};

const INTRO: Record<Props["reason"], string> = {
  setup: "If you ever forget your passcode, this key is the only way back in. Print this page or copy the key by hand.",
  recovered: "Your passcode is reset. The recovery key you just used no longer works, so print or copy this new one.",
  replaced: "Your old recovery key no longer works. Print this new one or copy it by hand, and destroy the old copy.",
};

export function RecoveryKeySheet({ recoveryKey, reason, onDone }: Props) {
  const [saved, setSaved] = useState(false);
  const checkId = useId();
  const today = new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });

  return (
    <main className="flex min-h-full items-center justify-center p-6 print:block print:p-0">
      <section className="flex w-full max-w-lg flex-col gap-5 rounded-xl border border-border bg-surface p-7 print:max-w-none print:rounded-none print:border-0">
        <div className="flex items-center gap-2.5">
          <LogoMark />
          <Wordmark />
        </div>

        <div className="flex flex-col gap-1.5">
          <h1 className="m-0 text-xl font-semibold tracking-tight">Kinsum recovery key</h1>
          <p className="m-0 text-sm leading-relaxed text-muted print:hidden">{INTRO[reason]}</p>
          <p className="m-0 hidden text-sm text-muted print:block">Made on {today}</p>
        </div>

        <p
          className="amount m-0 rounded-lg border-2 border-dashed border-border bg-page px-3 py-5 text-center text-xl font-medium tracking-[0.08em] select-all print:bg-transparent print:text-2xl"
        >
          {recoveryKey.split("-").map((group, i) => (
            <span key={i} className="inline-block whitespace-nowrap">
              {i > 0 && "-"}
              {group}
            </span>
          ))}
        </p>

        <ul className="m-0 flex list-disc flex-col gap-1.5 pl-5 text-sm leading-relaxed text-muted">
          <li>
            Forgot your passcode? On the lock screen choose <strong className="text-ink">Forgot passcode?</strong> and
            type this key. Capitals, spaces and dashes don't matter.
          </li>
          <li>Keep it with your important papers, not on or near the laptop.</li>
          <li>Anyone with this key and this laptop can open Kinsum, so treat it like a house key.</li>
          <li>Making a new key in Settings stops this one working.</li>
        </ul>

        <div className="flex flex-col gap-3 border-t border-border pt-5 print:hidden">
          <button
            type="button"
            onClick={() => window.print()}
            className="min-h-[44px] cursor-pointer rounded-lg border border-primary bg-surface text-sm font-semibold text-primary transition-colors duration-200 hover:bg-primary-soft"
          >
            Print this page
          </button>
          <label htmlFor={checkId} className="flex cursor-pointer items-start gap-2.5 text-sm">
            <input
              id={checkId}
              type="checkbox"
              checked={saved}
              onChange={(e) => setSaved(e.target.checked)}
              className="mt-0.5 h-4 w-4 accent-primary"
            />
            I have printed this key or written it down, and put it somewhere safe.
          </label>
          <button
            type="button"
            disabled={!saved}
            onClick={onDone}
            className="min-h-[44px] cursor-pointer rounded-lg bg-primary text-sm font-semibold text-white transition-colors duration-200 hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Continue to Kinsum
          </button>
        </div>
      </section>
    </main>
  );
}
