import { Activity, Database, Radio } from "lucide-react";
import type { Freshness } from "@/types";
import { Chip } from "./ui";
import { cx, freshnessMeta, verdictTone } from "@/utils/format";

export function FreshnessBadge({ freshness, className }: { freshness: Freshness | string; className?: string }) {
  const m = freshnessMeta(freshness);
  return (
    <Chip className={cx(m.cls, className)} title={`Data freshness: ${m.label}`}>
      <Activity className="h-3 w-3" />
      {m.label}
    </Chip>
  );
}

export function VerdictBadge({ verdict, className }: { verdict: string; className?: string }) {
  const tone = verdictTone(verdict);
  const cls = {
    risk: "text-risk border-risk/40 bg-risk/10",
    attention: "text-attention border-attention/40 bg-attention/10",
    neutral: "text-neutralc-soft border-neutralc/30 bg-neutralc/10",
    muted: "text-slate-400 border-white/10 bg-white/5",
  }[tone];
  return <Chip className={cx(cls, "font-semibold", className)}>{verdict}</Chip>;
}

export function OfflineDatasetBadge({ label }: { label?: string }) {
  return (
    <Chip className="border-neutralc/30 bg-neutralc/10 text-neutralc-soft" title="This is historical research data, not live market data.">
      <Database className="h-3 w-3" />
      {label ?? "Offline Research Dataset"}
    </Chip>
  );
}

export function DemoModeBadge() {
  return (
    <Chip className="border-attention/40 bg-attention/10 text-attention" title="Replay / demo mode — the market clock is simulated.">
      <Radio className="h-3 w-3" />
      Replay / Demo Mode
    </Chip>
  );
}
