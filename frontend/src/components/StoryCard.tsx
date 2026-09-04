import { forwardRef } from "react";
import type { StoryCardData } from "@/types";
import { Sparkline } from "./Sparkline";
import { fmtDate, scoreColor } from "@/utils/format";

export const StoryCard = forwardRef<HTMLDivElement, { data: StoryCardData }>(({ data }, ref) => {
  const color = scoreColor(data.attention_score);
  return (
    <div
      ref={ref}
      className="w-[440px] overflow-hidden rounded-lg border bg-card p-6 text-card-foreground"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="grid size-8 place-items-center rounded-md border border-primary/40 bg-primary/10">
            <span className="text-sm">🔍</span>
          </div>
          <div>
            <div className="text-xs font-semibold tracking-tight">CADENCE</div>
            <div className="text-[10px] text-muted-foreground">
              cause every market move has a rhythm
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="font-mono text-lg font-semibold">{data.symbol}</div>
          <div className="text-[10px] text-muted-foreground">{fmtDate(data.event_date)}</div>
        </div>
      </div>

      <div className="mt-5 flex items-end gap-4">
        <div>
          <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Attention Score
          </div>
          <div className="text-5xl font-semibold tabular-nums" style={{ color }}>
            {Math.round(data.attention_score)}
          </div>
          <div className="text-[10px] text-muted-foreground">
            {Math.round(data.confidence)}% confidence
          </div>
        </div>
        <div className="flex-1">
          <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Verdict
          </div>
          <div className="rounded-md border border-primary/30 bg-primary/10 px-3 py-2 text-sm font-semibold text-primary">
            {data.verdict}
          </div>
        </div>
      </div>

      <p className="mt-4 text-sm leading-relaxed text-foreground">{data.one_line}</p>

      <div className="mt-4">
        <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          Main evidence
        </div>
        <ul className="space-y-1">
          {data.main_evidence.map((e, i) => (
            <li key={i} className="flex gap-1.5 text-xs text-muted-foreground">
              <span style={{ color }}>▸</span>
              {e}
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-4 rounded-md border bg-muted/40 p-2">
        <Sparkline data={data.sparkline} width={392} height={44} strokeWidth={2} />
      </div>

      <div className="mt-4 flex items-center justify-between border-t pt-3 text-[10px] text-muted-foreground">
        <span>{data.dataset_label}</span>
        <span className="font-medium">{data.disclaimer}</span>
      </div>
    </div>
  );
});
StoryCard.displayName = "StoryCard";
