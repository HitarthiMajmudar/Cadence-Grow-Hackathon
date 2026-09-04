import { Link } from "react-router-dom";
import { ArrowUpRight, Clock, Eye, Users } from "lucide-react";
import type { CaseSummary } from "@/types";
import { AttentionMeter } from "./AttentionScore";
import { Sparkline } from "./Sparkline";
import { VerdictBadge } from "./badges";
import { Badge } from "@/components/ui/badge";
import { cn, fmtDateTime, severityMeta } from "@/utils/format";

export function CaseCard({ c, dense = false }: { c: CaseSummary; dense?: boolean }) {
  const sev = severityMeta(c.severity);
  return (
    <Link
      to={`/cases/${c.case_id}`}
      className={cn(
        "group block rounded-md border bg-card p-4 transition-colors hover:bg-accent/50",
        !c.is_seen && "border-primary/40",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-semibold">{c.symbol}</span>
            <span className="truncate text-xs text-muted-foreground">{c.company_name}</span>
            {!c.is_seen && (
              <span className="size-1.5 rounded-full bg-primary" title="New since your last visit" />
            )}
          </div>
          <div className="mt-1.5">
            <VerdictBadge verdict={c.verdict} />
          </div>
        </div>
        <ArrowUpRight className="size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-foreground" />
      </div>

      <p className={cn("mt-2 text-xs text-foreground/80", dense ? "line-clamp-2" : "line-clamp-3")}>
        {c.headline_explanation}
      </p>

      <div className="mt-3 flex items-center justify-between gap-3">
        <AttentionMeter score={c.attention_score} />
        <Sparkline data={c.spark ?? []} width={70} height={22} />
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
        <Badge variant={sev.tone} className="h-4 px-1.5">
          {sev.label}
        </Badge>
        <span className="flex items-center gap-1">
          <Clock className="size-3" />
          {fmtDateTime(c.detection_timestamp)}
        </span>
        {c.status === "viewed" && (
          <span className="flex items-center gap-1">
            <Eye className="size-3" /> viewed
          </span>
        )}
        {typeof c.peers_in_move === "number" && c.peers_in_move > 0 && (
          <span className="flex items-center gap-1">
            <Users className="size-3" /> +{c.peers_in_move} peers
          </span>
        )}
        <span className="ml-auto">{Math.round(c.confidence)}% conf</span>
      </div>
    </Link>
  );
}
