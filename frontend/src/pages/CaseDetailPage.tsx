import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Bookmark,
  Check,
  Rewind,
  Share2,
  ThumbsDown,
  ThumbsUp,
  Trash2,
} from "lucide-react";
import { useCase } from "@/hooks/queries";
import { api } from "@/api/endpoints";
import { useQueryClient } from "@tanstack/react-query";
import { AttentionScore } from "@/components/AttentionScore";
import { EvidenceCourt } from "@/components/EvidenceCourt";
import { EvidenceList, ScoreBreakdown } from "@/components/ScoreBreakdown";
import { NewsTimeline } from "@/components/NewsTimeline";
import { PriceChart } from "@/components/charts";
import { VerdictBadge, FreshnessBadge } from "@/components/badges";
import { StoryCardModal } from "@/components/StoryCardModal";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, ErrorState, LoadingBlock, SectionTitle } from "@/components/ui";
import { CodeBlock } from "@/components/ai-elements/code-block";
import { MessageResponse as Response } from "@/components/ai-elements/message";
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/ai-elements/reasoning";
import { cn, fmtDateTime, severityMeta } from "@/utils/format";

export function CaseDetailPage() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: c, isLoading, error, refetch } = useCase(caseId);
  const [storyOpen, setStoryOpen] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [showRaw, setShowRaw] = useState(false);

  if (isLoading) return <LoadingBlock height={400} />;
  if (error || !c) return <ErrorState message={(error as Error)?.message} onRetry={() => refetch()} />;

  const sev = severityMeta(c.severity);

  const setStatus = async (status: string) => {
    await api.setCaseStatus(c.case_id, status);
    qc.invalidateQueries({ queryKey: ["case", c.case_id] });
    qc.invalidateQueries({ queryKey: ["cases"] });
    qc.invalidateQueries({ queryKey: ["cases", "recent"] });
  };

  const sendFeedback = async (kind: string) => {
    setFeedback(kind);
    await api.submitFeedback(c.case_id, kind);
  };

  return (
    <div className="space-y-5">
      <button
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        onClick={() => navigate(-1)}
      >
        <ArrowLeft className="size-4" /> Back
      </button>

      <Card>
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="min-w-[260px] flex-1">
            <div className="flex items-center gap-2">
              <Link
                to={`/stocks/${c.symbol}`}
                className="font-mono text-lg font-semibold hover:text-primary"
              >
                {c.symbol}
              </Link>
              <span className="text-muted-foreground">{c.company_name}</span>
              <span className="text-xs text-muted-foreground">· {c.sector_name}</span>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <VerdictBadge verdict={c.verdict} />
              <Badge variant={sev.tone}>{sev.label} severity</Badge>
              <FreshnessBadge freshness={c.data_quality.freshness} />
              <span className="text-xs text-muted-foreground">
                detected {fmtDateTime(c.detection_timestamp)}
              </span>
            </div>
            <div className="mt-3 max-w-2xl text-sm text-foreground">
              <Response>{c.headline_explanation}</Response>
            </div>
            <div className="mt-2 max-w-2xl text-sm text-muted-foreground">
              <Response>{c.explanation}</Response>
            </div>
            {c.verdict_reason && (
              <Reasoning defaultOpen={false} className="mt-3">
                <ReasoningTrigger>How the verdict tree reached this</ReasoningTrigger>
                <ReasoningContent>{c.verdict_reason}</ReasoningContent>
              </Reasoning>
            )}
          </div>
          <div className="flex flex-col items-center gap-2">
            <AttentionScore score={c.attention_score} confidence={c.confidence} size={132} />
            <div className="flex gap-1.5">
              <button className={cn(buttonVariants({ size: "sm" }), "gap-1.5")} onClick={() => setStoryOpen(true)}>
                <Share2 /> Story Card
              </button>
              <Link
                to={`/time-machine/${c.symbol}`}
                className={cn(buttonVariants({ variant: "outline", size: "sm" }), "gap-1.5")}
              >
                <Rewind /> Replay
              </Link>
            </div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2 border-t pt-3">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Status
          </span>
          {(["viewed", "saved", "dismissed"] as const).map((s) => {
            const Icon = s === "saved" ? Bookmark : s === "dismissed" ? Trash2 : Check;
            return (
              <Button
                key={s}
                size="xs"
                variant={c.status === s ? "default" : "outline"}
                className="capitalize"
                onClick={() => setStatus(s)}
              >
                <Icon /> {s}
              </Button>
            );
          })}
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Was this useful?
            </span>
            <Button
              size="icon-xs"
              variant={feedback === "useful" ? "default" : "outline"}
              onClick={() => sendFeedback("useful")}
            >
              <ThumbsUp />
            </Button>
            <Button
              size="icon-xs"
              variant={feedback === "not_useful" ? "destructive" : "outline"}
              onClick={() => sendFeedback("not_useful")}
            >
              <ThumbsDown />
            </Button>
          </div>
        </div>
      </Card>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionTitle
            hint={`Comparison window · ${fmtDateTime(c.comparison_start)} → ${fmtDateTime(c.comparison_end)}`}
          >
            Price during the case window
          </SectionTitle>
          <PriceChart
            data={c.price_series.map((p) => ({ timestamp: p.timestamp, close: p.close }))}
            anomalies={[{ timestamp: c.detection_timestamp, level: "serious" }]}
            newsMarks={c.related_news.map((n) => ({ timestamp: n.timestamp }))}
          />
        </Card>

        <Card>
          <SectionTitle hint="Key statistics at detection">Metrics</SectionTitle>
          <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
            <Metric k="Return z-score" v={c.metrics.return_zscore} />
            <Metric k="Volume ratio" v={c.metrics.volume_ratio} suffix="x" />
            <Metric k="Sector-adj move" v={c.metrics.sector_adj_cum} pct />
            <Metric k="Market-adj move" v={c.metrics.market_adj_cum} pct />
            <Metric k="Volatility ratio" v={c.metrics.volatility_ratio} suffix="x" />
            <Metric k="Drawdown" v={c.metrics.drawdown} pct />
            <Metric k="Iso-forest score" v={c.metrics.iso_forest_score} />
            <Metric k="News in window" v={c.metrics.news_count} int />
          </dl>
          {c.data_quality.warnings.length > 0 && (
            <div className="mt-3 rounded-md border border-warning/40 bg-warning/10 p-3">
              <div className="text-xs font-medium text-warning-foreground">Data-quality warnings</div>
              <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                {c.data_quality.warnings.map((w, i) => (
                  <li key={i}>· {w}</li>
                ))}
              </ul>
              {c.data_quality.conflict_detail && (
                <p className="mt-2 text-xs text-muted-foreground">{c.data_quality.conflict_detail}</p>
              )}
            </div>
          )}
        </Card>
      </div>

      <Card>
        <EvidenceCourt findings={c.detectives} verdict={c.verdict} tally={c.court_tally} />
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <SectionTitle
            hint="What the Attention Score is made of"
            right={
              <Button variant="ghost" size="xs" onClick={() => setShowRaw((v) => !v)}>
                {showRaw ? "Hide raw" : "Raw JSON"}
              </Button>
            }
          >
            Score breakdown
          </SectionTitle>
          {showRaw ? (
            <CodeBlock
              language="json"
              code={JSON.stringify(c.score_components, null, 2)}
            />
          ) : (
            <ScoreBreakdown components={c.score_components} />
          )}
        </Card>
        <div className="space-y-5">
          <Card>
            <SectionTitle>Supporting evidence</SectionTitle>
            <EvidenceList items={c.supporting_evidence} kind="supporting" />
          </Card>
          <Card>
            <SectionTitle>Counter-evidence</SectionTitle>
            <EvidenceList items={c.counter_evidence} kind="counter" />
          </Card>
        </div>
      </div>

      <Card>
        <SectionTitle hint="Local headlines around the detection time — markers on the chart line up with these">
          Related local news
        </SectionTitle>
        <NewsTimeline news={c.related_news} detectionTs={c.detection_timestamp} />
      </Card>

      {storyOpen && <StoryCardModal caseId={c.case_id} onClose={() => setStoryOpen(false)} />}
    </div>
  );
}

function Metric({
  k,
  v,
  pct: isPct,
  int,
  suffix,
}: {
  k: string;
  v: number | undefined;
  pct?: boolean;
  int?: boolean;
  suffix?: string;
}) {
  let display = "—";
  if (v !== undefined && v !== null && !Number.isNaN(v)) {
    if (isPct) display = `${(v * 100).toFixed(2)}%`;
    else if (int) display = String(Math.round(v));
    else display = v.toFixed(2) + (suffix ?? "");
  }
  return (
    <div className="flex flex-col">
      <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{k}</dt>
      <dd className="font-mono font-semibold tabular-nums">{display}</dd>
    </div>
  );
}
