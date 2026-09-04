import type { Evidence, ScoreComponent } from "@/types";
import { Check, Minus, X } from "lucide-react";
import { InfoDot } from "./ui";
import { Progress } from "@/components/ui/progress";

const TERM_HELP: Record<string, string> = {
  price_surprise:
    "How far the price move is from this stock's own recent normal range. A z-score of 2 means about two standard deviations above normal.",
  volume_anomaly: "How elevated trading volume is versus its own 20-bar rolling average.",
  sector_divergence:
    "How much of the move is specific to this stock after removing what the rest of its sector did.",
  market_divergence:
    "How much of the move remains after removing what the market index did (beta-adjusted).",
  volatility_regime:
    "Whether bar-to-bar swings have expanded sharply — a stock that has become harder to price.",
  news_relevance_sentiment:
    "Change in local-news activity and the direction of that news relative to the price.",
  signal_agreement: "How many independent signals point the same way. More agreement = higher confidence.",
};

export function ScoreBreakdown({ components }: { components: ScoreComponent[] }) {
  return (
    <div className="space-y-2">
      {components.map((c) => {
        const pctFill = c.max_points > 0 ? (c.points / c.max_points) * 100 : 0;
        return (
          <div key={c.key} className="rounded-md border bg-muted/40 px-4 py-3">
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-1.5 font-medium">
                {c.label}
                {TERM_HELP[c.key] && <InfoDot text={TERM_HELP[c.key]} />}
              </span>
              <span className="tabular-nums text-muted-foreground">
                <span className="font-semibold text-foreground">{c.points.toFixed(1)}</span> /{" "}
                {c.max_points}
              </span>
            </div>
            <Progress value={pctFill} className="mt-1.5" />
            <p className="mt-1.5 text-xs text-muted-foreground">{c.detail}</p>
          </div>
        );
      })}
    </div>
  );
}

export function EvidenceList({ items, kind }: { items: Evidence[]; kind: "supporting" | "counter" }) {
  const Icon = kind === "supporting" ? Check : X;
  const color = kind === "supporting" ? "text-positive" : "text-primary";
  if (!items.length) {
    return (
      <p className="text-xs text-muted-foreground">
        <Minus className="mr-1 inline size-3" />
        None recorded.
      </p>
    );
  }
  return (
    <ul className="space-y-2">
      {items.map((e, i) => (
        <li key={i} className="flex gap-2">
          <Icon className={`mt-0.5 size-3.5 shrink-0 ${color}`} />
          <div>
            <div className="text-sm font-medium">{e.label}</div>
            <div className="text-xs text-muted-foreground">{e.detail}</div>
          </div>
        </li>
      ))}
    </ul>
  );
}
