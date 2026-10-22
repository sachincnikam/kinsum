// Kinsum logo, concept A "Growing family".
export function LogoMark({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <rect width="64" height="64" rx="15" fill="#1E40AF" />
      <rect x="13" y="37" width="10" height="17" rx="5" fill="#FFFFFF" />
      <circle cx="18" cy="30" r="4.5" fill="#FFFFFF" />
      <rect x="27" y="29" width="10" height="25" rx="5" fill="#FFFFFF" />
      <circle cx="32" cy="22" r="4.5" fill="#FFFFFF" />
      <rect x="41" y="21" width="10" height="33" rx="5" fill="#34D399" />
      <circle cx="46" cy="14" r="4.5" fill="#34D399" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="text-[18px] font-semibold tracking-tight">
      kin<span className="text-income">sum</span>
    </span>
  );
}
