import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Link } from "react-router-dom";
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
import { StockSearch } from "@/components/StockSearch";
import { AttentionScore } from "@/components/AttentionScore";
import { VerdictBadge, OfflineDatasetBadge } from "@/components/badges";
import { Card, LoadingBlock, SectionTitle } from "@/components/ui";
import { cx, fmtDateTime, scoreColor } from "@/utils/format";
import type { ReplayFrame } from "@/types";

const AXIS = { fontSize: 11, fill: "#64748b" };
const GRID = "rgba(255,255,255,0.06)";

export function TimeMachinePage() {
  const { symbol: routeSymbol } = useParams();
  const navigate = useNavigate();
  const { data: watchlists } = useWatchlists();
  const { data: clock } = useClock();

  const fallback = watchlists?.[0]?.symbols?.[0] ?? "TATAMOTORS";
  const symbol = routeSymbol ?? fallback;
  const [lookback, setLookback] = useState(65);

  const { data: replay, isLoading } = useReplay(symbol, lookback);
  const frames = useMemo(() => replay?.frames ?? [], [replay]);
  const player = useReplayPlayer(frames.length);
  const { index } = player;

  const cur: ReplayFrame | undefined = frames[index];
  const shown = useMemo(() => frames.slice(0, index + 1), [frames, index]);

  // auto-play once loaded
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
    const all = frames.map((f) => f.close).filter((c): c is number => c != null);
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
          <h1 className="flex items-center gap-2 text-2xl font-extrabold tracking-tight">
            <Zap className="h-6 w-6 text-attention" /> Market Time Machine
          </h1>
          <p className="text-sm text-slate-500">
            An animated replay of what happened between two points in the research dataset.
          </p>
        </div>
        <OfflineDatasetBadge label={replay?.dataset_label} />
      </div>

      {/* pickers */}
      <Card className="!p-4">
        <div className="grid gap-4 sm:grid-cols-[1fr_auto_auto]">
          <div>
            <span className="label">Stock</span>
            <div className="mt-1">
              <StockSearch onPick={(s) => navigate(`/time-machine/${s.symbol}`)} placeholder={`Replaying ${symbol} — pick another`} />
            </div>
          </div>
          <div>
            <span className="label">Window</span>
            <select
              value={lookback}
              onChange={(e) => setLookback(Number(e.target.value))}
              className="mt-1 block rounded-xl border border-white/10 bg-ink-850 px-3 py-2.5 text-sm outline-none focus:border-attention/60"
            >
              <option value={35}>~1 trading week</option>
              <option value={65}>~2 trading weeks</option>
              <option value={110}>~3 trading weeks</option>
              <option value={160}>~1 trading month</option>
              <option value={240}>~7 trading weeks</option>
            </select>
          </div>
          <div>
            <span className="label">Ends at</span>
            <div className="mt-1 rounded-xl border border-white/10 bg-ink-850 px-3 py-2.5 font-mono text-sm text-slate-300">
              {fmtDateTime(clock?.current_dataset_timestamp)}
            </div>
          </div>
        </div>
      </Card>

      {isLoading && <LoadingBlock height={420} />}

      {replay && cur && (
        <>
          {/* transport */}
          <Card className="!p-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-1.5">
                <button className="btn-ghost !px-2.5" onClick={player.stepBack} title="Step back">
                  <StepForward className="h-4 w-4 -scale-x-100" />
                </button>
                {player.playing ? (
                  <button className="btn-primary !px-3" onClick={player.pause}>
                    <Pause className="h-4 w-4" /> Pause
                  </button>
                ) : (
                  <button className="btn-primary !px-3" onClick={player.play}>
                    <Play className="h-4 w-4" /> {player.atEnd ? "Replay" : "Play"}
                  </button>
                )}
                <button className="btn-ghost !px-2.5" onClick={player.stepForward} title="Step forward">
                  <StepForward className="h-4 w-4" />
                </button>
                <button className="btn-ghost !px-2.5" onClick={player.restart} title="Restart">
                  <RotateCcw className="h-4 w-4" />
                </button>
              </div>

              <div className="flex items-center gap-1">
                <span className="label mr-1">Speed</span>
                {player.speeds.map((s) => (
                  <button
                    key={s}
                    onClick={() => player.setSpeed(s)}
                    className={cx(
                      "rounded-md px-2 py-1 text-xs font-semibold",
                      player.speed === s ? "bg-attention text-ink-950" : "bg-white/5 text-slate-400 hover:bg-white/10",
                    )}
                  >
                    {s}×
                  </button>
                ))}
              </div>

              <div className="ml-auto font-mono text-sm text-slate-300">{fmtDateTime(cur.timestamp)}</div>
            </div>

            {/* scrubber */}
            <div className="mt-3">
              <input
                type="range"
                min={0}
                max={frames.length - 1}
                value={index}
                onChange={(e) => player.seek(Number(e.target.value))}
                className="w-full accent-attention"
                aria-label="Replay timeline"
              />
              <div className="relative mt-1 h-3">
                {replay.anomaly_markers.map((a, i) => (
                  <span
                    key={`a${i}`}
                    className={cx(
                      "absolute top-0 h-2.5 w-1 -translate-x-1/2 rounded-full",
                      a.level === "serious" ? "bg-risk" : "bg-attention",
                    )}
                    style={{ left: `${(a.frame_index / (frames.length - 1)) * 100}%` }}
                    title={a.label}
                  />
                ))}
                {replay.news_markers.map((n, i) => (
                  <span
                    key={`n${i}`}
                    className="absolute top-0 h-2.5 w-0.5 -translate-x-1/2 bg-indigo-400"
                    style={{ left: `${(n.frame_index / (frames.length - 1)) * 100}%` }}
                    title={n.headline}
                  />
                ))}
              </div>
            </div>
          </Card>

          {/* main stage */}
          <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
            <div className="space-y-4">
              <Card
                className={cx(
                  "relative transition-shadow",
                  flashAnomaly && !player.reduced && "animate-pulse-ring",
                )}
              >
                <SectionTitle
                  right={
                    <span className="flex items-center gap-2 text-xs">
                      {flashNews && (
                        <span className="flex items-center gap-1 rounded-full border border-indigo-400/40 bg-indigo-400/10 px-2 py-0.5 text-indigo-300">
                          <Newspaper className="h-3 w-3" /> headline now
                        </span>
                      )}
                      <VerdictBadge verdict={cur.verdict} />
                    </span>
                  }
                >
                  {replay.company_name} — price
                </SectionTitle>
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={priceData} margin={{ top: 6, right: 12, bottom: 0, left: 0 }}>
                    <defs>
                      <linearGradient id="tmpx" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke={GRID} vertical={false} />
                    <XAxis dataKey="timestamp" tick={AXIS} tickFormatter={(t) => fmtDateTime(t).slice(0, 6)} minTickGap={44} axisLine={false} tickLine={false} />
                    <YAxis tick={AXIS} domain={yPrice} width={54} axisLine={false} tickLine={false} tickFormatter={(v) => `₹${Math.round(v)}`} />
                    <Area type="monotone" dataKey="close" stroke="#22d3ee" strokeWidth={2.2} fill="url(#tmpx)" isAnimationActive={false} connectNulls />
                    {visibleNews.map((n, i) => (
                      <ReferenceLine key={`nl${i}`} x={n.timestamp} stroke="#818cf8" strokeDasharray="2 3" strokeOpacity={0.55} />
                    ))}
                    {visibleAnomalies.map((a, i) => {
                      const f = frames[a.frame_index];
                      return (
                        <ReferenceDot
                          key={`ad${i}`}
                          x={f?.timestamp}
                          y={f?.close ?? undefined}
                          r={a.level === "serious" ? 6 : 4}
                          fill={a.level === "serious" ? "#f43f5e" : "#f5a524"}
                          stroke="#0b1220"
                          strokeWidth={1.5}
                          isFront
                        />
                      );
                    })}
                    {cur.close != null && (
                      <ReferenceDot x={cur.timestamp} y={cur.close} r={3.5} fill="#e2e8f0" stroke="#0b1220" strokeWidth={1.5} isFront />
                    )}
                  </AreaChart>
                </ResponsiveContainer>
              </Card>

              <div className="grid gap-4 sm:grid-cols-2">
                <Card>
                  <SectionTitle>Volume</SectionTitle>
                  <ResponsiveContainer width="100%" height={130}>
                    <BarChart data={volData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                      <CartesianGrid stroke={GRID} vertical={false} />
                      <XAxis dataKey="timestamp" hide />
                      <YAxis tick={AXIS} width={46} axisLine={false} tickLine={false} tickFormatter={(v) => (v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : `${Math.round(v / 1e3)}k`)} />
                      <Bar dataKey="volume" fill="#334155" radius={[2, 2, 0, 0]} isAnimationActive={false} />
                    </BarChart>
                  </ResponsiveContainer>
                  <div className="mt-1 text-xs text-slate-500">
                    {cur.volume_ratio.toFixed(2)}× rolling average
                  </div>
                </Card>
                <Card>
                  <SectionTitle right={<span className="text-[11px] text-slate-500">rebased to 100</span>}>
                    Stock vs sector vs market
                  </SectionTitle>
                  <ResponsiveContainer width="100%" height={130}>
                    <LineChart data={compData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                      <CartesianGrid stroke={GRID} vertical={false} />
                      <XAxis dataKey="timestamp" hide />
                      <YAxis tick={AXIS} width={38} axisLine={false} tickLine={false} domain={["auto", "auto"]} />
                      <ReferenceLine y={100} stroke={GRID} />
                      <Line type="monotone" dataKey="stock" stroke="#f5a524" strokeWidth={2.2} dot={false} isAnimationActive={false} />
                      <Line type="monotone" dataKey="sector" stroke="#22d3ee" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                      <Line type="monotone" dataKey="market" stroke="#94a3b8" strokeWidth={1.3} strokeDasharray="4 3" dot={false} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                  <div className="mt-1 flex gap-3 text-[11px] text-slate-500">
                    <span className="text-attention">■ stock</span>
                    <span className="text-neutralc">■ sector</span>
                    <span className="text-slate-400">■ market</span>
                  </div>
                </Card>
              </div>
            </div>

            {/* right rail: live state */}
            <div className="space-y-4">
              <Card className="flex flex-col items-center">
                <AttentionScore score={cur.attention_score} confidence={cur.confidence} size={128} />
                <div className="mt-2 text-center">
                  <VerdictBadge verdict={cur.verdict} />
                </div>
                <div className="mt-3 grid w-full grid-cols-2 gap-2 text-center text-xs">
                  <div className="glass-soft py-2">
                    <div className="label">Return z</div>
                    <div className="font-mono font-bold" style={{ color: scoreColor(Math.abs(cur.return_zscore) * 15) }}>
                      {cur.return_zscore >= 0 ? "+" : ""}
                      {cur.return_zscore.toFixed(1)}
                    </div>
                  </div>
                  <div className="glass-soft py-2">
                    <div className="label">Freshness</div>
                    <div className="font-semibold capitalize text-slate-200">{cur.freshness}</div>
                  </div>
                </div>
              </Card>

              <Card>
                <SectionTitle hint={replay.first_mover_detail || undefined}>
                  <span className="flex items-center gap-2">
                    <Flag className="h-4 w-4 text-attention" /> Who moved first?
                  </span>
                </SectionTitle>
                <div className="flex items-center gap-2 text-lg font-bold capitalize">
                  <ChevronsRight className="h-5 w-5 text-attention" />
                  {replay.who_moved_first ?? "no clear leader"}
                </div>
              </Card>

              <Card>
                <SectionTitle>
                  <span className="flex items-center gap-2">
                    <Gauge className="h-4 w-4 text-slate-400" /> Anomalies so far
                  </span>
                </SectionTitle>
                <div className="space-y-2">
                  {visibleAnomalies.length === 0 && (
                    <p className="text-sm text-slate-500">Calm so far. Keep playing.</p>
                  )}
                  {visibleAnomalies.map((a, i) => (
                    <div key={i} className="flex items-center justify-between rounded-lg border border-white/5 bg-white/[0.03] px-3 py-2 text-xs">
                      <span className="flex items-center gap-2">
                        <span className={cx("h-2 w-2 rounded-full", a.level === "serious" ? "bg-risk" : "bg-attention")} />
                        {a.verdict}
                      </span>
                      {a.case_id ? (
                        <Link to={`/cases/${a.case_id}`} className="text-neutralc-soft hover:underline">
                          open →
                        </Link>
                      ) : (
                        <span className="text-slate-600">{fmtDateTime(a.timestamp).slice(0, 6)}</span>
                      )}
                    </div>
                  ))}
                </div>
              </Card>

              {flashNews && (
                <Card className="border-indigo-400/30 bg-indigo-400/5 animate-fade-up">
                  <div className="flex items-center gap-2 text-xs font-semibold text-indigo-300">
                    <Newspaper className="h-3.5 w-3.5" /> Local headline · {fmtDateTime(flashNews.timestamp)}
                  </div>
                  <p className="mt-1 text-sm text-slate-200">{flashNews.headline}</p>
                  <div className="mt-1 text-[11px] text-slate-500">
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
