import type { ChangeClass, Freshness, Severity } from "@/types";

export { cn, cn as cx } from "@/lib/utils";

const INR = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });
const INR0 = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

export function money(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `₹${INR.format(v)}`;
}

export function compactNumber(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  if (Math.abs(v) >= 1e7) return `${(v / 1e7).toFixed(2)} Cr`;
  if (Math.abs(v) >= 1e5) return `${(v / 1e5).toFixed(2)} L`;
  if (Math.abs(v) >= 1e3) return `${(v / 1e3).toFixed(1)}k`;
  return INR0.format(v);
}

const CURRENCY_SYMBOLS: Record<string, string> = {
  INR: "₹",
  USD: "$",
  EUR: "€",
  GBP: "£",
  JPY: "¥",
  CNY: "¥",
  HKD: "HK$",
  AUD: "A$",
  CAD: "C$",
  SGD: "S$",
};

/** Live Markets covers arbitrary global symbols — unlike `money()`, which is
 * intentionally INR-only for Detective Mode's Indian-equities dataset. */
export function currencySymbol(code: string | null | undefined): string {
  if (!code) return "";
  return CURRENCY_SYMBOLS[code.toUpperCase()] ?? `${code.toUpperCase()} `;
}

export function moneyIn(v: number | null | undefined, currencyCode: string | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${currencySymbol(currencyCode)}${INR.format(v)}`;
}

export function pct(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${v > 0 ? "+" : ""}${v.toFixed(digits)}%`;
}

export function signed(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${v > 0 ? "+" : ""}${v.toFixed(digits)}`;
}

const DT = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});
const D = new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" });
const T = new Intl.DateTimeFormat("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false });

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return DT.format(new Date(iso)).replace(",", "");
}
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return D.format(new Date(iso));
}
export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return T.format(new Date(iso));
}

export function marketHoursLabel(bars: number): string {
  if (bars <= 0) return "just now";
  if (bars < 7) return `${bars} simulated market hour${bars === 1 ? "" : "s"}`;
  const sessions = bars / 7;
  return `${bars} simulated market hours (~${sessions.toFixed(1)} sessions)`;
}

// ---- badge tone + label helpers ------------------------------------------- //

/** Names that map 1:1 to <Badge variant="…"> in components/ui/badge.tsx. */
export type BadgeTone =
  | "default"
  | "secondary"
  | "outline"
  | "destructive"
  | "positive"
  | "negative"
  | "warning";

export function severityMeta(s: Severity | string): { label: string; tone: BadgeTone } {
  switch (s) {
    case "critical":
      return { label: "Critical", tone: "negative" };
    case "high":
      return { label: "High", tone: "warning" };
    case "moderate":
      return { label: "Moderate", tone: "warning" };
    case "low":
      return { label: "Low", tone: "secondary" };
    default:
      return { label: "Minimal", tone: "outline" };
  }
}

export function freshnessMeta(f: Freshness | string): { label: string; tone: BadgeTone } {
  switch (f) {
    case "fresh":
      return { label: "Fresh", tone: "positive" };
    case "delayed":
      return { label: "Delayed", tone: "warning" };
    case "stale":
      return { label: "Stale", tone: "warning" };
    case "missing":
      return { label: "Missing", tone: "negative" };
    case "conflicting":
      return { label: "Conflicting", tone: "negative" };
    default:
      return { label: String(f), tone: "outline" };
  }
}

export function changeClassMeta(c: ChangeClass | string): { label: string; tone: BadgeTone } {
  switch (c) {
    case "important":
      return { label: "Important", tone: "warning" };
    case "investigating":
      return { label: "Investigating", tone: "default" };
    case "explained":
      return { label: "Explained", tone: "secondary" };
    case "insufficient_data":
      return { label: "Insufficient data", tone: "negative" };
    default:
      return { label: "Normal", tone: "outline" };
  }
}

export function priceDirClass(v: number | null | undefined): string {
  if (v === null || v === undefined || v === 0) return "text-muted-foreground";
  return v > 0 ? "text-positive" : "text-negative";
}

/** CSS-variable colour for the Attention Score gauge / chart marks (0-100). */
export function scoreColor(score: number): string {
  if (score >= 70) return "var(--negative)";
  if (score >= 50) return "var(--warning)";
  if (score >= 30) return "var(--chart-2)";
  return "var(--muted-foreground)";
}

export function verdictTone(verdict: string): BadgeTone {
  const risky = ["Unusual price and volume activity", "Possible breakdown", "Price activity before recorded news"];
  const attn = ["Conflicting evidence", "Volatility-regime change", "Possible breakout"];
  const muted = ["Normal movement", "Insufficient data", "Headline noise"];
  if (risky.includes(verdict)) return "negative";
  if (attn.includes(verdict)) return "warning";
  if (muted.includes(verdict)) return "secondary";
  return "default";
}
