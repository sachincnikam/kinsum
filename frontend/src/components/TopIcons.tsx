import { Icon } from "./Icon";
import type { PageId } from "./Sidebar";

const QUICK: { id: PageId; label: string; icon: "import" | "ask" | "inbox" }[] = [
  { id: "import", label: "Import statements", icon: "import" },
  { id: "ask", label: "Ask Kinsum", icon: "ask" },
  { id: "inbox", label: "Inbox", icon: "inbox" },
];

export function TopIcons({
  active,
  inboxCount,
  onNavigate,
}: {
  active: PageId;
  inboxCount: number;
  onNavigate: (id: PageId) => void;
}) {
  return (
    <div role="toolbar" aria-label="Quick actions" className="flex items-center gap-1.5">
      {QUICK.map((q) => {
        const on = q.id === active;
        const label = q.id === "inbox" && inboxCount > 0 ? `${q.label}, ${inboxCount} items` : q.label;
        return (
          <button
            key={q.id}
            type="button"
            title={label}
            aria-label={label}
            aria-current={on ? "page" : undefined}
            onClick={() => onNavigate(q.id)}
            className={
              "relative flex h-[42px] w-[42px] cursor-pointer items-center justify-center rounded-lg border transition-colors duration-200 " +
              (on ? "border-primary bg-primary text-white" : "border-border bg-surface text-ink hover:bg-page")
            }
          >
            <Icon name={q.icon} size={20} />
            {q.id === "inbox" && inboxCount > 0 && (
              <span
                aria-hidden="true"
                className="absolute -right-1 -top-1 flex h-[18px] min-w-[18px] items-center justify-center rounded-full border-2 border-page bg-over px-1 text-[10px] font-semibold text-white"
              >
                {inboxCount}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
