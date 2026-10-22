// Line icons (Lucide-style paths), drawn inline so the app works offline.
export const ICONS = {
  dashboard: "M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z",
  transactions: "M8 6h13M8 12h13M8 18h13M3.5 6h.5M3.5 12h.5M3.5 18h.5",
  recurring: "M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3",
  review: "M6 3h9l3 3v15H6zM9 10h6M9 14h6M9 18h4",
  compare: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  merchants: "M3 9l1.5-5h15L21 9M3 9v11h18V9M3 9h18M9 20v-6h6v6",
  networth: "M3 21h18M5 21V10M19 21V10M9.5 21V10M14.5 21V10M2 10l10-7 10 7z",
  budgets: "M12 3a9 9 0 1 0 9 9h-9zM15 3.5A9 9 0 0 1 20.5 9H15z",
  goals: "M12 21a9 9 0 1 0 0-18a9 9 0 1 0 0 18zM12 16a4 4 0 1 0 0-8a4 4 0 1 0 0 8zM12 12h.01",
  categories: "M3 3h8l10 10-8 8L3 11zM7.5 7.5h.01",
  household: "M9 11a3 3 0 1 0 0-6a3 3 0 1 0 0 6zM3 20a6 6 0 0 1 12 0M16 11a2.5 2.5 0 1 0 0-5M18 20a5 5 0 0 0-3-4.6",
  settings:
    "M9 12a3 3 0 1 0 6 0a3 3 0 1 0-6 0M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9 7 7M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1",
  import: "M12 16V4M7 9l5-5 5 5M4 20h16",
  ask: "M4 5h16v11H9l-5 4zM12 8l.8 1.7 1.7.8-1.7.8L12 13l-.8-1.7-1.7-.8 1.7-.8z",
  inbox: "M3 13l3-8h12l3 8v6H3zM3 13h5l1 3h6l1-3h5",
  lock: "M6 11h12v10H6zM8 11V7a4 4 0 0 1 8 0v4",
} as const;

export type IconName = keyof typeof ICONS;

export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={ICONS[name]} />
    </svg>
  );
}
