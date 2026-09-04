import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Rewind, Share2 } from "lucide-react";
import {
  useComparison,
  useStockCases,
  useStockHistory,
  useStockNews,
  useStockState,
  useStocks,
} from "@/hooks/queries";
import { AttentionScore } from "@/components/AttentionScore";
import { ComparisonChart, PriceChart, VolumeChart } from "@/components/charts";
import { NewsTimeline } from "@/components/NewsTimeline";
import { CaseCard } from "@/components/CaseCard";
import { VerdictBadge, FreshnessBadge } from "@/components/badges";
import { StoryCardModal } from "@/components/StoryCardModal";
import { Card, EmptyState, LoadingBlock, SectionTitle, StatTile } from "@/components/ui";
import { buttonVariants } from "@/components/ui/button";
import { cn, money, pct, priceDirClass, compactNumber } from "@/utils/format";

export function StockDetailPage() {
  const { symbol = "" } = useParams();
  const { data: state, isLoading } = useStockState(symbol);
  const { data: history } = useStockHistory(symbol);
  const { data: comparison } = useComparison(symbol, 90);
  const { data: news } = useStockNews(symbol);
  const { data: cases } = useStockCases(symbol);
  const { data: stocksMeta } = useStocks();
  const [storyCaseId, setStoryCaseId] = useState<string | null>(null);

  const meta = stocksMeta?.find((s) => s.symbol === symbol);

  if (isLoading || !state) return <LoadingBlock height={360} />;

  const candles = history?.candles ?? [];
  const priceData = candles.map((c) => ({ timestamp: c.timestamp, close: c.close }));
  const volData = candles.map((c) => ({ timestamp: c.timestamp, volume: c.volume }));
  const openCase = cases?.cases?.[0];

  return (
    <div className="space-y-5">
      <Link to="/" className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Investigation Room
      </Link>

      <Card>
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="font-mono text-xl font-semibold">{state.symbol}</h1>
              <FreshnessBadge freshness={state.freshness} />
            </div>
            <p className="mt-0.5 text-sm text-muted-foreground">
              {state.name} · {state.sector_name}
            </p>
            <div className="mt-3 flex items-end gap-3">
              <span className="text-3xl font-semibold tabular-nums">{money(state.price)}</span>
              <span className={cn("pb-1 text-sm font-semibold", priceDirClass(state.change_pct))}>
                {pct(state.change_pct)} ({money(state.change_abs)})
              </span>
            </div>
            {state.verdict && (
              <div className="mt-2">
                <VerdictBadge verdict={state.verdict} />
              </div>
            )}
          </div>
          <div className="flex flex-col items-center gap-2">
            <AttentionScore score={state.attention_score} confidence={state.confidence} size={120} />
            <div className="flex gap-1.5">
              <Link
                to={`/time-machine/${symbol}`}
                className={cn(buttonVariants({ variant: "outline", size: "sm" }), "gap-1.5")}
              >
                <Rewind /> Time Machine
              </Link>
              {openCase && (
                <button
                  className={cn(buttonVariants({ size: "sm" }), "gap-1.5")}
                  onClick={() => setStoryCaseId(openCase.case_id)}
                >
                  <Share2 /> Story Card
                </button>
              )}
            </div>
          </div>
        </div>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Day volume" value={compactNumber(state.day_volume)} />
        <StatTile
          label="Stock-specific move"
          value={
            comparison
              ? `${(comparison.stock_return_pct - comparison.sector_return_pct).toFixed(2)}%`
              : "—"
          }
          sub="stock minus sector"
          tone="neutral"
        />
        <StatTile
          label="Sector return"
          value={comparison ? `${comparison.sector_return_pct.toFixed(2)}%` : "—"}
        />
        <StatTile
          label="Market return"
          value={comparison ? `${comparison.market_return_pct.toFixed(2)}%` : "—"}
        />
      </div>

      {openCase && (
        <Card className="border-primary/40">
          <SectionTitle hint="The most relevant open Investigation Case for this stock">
            Current verdict
          </SectionTitle>
          <CaseCard c={openCase} />
        </Card>
      )}

      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionTitle hint="Amber / red dots are detected anomalies; dashed lines are local headlines">
            Price
          </SectionTitle>
          <PriceChart
            data={priceData}
            anomalies={(cases?.cases ?? []).map((c) => ({
              timestamp: c.detection_timestamp,
              level: c.severity === "critical" || c.severity === "high" ? "serious" : "moderate",
            }))}
            newsMarks={(news?.news ?? []).map((n) => ({ timestamp: n.timestamp }))}
            height={260}
          />
          <div className="mt-2">
            <SectionTitle>Volume</SectionTitle>
            <VolumeChart data={volData} height={110} />
          </div>
        </Card>

        <Card>
          <SectionTitle hint="Company profile">{state.name}</SectionTitle>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {meta?.summary ?? "Company profile unavailable in this dataset."}
          </p>
          <div className="mt-3 space-y-1.5 text-xs text-muted-foreground">
            <div>Sector: {state.sector_name}</div>
            <div>Latest dataset price as of {state.as_of.slice(0, 16).replace("T", " ")}</div>
            <div>Data source freshness: {state.freshness}</div>
          </div>
        </Card>
      </div>

      <Card>
        <SectionTitle
          hint="Rebased to 100 at the window start — did the stock, its sector or the market move first?"
          right={
            comparison?.who_moved_first ? (
              <span className="text-xs text-muted-foreground">
                first mover:{" "}
                <span className="font-semibold capitalize text-primary">
                  {comparison.who_moved_first}
                </span>
              </span>
            ) : null
          }
        >
          Stock vs sector vs market
        </SectionTitle>
        {comparison ? (
          <ComparisonChart
            data={comparison.points.map((p) => ({
              timestamp: p.timestamp,
              stock_indexed: p.stock_indexed,
              sector_indexed: p.sector_indexed,
              market_indexed: p.market_indexed,
            }))}
            labels={{ stock: state.symbol, sector: state.sector_name, market: comparison.market_index }}
          />
        ) : (
          <LoadingBlock height={200} />
        )}
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <SectionTitle hint="Local headlines associated with this company">Related local news</SectionTitle>
          <NewsTimeline news={news?.news ?? []} />
        </Card>
        <Card>
          <SectionTitle hint="Every Investigation Case detected for this stock up to now">
            Historical cases
          </SectionTitle>
          <div className="space-y-3">
            {(cases?.cases ?? []).length === 0 && (
              <EmptyState
                title="No cases yet"
                message="Nothing unusual has been detected for this stock in the dataset so far."
              />
            )}
            {(cases?.cases ?? []).map((c) => (
              <CaseCard key={c.case_id} c={c} dense />
            ))}
          </div>
        </Card>
      </div>

      {storyCaseId && <StoryCardModal caseId={storyCaseId} onClose={() => setStoryCaseId(null)} />}
    </div>
  );
}
