import { forwardRef } from "react";
import type { StoryCardData } from "@/types";
import { Sparkline } from "./Sparkline";
import { fmtDate, scoreColor } from "@/utils/format";

export const StoryCard = forwardRef<HTMLDivElement, { data: StoryCardData }>(({ data }, ref) => {
  const color = scoreColor(data.attention_score);
  return (
    <div
      ref={ref}
      className="relative w-[440px] overflow-hidden rounded-2xl border border-white/10 p-6 text-slate-100"
      style={{
        background:
          "radial-gradient(600px 300px at 0% 0%, rgba(245,165,36,0.16), transparent 60%), radial-gradient(500px 260px at 100% 10%, rgba(34,211,238,0.14), transparent 55%), #0b1220",
      }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg border border-attention/40 bg-attention/10">
            <span className="text-sm">🔍</span>
          </div>
          <div>
            <div className="text-xs font-extrabold tracking-tight">MARKET DETECTIVE</div>
            <div className="text-[10px] text-slate-500">Your stocks moved. We investigated why.</div>
          </div>
        </div>
        <div className="text-right">
          <div className="font-mono text-lg font-bold">{data.symbol}</div>
          <div className="text-[10px] text-slate-500">{fmtDate(data.event_date)}</div>
        </div>
      </div>

      <div className="mt-5 flex items-end gap-4">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Attention Score</div>
          <div className="text-5xl font-extrabold tabular-nums" style={{ color }}>
            {Math.round(data.attention_score)}
          </div>
          <div className="text-[10px] text-slate-500">{Math.round(data.confidence)}% confidence</div>
        </div>
        <div className="flex-1">
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Verdict</div>
          <div className="rounded-lg border border-attention/30 bg-attention/10 px-3 py-2 text-sm font-bold text-attention">
            {data.verdict}
          </div>
        </div>
      </div>

      <p className="mt-4 text-sm leading-relaxed text-slate-200">{data.one_line}</p>

      <div className="mt-4">
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Main evidence</div>
        <ul className="space-y-1">
          {data.main_evidence.map((e, i) => (
            <li key={i} className="flex gap-1.5 text-xs text-slate-400">
              <span style={{ color }}>▸</span>
              {e}
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-4 rounded-lg border border-white/5 bg-white/5 p-2">
        <Sparkline data={data.sparkline} width={392} height={44} strokeWidth={2} />
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-3 text-[10px] text-slate-500">
        <span>{data.dataset_label}</span>
        <span className="font-semibold text-slate-400">{data.disclaimer}</span>
      </div>
    </div>
  );
});
StoryCard.displayName = "StoryCard";
