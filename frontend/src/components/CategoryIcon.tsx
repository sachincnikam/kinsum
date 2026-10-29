import { iconFor } from "../lib/categoryIcons";

// A category's icon on a small tile tinted with its colour, used wherever a category appears.
export function CategoryIcon({ icon, colour, size = 32 }: { icon: string; colour: string; size?: number }) {
  const Icon = iconFor(icon);
  return (
    <span
      aria-hidden="true"
      className="inline-flex shrink-0 items-center justify-center rounded-lg"
      style={{ width: size, height: size, background: `${colour}1F`, color: colour }}
    >
      <Icon size={Math.round(size * 0.56)} strokeWidth={1.8} />
    </span>
  );
}
