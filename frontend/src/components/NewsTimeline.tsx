import { Newspaper } from "lucide-react";
import type { RelatedNews } from "@/types";
import { cx, fmtDateTime } from "@/utils/format";

const SENTIMENT_CLS: Record<string, string> = {
  positive: "text-gain border-gain/30 bg-gain/10",
  negative: "text-risk border-risk/30 bg-risk/10",
  neutral: "text-slate-400 border-white/10 bg-white/5",
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
      <p className="text-sm text-slate-500">
        No related local headlines in this window. If the price moved, it is currently unexplained.
      </p>
    );
  }
  const detection = detectionTs ? new Date(detectionTs).getTime() : null;
  return (
    <ol className="relative space-y-3 border-l border-white/10 pl-4">
      {news.map((n) => {
        const t = new Date(n.timestamp).getTime();
        const after = detection !== null && t > detection;
        return (
          <li key={n.id} className="relative">
            <span
              className={cx(
                "absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-ink-900",
                after ? "bg-attention" : "bg-neutralc",
              )}
            />
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <span className="font-mono">{fmtDateTime(n.timestamp)}</span>
              <span className={cx("chip !py-0.5", SENTIMENT_CLS[n.sentiment_label] ?? SENTIMENT_CLS.neutral)}>
                {n.sentiment_label}
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5">{n.event_type}</span>
              {after && <span className="text-attention">after the move</span>}
            </div>
            <p className="mt-1 flex gap-2 text-sm text-slate-200">
              <Newspaper className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" />
              {n.headline}
            </p>
            <div className="mt-0.5 text-[11px] text-slate-600">source: {n.source}</div>
          </li>
        );
      })}
    </ol>
  );
}
