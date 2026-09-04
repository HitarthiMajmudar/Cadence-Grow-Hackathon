import { Gavel, Newspaper, TrendingUp, Users, BarChart3 } from "lucide-react";
import type { DetectiveFinding } from "@/types";
import { cx } from "@/utils/format";

const ICONS = {
  stock: TrendingUp,
  volume: BarChart3,
  sector: Users,
  news: Newspaper,
};

const STATUS_META = {
  supports: { label: "Supports", cls: "text-attention border-attention/40 bg-attention/10" },
  opposes: { label: "Explains it", cls: "text-neutralc-soft border-neutralc/30 bg-neutralc/10" },
  inconclusive: { label: "Inconclusive", cls: "text-slate-400 border-white/10 bg-white/5" },
};

export function EvidenceCourt({
  findings,
  verdict,
  tally,
}: {
  findings: DetectiveFinding[];
  verdict: string;
  tally?: { supports: number; opposes: number; inconclusive: number };
}) {
  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <Gavel className="h-4 w-4 text-attention" />
        <h3 className="text-sm font-bold uppercase tracking-wide text-slate-200">Evidence Court</h3>
        {tally && (
          <span className="ml-auto text-xs text-slate-500">
            {tally.supports} support · {tally.opposes} explain · {tally.inconclusive} unclear
          </span>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {findings.map((f) => {
          const Icon = ICONS[f.key];
          const sm = STATUS_META[f.status];
          return (
            <div key={f.key} className="glass-soft p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-bold text-slate-200">
                  <Icon className="h-4 w-4 text-slate-400" />
                  {f.detective}
                </div>
                <span className={cx("chip", sm.cls)}>{sm.label}</span>
              </div>
              <p className="mt-2 text-sm text-slate-300">{f.finding}</p>
              <ul className="mt-2 space-y-1">
                {f.evidence.map((e, i) => (
                  <li key={i} className="flex gap-1.5 text-xs text-slate-500">
                    <span className="text-slate-600">·</span>
                    {e}
                  </li>
                ))}
              </ul>
              <div className="mt-2 flex items-center gap-2">
                <div className="h-1 flex-1 overflow-hidden rounded-full bg-white/10">
                  <div className="h-full rounded-full bg-slate-500" style={{ width: `${f.confidence}%` }} />
                </div>
                <span className="text-[10px] text-slate-500">{Math.round(f.confidence)}%</span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-3 flex items-center gap-2 rounded-xl border border-attention/25 bg-attention/5 px-4 py-3">
        <Gavel className="h-4 w-4 text-attention" />
        <span className="text-xs text-slate-400">Combined verdict:</span>
        <span className="text-sm font-bold text-attention">{verdict}</span>
      </div>
    </div>
  );
}
