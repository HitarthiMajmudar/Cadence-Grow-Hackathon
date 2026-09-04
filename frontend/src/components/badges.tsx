import { Activity, Database, Radio, Wifi } from "lucide-react";
import type { Freshness } from "@/types";
import { Badge } from "@/components/ui/badge";
import { cn, freshnessMeta, verdictTone } from "@/utils/format";

export function FreshnessBadge({
  freshness,
  className,
}: {
  freshness: Freshness | string;
  className?: string;
}) {
  const m = freshnessMeta(freshness);
  return (
    <Badge variant={m.tone} className={cn("gap-1", className)} title={`Data freshness: ${m.label}`}>
      <Activity />
      {m.label}
    </Badge>
  );
}

export function VerdictBadge({ verdict, className }: { verdict: string; className?: string }) {
  return (
    <Badge variant={verdictTone(verdict)} className={cn("font-medium", className)}>
      {verdict}
    </Badge>
  );
}

export function OfflineDatasetBadge({ label }: { label?: string }) {
  return (
    <Badge
      variant="outline"
      className="gap-1"
      title="This is historical research data, not live market data."
    >
      <Database />
      {label ?? "Offline Research Dataset"}
    </Badge>
  );
}

export function DemoModeBadge() {
  return (
    <Badge variant="warning" className="gap-1" title="The market clock is simulated, not live.">
      <Radio />
      Simulated Market Clock
    </Badge>
  );
}

export function LiveDataBadge() {
  return (
    <Badge
      variant="positive"
      className="gap-1"
      title="Real quotes fetched live from Twelve Data — no Attention Score or anomaly detection here."
    >
      <Wifi />
      Live via Twelve Data
    </Badge>
  );
}
