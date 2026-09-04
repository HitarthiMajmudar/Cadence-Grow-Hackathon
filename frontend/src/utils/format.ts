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

// ---- colour + label helpers ------------------------------------------------ //

export function severityMeta(s: Severity | string): { label: string; cls: string; dot: string } {
  switch (s) {
    case "critical":
      return { label: "Critical", cls: "text-risk border-risk/40 bg-risk/10", dot: "bg-risk" };
    case "high":
      return { label: "High", cls: "text-attention border-attention/40 bg-attention/10", dot: "bg-attention" };
    case "moderate":
      return { label: "Moderate", cls: "text-attention-soft border-attention/30 bg-attention/5", dot: "bg-attention-soft" };
    case "low":
      return { label: "Low", cls: "text-neutralc-soft border-neutralc/30 bg-neutralc/5", dot: "bg-neutralc" };
    default:
      return { label: "Minimal", cls: "text-slate-400 border-white/10 bg-white/5", dot: "bg-slate-500" };
  }
}

export function freshnessMeta(f: Freshness | string): { label: string; cls: string } {
  switch (f) {
    case "fresh":
      return { label: "Fresh", cls: "text-gain border-gain/30 bg-gain/10" };
    case "delayed":
      return { label: "Delayed", cls: "text-attention-soft border-attention/30 bg-attention/10" };
    case "stale":
      return { label: "Stale", cls: "text-attention border-attention/40 bg-attention/10" };
    case "missing":
      return { label: "Missing", cls: "text-risk border-risk/40 bg-risk/10" };
    case "conflicting":
      return { label: "Conflicting", cls: "text-risk border-risk/40 bg-risk/10" };
    default:
      return { label: f, cls: "text-slate-400 border-white/10 bg-white/5" };
  }
}

export function changeClassMeta(c: ChangeClass | string): { label: string; cls: string } {
  switch (c) {
    case "important":
      return { label: "Important", cls: "text-attention border-attention/40 bg-attention/10" };
    case "investigating":
      return { label: "Investigating", cls: "text-neutralc-soft border-neutralc/30 bg-neutralc/10" };
    case "explained":
      return { label: "Explained", cls: "text-slate-300 border-white/10 bg-white/5" };
    case "insufficient_data":
      return { label: "Insufficient data", cls: "text-risk border-risk/30 bg-risk/10" };
    default:
      return { label: "Normal", cls: "text-slate-400 border-white/10 bg-white/5" };
  }
}

export function priceDirClass(v: number | null | undefined): string {
  if (v === null || v === undefined || v === 0) return "text-slate-300";
  return v > 0 ? "text-gain" : "text-risk";
}

export function scoreColor(score: number): string {
  if (score >= 78) return "#f43f5e";
  if (score >= 60) return "#f5a524";
  if (score >= 44) return "#fbbf24";
  if (score >= 28) return "#22d3ee";
  return "#64748b";
}

export function verdictTone(verdict: string): "risk" | "attention" | "neutral" | "muted" {
  const risky = ["Unusual price and volume activity", "Possible breakdown", "Price activity before recorded news"];
  const attn = ["Conflicting evidence", "Volatility-regime change", "Possible breakout"];
  const muted = ["Normal movement", "Insufficient data", "Headline noise"];
  if (risky.includes(verdict)) return "risk";
  if (attn.includes(verdict)) return "attention";
  if (muted.includes(verdict)) return "muted";
  return "neutral";
}
