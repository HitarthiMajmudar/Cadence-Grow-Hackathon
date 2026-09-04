import { Newspaper } from "lucide-react";
import type { RelatedNews } from "@/types";
import { Badge } from "@/components/ui/badge";
import { cn, fmtDateTime } from "@/utils/format";

const SENTIMENT_TONE: Record<string, "positive" | "negative" | "secondary"> = {
  positive: "positive",
  negative: "negative",
  neutral: "secondary",
};

export function NewsTimeline({
  news,
  detectionTs,
}: {
  news: RelatedNews[];
  detectionTs?: string;
}) {
  if (!news.length) {
    return (
      <p className="text-sm text-muted-foreground">
        No related local headlines in this window. If the price moved, it is currently unexplained.
      </p>
    );
  }
  const detection = detectionTs ? new Date(detectionTs).getTime() : null;
  return (
    <ol className="relative space-y-3 border-l pl-4">
      {news.map((n) => {
        const t = new Date(n.timestamp).getTime();
        const after = detection !== null && t > detection;
        return (
          <li key={n.id} className="relative">
            <span
              className={cn(
                "absolute -left-[21px] top-1.5 size-2.5 rounded-full border-2 border-background",
                after ? "bg-warning" : "bg-primary",
              )}
            />
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span className="font-mono">{fmtDateTime(n.timestamp)}</span>
              <Badge variant={SENTIMENT_TONE[n.sentiment_label] ?? "secondary"} className="h-4 px-1.5">
                {n.sentiment_label}
              </Badge>
              <Badge variant="outline" className="h-4 px-1.5">
                {n.event_type}
              </Badge>
              {after && <span className="text-warning-foreground">after the move</span>}
            </div>
            <p className="mt-1 flex gap-2 text-sm text-foreground">
              <Newspaper className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
              {n.headline}
            </p>
            <div className="mt-0.5 text-[11px] text-muted-foreground">source: {n.source}</div>
          </li>
        );
      })}
    </ol>
  );
}
