import { Link } from "react-router-dom";
import { CheckCircle2, Eye, Sparkles } from "lucide-react";
import type { Briefing } from "@/types";
import { changeClassMeta, cn, fmtDateTime, pct, priceDirClass } from "@/utils/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export function SinceYouLeft({
  briefing,
  onMarkSeen,
  marking,
}: {
  briefing: Briefing;
  onMarkSeen: () => void;
  marking: boolean;
}) {
  const b = briefing;
  return (
    <Card>
      <CardHeader className="border-b">
        <div className="flex flex-wrap items-start justify-between gap-4 pb-4">
          <div>
            <div className="flex items-center gap-1.5 text-xs font-medium text-primary">
              <Sparkles className="size-4" /> Since You Left
            </div>
            <h2 className="mt-1 max-w-2xl text-sm font-semibold leading-snug text-foreground">
              {b.summary_line}
            </h2>
            {b.has_previous_snapshot && (
              <p className="mt-1 text-xs text-muted-foreground">
                Comparing against your snapshot from {fmtDateTime(b.snapshot_dataset_timestamp)} ·
                threshold {b.threshold}
              </p>
            )}
          </div>
          <Button size="sm" onClick={onMarkSeen} disabled={marking}>
            <CheckCircle2 />
            {marking ? "Saving…" : "Mark briefing as seen"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="divide-y p-0">
        {b.changes.map((c) => {
          const cm = changeClassMeta(c.classification);
          return (
            <div
              key={c.symbol}
              className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 hover:bg-accent/40"
            >
              <div className="w-28 shrink-0">
                <Link
                  to={`/stocks/${c.symbol}`}
                  className="font-mono text-sm font-semibold hover:text-primary"
                >
                  {c.symbol}
                </Link>
                <div className="truncate text-[11px] text-muted-foreground">{c.sector}</div>
              </div>
              <Badge variant={cm.tone} className="shrink-0">
                {cm.label}
              </Badge>
              <div className="min-w-0 flex-1 text-xs text-foreground/80">{c.headline}</div>
              <div className="w-20 shrink-0 text-right">
                <div className={cn("text-sm font-semibold tabular-nums", priceDirClass(c.price_change_pct))}>
                  {pct(c.price_change_pct)}
                </div>
                <div className="text-[11px] text-muted-foreground">
                  attn {c.attention_delta >= 0 ? "+" : ""}
                  {c.attention_delta.toFixed(0)}
                </div>
              </div>
              {c.new_case_id ? (
                <Button variant="secondary" size="xs" render={<Link to={`/cases/${c.new_case_id}`} />}>
                  Open case
                </Button>
              ) : (
                <span className="flex w-[86px] items-center justify-end gap-1 text-[11px] text-muted-foreground">
                  <Eye className="size-3" /> no new case
                </span>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
