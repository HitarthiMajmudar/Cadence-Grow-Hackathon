import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ChevronsRight,
  Flag,
  Gauge,
  Newspaper,
  Pause,
  Play,
  RotateCcw,
  StepForward,
  Zap,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { useReplay, useWatchlists, useClock } from "@/hooks/queries";
import { useReplayPlayer } from "@/hooks/useReplayPlayer";
import { useChartColors } from "@/lib/chart-colors";
import { StockSearch } from "@/components/StockSearch";
import { AttentionScore } from "@/components/AttentionScore";
import { VerdictBadge, OfflineDatasetBadge } from "@/components/badges";
import { Card as UICard, LoadingBlock, SectionTitle } from "@/components/ui";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn, fmtDateTime, scoreColor } from "@/utils/format";
import type { ReplayFrame } from "@/types";

const LABEL = "text-xs font-medium uppercase tracking-wider text-muted-foreground";

const WINDOWS = [
  { v: 35, label: "~1 trading week" },
  { v: 65, label: "~2 trading weeks" },
  { v: 110, label: "~3 trading weeks" },
  { v: 160, label: "~1 trading month" },
  { v: 240, label: "~7 trading weeks" },
];

export function TimeMachinePage() {
  const { symbol: routeSymbol } = useParams();
  const navigate = useNavigate();
  const { data: watchlists } = useWatchlists();
  const { data: clock } = useClock();
  const c = useChartColors();
  const axis = { fontSize: 11, fill: c.axis };

  const fallback = watchlists?.[0]?.symbols?.[0] ?? "TATAMOTORS";
  const symbol = routeSymbol ?? fallback;
  const [lookback, setLookback] = useState(65);

  const { data: replay, isLoading } = useReplay(symbol, lookback);
  const frames = useMemo(() => replay?.frames ?? [], [replay]);
  const player = useReplayPlayer(frames.length);
  const { index } = player;

  const cur: ReplayFrame | undefined = frames[index];
  const shown = useMemo(() => frames.slice(0, index + 1), [frames, index]);

  useEffect(() => {
    if (frames.length > 0 && index === 0 && !player.playing) {
      const t = setTimeout(() => player.play(), 400);
      return () => clearTimeout(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frames.length]);

  const priceData = shown.map((f) => ({ timestamp: f.timestamp, close: f.close }));
  const volData = shown.map((f) => ({ timestamp: f.timestamp, volume: f.volume }));
  const compData = shown.map((f) => ({
    timestamp: f.timestamp,
    stock: f.stock_indexed,
    sector: f.sector_indexed,
    market: f.market_indexed,
  }));

  const visibleAnomalies = (replay?.anomaly_markers ?? []).filter((a) => a.frame_index <= index);
  const visibleNews = (replay?.news_markers ?? []).filter((n) => n.frame_index <= index);
  const flashNews = visibleNews.find((n) => n.frame_index === index);
  const flashAnomaly = cur?.anomaly_level === "serious" && cur.is_anomaly;

  const yPrice = useMemo<[number | string, number | string]>(() => {
    const all = frames.map((f) => f.close).filter((x): x is number => x != null);
    if (!all.length) return ["auto", "auto"];
    const min = Math.min(...all);
    const max = Math.max(...all);
    const pad = (max - min) * 0.08 || 1;
    return [min - pad, max + pad];
  }, [frames]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold tracking-tight">
            <Zap className="size-5 text-primary" /> Market Time Machine
          </h1>
          <p className="text-sm text-muted-foreground">
            An animated replay of what happened between two points in the research dataset.
          </p>
        </div>
        <OfflineDatasetBadge label={replay?.dataset_label} />
      </div>

      <UICard className="p-4">
        <div className="grid gap-4 sm:grid-cols-[1fr_auto_auto]">
          <div>
            <span className={LABEL}>Stock</span>
            <div className="mt-1">
              <StockSearch
                onPick={(s) => navigate(`/time-machine/${s.symbol}`)}
                placeholder={`Replaying ${symbol} — pick another`}
              />
            </div>
          </div>
          <div>
            <span className={LABEL}>Window</span>
            <Select value={String(lookback)} onValueChange={(v) => v && setLookback(Number(v))}>
              <SelectTrigger className="mt-1">
                <SelectValue>
                  {(v) => WINDOWS.find((w) => String(w.v) === v)?.label ?? v}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {WINDOWS.map((w) => (
                  <SelectItem key={w.v} value={String(w.v)}>
                    {w.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <span className={LABEL}>Ends at</span>
            <div className="mt-1 flex h-8 items-center rounded-none border bg-background px-2.5 font-mono text-xs text-muted-foreground">
              {fmtDateTime(clock?.current_dataset_timestamp)}
            </div>
          </div>
        </div>
      </UICard>

      {isLoading && <LoadingBlock height={420} />}

      {replay && cur && (
        <>
          <UICard className="p-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-1.5">
                <Button variant="outline" size="icon-sm" onClick={player.stepBack} title="Step back">
                  <StepForward className="-scale-x-100" />
                </Button>
                {player.playing ? (
                  <Button size="sm" onClick={player.pause}>
                    <Pause /> Pause
                  </Button>
                ) : (
                  <Button size="sm" onClick={player.play}>
                    <Play /> {player.atEnd ? "Replay" : "Play"}
                  </Button>
                )}
                <Button variant="outline" size="icon-sm" onClick={player.stepForward} title="Step forward">
                  <StepForward />
                </Button>
                <Button variant="outline" size="icon-sm" onClick={player.restart} title="Restart">
                  <RotateCcw />
                </Button>
              </div>

              <div className="flex items-center gap-1">
                <span className={cn(LABEL, "mr-1")}>Speed</span>
                {player.speeds.map((s) => (
                  <button
                    key={s}
                    onClick={() => player.setSpeed(s)}
                    className={cn(
                      "rounded-none px-2 py-1 text-xs font-semibold",
                      player.speed === s
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground hover:bg-accent",
                    )}
                  >
                    {s}×
                  </button>
                ))}
              </div>

              <div className="ml-auto font-mono text-sm text-muted-foreground">
                {fmtDateTime(cur.timestamp)}
              </div>
            </div>

            <div className="mt-3">
              <input
                type="range"
                min={0}
                max={frames.length - 1}
                value={index}
                onChange={(e) => player.seek(Number(e.target.value))}
                className="w-full accent-primary"
                aria-label="Replay timeline"
              />
              <div className="relative mt-1 h-3">
                {replay.anomaly_markers.map((a, i) => (
                  <span
                    key={`a${i}`}
                    className={cn(
                      "absolute top-0 h-2.5 w-1 -translate-x-1/2 rounded-full",
                      a.level === "serious" ? "bg-negative" : "bg-warning",
                    )}
                    style={{ left: `${(a.frame_index / (frames.length - 1)) * 100}%` }}
                    title={a.label}
                  />
                ))}
                {replay.news_markers.map((n, i) => (
                  <span
                    key={`n${i}`}
                    className="absolute top-0 h-2.5 w-0.5 -translate-x-1/2"
                    style={{
                      left: `${(n.frame_index / (frames.length - 1)) * 100}%`,
                      background: c.news,
                    }}
                    title={n.headline}
                  />
                ))}
              </div>
            </div>
          </UICard>

          <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
            <div className="space-y-4">
              <Card
                className={cn(
                  "p-4 transition-shadow",
                  flashAnomaly && !player.reduced && "ring-2 ring-negative",
                )}
              >
                <SectionTitle
                  right={
                    <span className="flex items-center gap-2 text-xs">
                      {flashNews && (
                        <Badge variant="outline" className="gap-1">
                          <Newspaper /> headline now
                        </Badge>
                      )}
                      <VerdictBadge verdict={cur.verdict} />
                    </span>
                  }
                >
                  {replay.company_name} — price
                </SectionTitle>
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={priceData} margin={{ top: 6, right: 12, bottom: 0, left: 0 }}>
                    <CartesianGrid stroke={c.grid} vertical={false} />
                    <XAxis
                      dataKey="timestamp"
                      tick={axis}
                      tickFormatter={(t) => fmtDateTime(t).slice(0, 6)}
                      minTickGap={44}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={axis}
                      domain={yPrice}
                      width={54}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(v) => `₹${Math.round(v)}`}
                    />
                    <Area
                      type="monotone"
                      dataKey="close"
                      stroke={c.stock}
                      strokeWidth={2.2}
                      fill={c.stock}
                      fillOpacity={0.1}
                      isAnimationActive={false}
                      connectNulls
                    />
                    {visibleNews.map((n, i) => (
                      <ReferenceLine
                        key={`nl${i}`}
                        x={n.timestamp}
                        stroke={c.news}
                        strokeDasharray="2 3"
                        strokeOpacity={0.55}
                      />
                    ))}
                    {visibleAnomalies.map((a, i) => {
                      const f = frames[a.frame_index];
                      return (
                        <ReferenceDot
                          key={`ad${i}`}
                          x={f?.timestamp}
                          y={f?.close ?? undefined}
                          r={a.level === "serious" ? 6 : 4}
                          fill={a.level === "serious" ? c.negative : c.warning}
                          stroke={c.surface}
                          strokeWidth={1.5}
                          isFront
                        />
                      );
                    })}
                    {cur.close != null && (
                      <ReferenceDot
                        x={cur.timestamp}
                        y={cur.close}
                        r={3.5}
                        fill={c.axis}
                        stroke={c.surface}
                        strokeWidth={1.5}
                        isFront
                      />
                    )}
                  </AreaChart>
                </ResponsiveContainer>
              </Card>

              <div className="grid gap-4 sm:grid-cols-2">
                <Card className="p-4">
                  <SectionTitle>Volume</SectionTitle>
                  <ResponsiveContainer width="100%" height={130}>
                    <BarChart data={volData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                      <CartesianGrid stroke={c.grid} vertical={false} />
                      <XAxis dataKey="timestamp" hide />
                      <YAxis
                        tick={axis}
                        width={46}
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={(v) =>
                          v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : `${Math.round(v / 1e3)}k`
                        }
                      />
                      <Bar dataKey="volume" fill={c.market} fillOpacity={0.5} radius={[2, 2, 0, 0]} isAnimationActive={false} />
                    </BarChart>
                  </ResponsiveContainer>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {cur.volume_ratio.toFixed(2)}× rolling average
                  </div>
                </Card>
                <Card className="p-4">
                  <SectionTitle right={<span className="text-[11px] text-muted-foreground">rebased to 100</span>}>
                    Stock vs sector vs market
                  </SectionTitle>
                  <ResponsiveContainer width="100%" height={130}>
                    <LineChart data={compData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                      <CartesianGrid stroke={c.grid} vertical={false} />
                      <XAxis dataKey="timestamp" hide />
                      <YAxis tick={axis} width={38} axisLine={false} tickLine={false} domain={["auto", "auto"]} />
                      <ReferenceLine y={100} stroke={c.grid} />
                      <Line type="monotone" dataKey="stock" stroke={c.stock} strokeWidth={2.2} dot={false} isAnimationActive={false} />
                      <Line type="monotone" dataKey="sector" stroke={c.sector} strokeWidth={1.5} dot={false} isAnimationActive={false} />
                      <Line type="monotone" dataKey="market" stroke={c.market} strokeWidth={1.3} strokeDasharray="4 3" dot={false} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                  <div className="mt-1 flex gap-3 text-[11px] text-muted-foreground">
                    <span style={{ color: c.stock }}>■ stock</span>
                    <span style={{ color: c.sector }}>■ sector</span>
                    <span>■ market</span>
                  </div>
                </Card>
              </div>
            </div>

            <div className="space-y-4">
              <Card className="items-center p-4">
                <AttentionScore score={cur.attention_score} confidence={cur.confidence} size={128} />
                <div className="mt-2 text-center">
                  <VerdictBadge verdict={cur.verdict} />
                </div>
                <div className="mt-3 grid w-full grid-cols-2 gap-2 text-center text-xs">
                  <div className="rounded-md border bg-muted/40 py-2">
                    <div className={LABEL}>Return z</div>
                    <div
                      className="font-mono font-semibold"
                      style={{ color: scoreColor(Math.abs(cur.return_zscore) * 15) }}
                    >
                      {cur.return_zscore >= 0 ? "+" : ""}
                      {cur.return_zscore.toFixed(1)}
                    </div>
                  </div>
                  <div className="rounded-md border bg-muted/40 py-2">
                    <div className={LABEL}>Freshness</div>
                    <div className="font-semibold capitalize">{cur.freshness}</div>
                  </div>
                </div>
              </Card>

              <UICard>
                <SectionTitle hint={replay.first_mover_detail || undefined}>
                  <span className="flex items-center gap-2">
                    <Flag className="size-4 text-primary" /> Who moved first?
                  </span>
                </SectionTitle>
                <div className="flex items-center gap-2 text-base font-semibold capitalize">
                  <ChevronsRight className="size-5 text-primary" />
                  {replay.who_moved_first ?? "no clear leader"}
                </div>
              </UICard>

              <UICard>
                <SectionTitle>
                  <span className="flex items-center gap-2">
                    <Gauge className="size-4 text-muted-foreground" /> Anomalies so far
                  </span>
                </SectionTitle>
                <div className="space-y-2">
                  {visibleAnomalies.length === 0 && (
                    <p className="text-sm text-muted-foreground">Calm so far. Keep playing.</p>
                  )}
                  {visibleAnomalies.map((a, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between rounded-md border bg-card px-3 py-2 text-xs"
                    >
                      <span className="flex items-center gap-2">
                        <span
                          className={cn(
                            "size-2 rounded-full",
                            a.level === "serious" ? "bg-negative" : "bg-warning",
                          )}
                        />
                        {a.verdict}
                      </span>
                      {a.case_id ? (
                        <Link to={`/cases/${a.case_id}`} className="text-primary hover:underline">
                          open →
                        </Link>
                      ) : (
                        <span className="text-muted-foreground">
                          {fmtDateTime(a.timestamp).slice(0, 6)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </UICard>

              {flashNews && (
                <Card className="animate-in fade-in slide-in-from-bottom-2 border-primary/30 bg-primary/5 p-4">
                  <div className="flex items-center gap-2 text-xs font-medium text-primary">
                    <Newspaper className="size-3.5" /> Local headline · {fmtDateTime(flashNews.timestamp)}
                  </div>
                  <p className="mt-1 text-sm text-foreground">{flashNews.headline}</p>
                  <div className="mt-1 text-[11px] text-muted-foreground">
                    {flashNews.event_type} · {flashNews.sentiment_label}
                  </div>
                </Card>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
