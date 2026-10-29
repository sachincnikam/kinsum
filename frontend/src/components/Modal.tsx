import { useEffect, useRef, type ReactNode } from "react";

// A dialog built on <dialog>, so focus is trapped and Esc closes it for free.
export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      aria-labelledby="modal-title"
      className="m-auto w-[calc(100%-32px)] max-w-lg rounded-xl border border-border bg-surface p-0 text-ink shadow-xl backdrop:bg-ink/40"
    >
      <div className="flex max-h-[85vh] flex-col gap-4 overflow-y-auto p-6">
        <h2 id="modal-title" className="m-0 text-lg font-semibold">
          {title}
        </h2>
        {children}
      </div>
    </dialog>
  );
}

export const inputClass =
  "min-h-[44px] rounded-lg border border-border bg-surface px-3 text-base outline-none focus-visible:border-primary";
export const primaryButton =
  "min-h-[44px] cursor-pointer rounded-lg bg-primary px-4 text-sm font-semibold text-white transition-colors duration-200 hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60";
export const secondaryButton =
  "min-h-[40px] cursor-pointer rounded-lg border border-border bg-surface px-3 text-sm font-medium transition-colors duration-200 hover:bg-page disabled:cursor-not-allowed disabled:opacity-60";
