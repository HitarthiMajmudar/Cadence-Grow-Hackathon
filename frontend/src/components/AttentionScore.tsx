import { scoreColor, cx } from "@/utils/format";

interface Props {
  score: number;
  confidence?: number;
  size?: number;
  label?: string;
  className?: string;
}

/** Circular Attention-Score gauge (0-100). */
export function AttentionScore({ score, confidence, size = 116, label = "Attention", className }: Props) {
  const stroke = size >= 100 ? 9 : 7;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, score));
  const dash = (clamped / 100) * c;
  const color = scoreColor(clamped);

  return (
    <div className={cx("relative inline-flex flex-col items-center", className)}>
      <svg width={size} height={size} className="-rotate-90" role="img" aria-label={`${label} score ${Math.round(clamped)} of 100`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${c - dash}`}
          style={{ transition: "stroke-dasharray 0.6s ease, stroke 0.3s" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-extrabold tabular-nums" style={{ color }}>
          {Math.round(clamped)}
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>
      </div>
      {confidence !== undefined && (
        <div className="mt-1 text-[11px] text-slate-500">
          {Math.round(confidence)}% confidence
        </div>
      )}
    </div>
  );
}

export function AttentionMeter({ score, className }: { score: number; className?: string }) {
  const clamped = Math.max(0, Math.min(100, score));
  return (
    <div className={cx("flex items-center gap-2", className)}>
      <div className="h-2 w-24 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${clamped}%`, background: scoreColor(clamped) }}
        />
      </div>
      <span className="w-7 text-right text-xs font-bold tabular-nums" style={{ color: scoreColor(clamped) }}>
        {Math.round(clamped)}
      </span>
    </div>
  );
}
