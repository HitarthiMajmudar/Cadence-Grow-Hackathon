import { Link } from "react-router-dom";
import { CheckCircle2, Eye, Sparkles } from "lucide-react";
import type { Briefing } from "@/types";
import { changeClassMeta, cx, fmtDateTime, pct, priceDirClass } from "@/utils/format";
import { Chip } from "./ui";

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
    <section className="glass overflow-hidden p-0">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/10 bg-gradient-to-r from-attention/10 via-transparent to-transparent p-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-attention">
            <Sparkles className="h-4 w-4" /> Since You Left
          </div>
          <h2 className="mt-1 max-w-2xl text-lg font-bold leading-snug text-slate-100">
            {b.summary_line}
          </h2>
          {b.has_previous_snapshot && (
            <p className="mt-1 text-xs text-slate-500">
              Comparing against your snapshot from {fmtDateTime(b.snapshot_dataset_timestamp)} · threshold{" "}
              {b.threshold}
            </p>
          )}
        </div>
        <button className="btn-primary shrink-0" onClick={onMarkSeen} disabled={marking}>
          <CheckCircle2 className="h-4 w-4" />
          {marking ? "Saving…" : "Mark Briefing as Seen"}
        </button>
      </div>

      <div className="divide-y divide-white/5">
        {b.changes.map((c) => {
          const cm = changeClassMeta(c.classification);
          return (
            <div key={c.symbol} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3 hover:bg-white/[0.03]">
              <div className="w-28 shrink-0">
                <Link to={`/stocks/${c.symbol}`} className="font-mono text-sm font-bold text-slate-100 hover:text-attention">
                  {c.symbol}
                </Link>
                <div className="truncate text-[11px] text-slate-500">{c.sector}</div>
              </div>
              <Chip className={cx(cm.cls, "shrink-0")}>{cm.label}</Chip>
              <div className="min-w-0 flex-1 text-sm text-slate-300">{c.headline}</div>
              <div className="w-20 shrink-0 text-right">
                <div className={cx("text-sm font-semibold tabular-nums", priceDirClass(c.price_change_pct))}>
                  {pct(c.price_change_pct)}
                </div>
                <div className="text-[11px] text-slate-500">
                  attn {c.attention_delta >= 0 ? "+" : ""}
                  {c.attention_delta.toFixed(0)}
                </div>
              </div>
              {c.new_case_id ? (
                <Link to={`/cases/${c.new_case_id}`} className="btn-cyan !px-3 !py-1.5 text-xs">
                  Open case
                </Link>
              ) : (
                <span className="flex w-[86px] items-center justify-end gap-1 text-[11px] text-slate-600">
                  <Eye className="h-3 w-3" /> no new case
                </span>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
