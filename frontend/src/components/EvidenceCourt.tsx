import { Gavel, Newspaper, TrendingUp, Users, BarChart3 } from "lucide-react";
import type { DetectiveFinding } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

const ICONS = {
  stock: TrendingUp,
  volume: BarChart3,
  sector: Users,
  news: Newspaper,
};

const STATUS_META: Record<string, { label: string; tone: "warning" | "default" | "secondary" }> = {
  supports: { label: "Supports", tone: "warning" },
  opposes: { label: "Explains it", tone: "default" },
  inconclusive: { label: "Inconclusive", tone: "secondary" },
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
        <Gavel className="size-4 text-primary" />
        <h3 className="text-sm font-semibold tracking-tight">Evidence Court</h3>
        {tally && (
          <span className="ml-auto text-xs text-muted-foreground">
            {tally.supports} support · {tally.opposes} explain · {tally.inconclusive} unclear
          </span>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {findings.map((f) => {
          const Icon = ICONS[f.key];
          const sm = STATUS_META[f.status] ?? STATUS_META.inconclusive;
          return (
            <div key={f.key} className="rounded-md border bg-muted/40 p-4">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Icon className="size-4 text-muted-foreground" />
                  {f.detective}
                </div>
                <Badge variant={sm.tone}>{sm.label}</Badge>
              </div>
              <p className="mt-2 text-xs text-foreground/80">{f.finding}</p>
              <ul className="mt-2 space-y-1">
                {f.evidence.map((e, i) => (
                  <li key={i} className="flex gap-1.5 text-xs text-muted-foreground">
                    <span>·</span>
                    {e}
                  </li>
                ))}
              </ul>
              <div className="mt-2 flex items-center gap-2">
                <Progress value={f.confidence} className="flex-1" />
                <span className="text-[10px] text-muted-foreground tabular-nums">
                  {Math.round(f.confidence)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-3 flex items-center gap-2 rounded-md border border-primary/30 bg-primary/5 px-4 py-3">
        <Gavel className="size-4 text-primary" />
        <span className="text-xs text-muted-foreground">Combined verdict:</span>
        <span className="text-sm font-semibold text-primary">{verdict}</span>
      </div>
    </div>
  );
}
