// Money is integer cents everywhere. These turn it into text and back.

const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

/** "$1,250.50". Always signed with a real minus (−) when negative, so colour is never the only signal. */
export function formatCents(cents: number): string {
  const text = usd.format(Math.abs(cents) / 100);
  return cents < 0 ? `−${text}` : text;
}

/** Reads what someone typed ("1,250.5", "$80", "-12") as cents. Null when it is not an amount. */
export function parseDollars(text: string): number | null {
  const cleaned = text.replace(/[$,\s]/g, "").replace("−", "-");
  if (cleaned === "") return 0;
  if (!/^-?\d+(\.\d{0,2})?$/.test(cleaned)) return null;
  const negative = cleaned.startsWith("-");
  const [whole, part = ""] = cleaned.replace("-", "").split(".");
  const cents = Number(whole) * 100 + Number(part.padEnd(2, "0"));
  return negative ? -cents : cents;
}

/** Cents as plain text for an input box ("1250.50"). */
export function centsToInput(cents: number): string {
  return (cents / 100).toFixed(2);
}
