import { Icon, type IconName } from "./Icon";
import { LogoMark, Wordmark } from "./Logo";

export type PageId =
  | "dashboard"
  | "transactions"
  | "recurring"
  | "review"
  | "compare"
  | "merchants"
  | "networth"
  | "budgets"
  | "goals"
  | "categories"
  | "household"
  | "settings"
  | "import"
  | "ask"
  | "inbox";

type Item = { id: PageId; label: string; icon: IconName };

// Menu groups agreed in the plan: 12 sidebar items; Import, Ask and Inbox live as top-right icons.
export const MENU: { title: string; items: Item[] }[] = [
  {
    title: "",
    items: [
      { id: "dashboard", label: "Dashboard", icon: "dashboard" },
      { id: "transactions", label: "Transactions", icon: "transactions" },
      { id: "recurring", label: "Recurring & subscriptions", icon: "recurring" },
    ],
  },
  {
    title: "Insights",
    items: [
      { id: "review", label: "Monthly review", icon: "review" },
      { id: "compare", label: "Month to month", icon: "compare" },
      { id: "merchants", label: "Merchants", icon: "merchants" },
      { id: "networth", label: "Net worth & look back", icon: "networth" },
    ],
  },
  {
    title: "Plan",
    items: [
      { id: "budgets", label: "Budgets & limits", icon: "budgets" },
      { id: "goals", label: "Savings goals", icon: "goals" },
    ],
  },
  {
    title: "Setup",
    items: [
      { id: "categories", label: "Categories, tags & rules", icon: "categories" },
      { id: "household", label: "Household & accounts", icon: "household" },
      { id: "settings", label: "Settings", icon: "settings" },
    ],
  },
];

export function Sidebar({
  active,
  onNavigate,
  onLock,
}: {
  active: PageId;
  onNavigate: (id: PageId) => void;
  onLock: () => void;
}) {
  return (
    <nav
      aria-label="Main"
      className="flex w-60 shrink-0 flex-col gap-0.5 border-r border-border bg-surface px-3.5 py-5"
    >
      <div className="flex items-center gap-2.5 px-2.5 pb-4">
        <LogoMark />
        <Wordmark />
      </div>
      {MENU.map((group, gi) => (
        <div key={gi} className={gi > 0 ? "mt-3.5 flex flex-col gap-px" : "flex flex-col gap-px"}>
          {group.title && (
            <span className="px-2.5 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted">
              {group.title}
            </span>
          )}
          {group.items.map((item) => {
            const on = item.id === active;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onNavigate(item.id)}
                aria-current={on ? "page" : undefined}
                className={
                  "flex min-h-[38px] cursor-pointer items-center gap-3 rounded-lg px-2.5 text-left text-sm transition-colors duration-200 " +
                  (on
                    ? "bg-primary-soft font-semibold text-ink"
                    : "text-muted hover:bg-page hover:text-ink")
                }
              >
                <Icon name={item.icon} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      ))}
      <div className="flex-1" />
      <div className="mt-4 flex flex-col gap-2 rounded-lg bg-page p-3">
        <span className="flex items-center gap-2 text-xs text-muted">
          <Icon name="lock" size={14} />
          Local · data stays on this laptop
        </span>
        <button
          type="button"
          onClick={onLock}
          className="min-h-[38px] cursor-pointer rounded-lg border border-border bg-surface text-[13px] font-medium hover:bg-page"
        >
          Lock app
        </button>
      </div>
    </nav>
  );
}
