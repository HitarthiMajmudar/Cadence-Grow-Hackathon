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
import { Card, ErrorState, LoadingBlock, SectionTitle } from "@/components/ui";
import { cx, fmtDateTime, severityMeta } from "@/utils/format";

export function CaseDetailPage() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: c, isLoading, error, refetch } = useCase(caseId);
  const [storyOpen, setStoryOpen] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

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
      <button className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-200" onClick={() => navigate(-1)}>
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      {/* header */}
      <Card className="border-white/15">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="min-w-[260px] flex-1">
            <div className="flex items-center gap-2">
              <Link to={`/stocks/${c.symbol}`} className="font-mono text-xl font-extrabold hover:text-attention">
                {c.symbol}
              </Link>
              <span className="text-slate-500">{c.company_name}</span>
              <span className="text-xs text-slate-600">· {c.sector_name}</span>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <VerdictBadge verdict={c.verdict} />
              <Badge variant={sev.tone}>{sev.label} severity</Badge>
              <FreshnessBadge freshness={c.data_quality.freshness} />
              <span className="text-xs text-slate-500">
                detected {fmtDateTime(c.detection_timestamp)}
              </span>
            </div>
            <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-slate-200">
              {c.headline_explanation}
            </p>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">{c.explanation}</p>
          </div>
          <div className="flex flex-col items-center gap-2">
            <AttentionScore score={c.attention_score} confidence={c.confidence} size={132} />
            <div className="flex gap-1.5">
              <button className="btn-primary !px-3 !py-2 text-xs" onClick={() => setStoryOpen(true)}>
                <Share2 className="h-3.5 w-3.5" /> Story Card
              </button>
              <Link to={`/time-machine/${c.symbol}`} className="btn-ghost !px-3 !py-2 text-xs">
                <Rewind className="h-3.5 w-3.5" /> Replay
              </Link>
            </div>
          </div>
        </div>

        {/* status + feedback bar */}
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-white/10 pt-3">
          <span className="label">Status</span>
          {(["viewed", "saved", "dismissed"] as const).map((s) => {
            const Icon = s === "saved" ? Bookmark : s === "dismissed" ? Trash2 : Check;
            return (
              <button
                key={s}
                onClick={() => setStatus(s)}
                className={cx(
                  "chip capitalize",
                  c.status === s
                    ? "border-attention/40 bg-attention/10 text-attention"
                    : "border-white/10 bg-white/5 text-slate-400 hover:bg-white/10",
                )}
              >
                <Icon className="h-3 w-3" /> {s}
              </button>
            );
          })}
          <div className="ml-auto flex items-center gap-2">
            <span className="label">Was this useful?</span>
            <button
              onClick={() => sendFeedback("useful")}
              className={cx("chip", feedback === "useful" ? "border-gain/40 bg-gain/10 text-gain" : "border-white/10 bg-white/5 text-slate-400 hover:bg-white/10")}
            >
              <ThumbsUp className="h-3 w-3" />
            </button>
            <button
              onClick={() => sendFeedback("not_useful")}
              className={cx("chip", feedback === "not_useful" ? "border-risk/40 bg-risk/10 text-risk" : "border-white/10 bg-white/5 text-slate-400 hover:bg-white/10")}
            >
              <ThumbsDown className="h-3 w-3" />
            </button>
          </div>
        </div>
      </Card>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionTitle hint={`Comparison window · ${fmtDateTime(c.comparison_start)} → ${fmtDateTime(c.comparison_end)}`}>
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
            <div className="mt-3 rounded-lg border border-attention/25 bg-attention/5 p-3">
              <div className="text-xs font-semibold text-attention">Data-quality warnings</div>
              <ul className="mt-1 space-y-1 text-xs text-slate-400">
                {c.data_quality.warnings.map((w, i) => (
                  <li key={i}>· {w}</li>
                ))}
              </ul>
              {c.data_quality.conflict_detail && (
                <p className="mt-2 text-xs text-slate-400">{c.data_quality.conflict_detail}</p>
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
          <SectionTitle hint="What the Attention Score is made of">Score breakdown</SectionTitle>
          <ScoreBreakdown components={c.score_components} />
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
      <dt className="text-[11px] uppercase tracking-wide text-slate-500">{k}</dt>
      <dd className="font-mono font-semibold tabular-nums text-slate-100">{display}</dd>
    </div>
  );
}
