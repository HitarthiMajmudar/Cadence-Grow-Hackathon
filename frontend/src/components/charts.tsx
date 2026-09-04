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
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fmtDateTime, money } from "@/utils/format";

const AXIS = { fontSize: 11, fill: "#64748b" };
const GRID = "rgba(255,255,255,0.06)";

function ChartTooltip({ active, payload, label, unit }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-white/10 bg-ink-900/95 px-3 py-2 text-xs shadow-xl">
      <div className="mb-1 font-mono text-slate-400">{fmtDateTime(label)}</div>
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
          <span className="text-slate-400">{p.name}</span>
          <span className="ml-auto font-semibold text-slate-100">
            {unit === "money" ? money(p.value) : typeof p.value === "number" ? p.value.toFixed(2) : p.value}
            {unit === "pct" ? "" : ""}
          </span>
        </div>
      ))}
    </div>
  );
}

export interface AnomalyMark {
  timestamp: string;
  value?: number;
  level: string;
}

export function PriceChart({
  data,
  anomalies = [],
  newsMarks = [],
  height = 240,
}: {
  data: { timestamp: string; close: number | null }[];
  anomalies?: AnomalyMark[];
  newsMarks?: { timestamp: string }[];
  height?: number;
}) {
  const closeByTs = new Map(data.map((d) => [d.timestamp, d.close]));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="px" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="timestamp" tick={AXIS} tickFormatter={(t) => fmtDateTime(t).slice(0, 6)} minTickGap={40} axisLine={false} tickLine={false} />
        <YAxis tick={AXIS} domain={["auto", "auto"]} width={54} axisLine={false} tickLine={false} tickFormatter={(v) => `₹${Math.round(v)}`} />
        <Tooltip content={<ChartTooltip unit="money" />} />
        <Area type="monotone" dataKey="close" name="Price" stroke="#22d3ee" strokeWidth={2} fill="url(#px)" connectNulls isAnimationActive={false} />
        {newsMarks.map((n, i) => (
          <ReferenceLine key={`n${i}`} x={n.timestamp} stroke="#818cf8" strokeDasharray="2 3" strokeOpacity={0.6} />
        ))}
        {anomalies.map((a, i) => (
          <ReferenceDot
            key={`a${i}`}
            x={a.timestamp}
            y={a.value ?? closeByTs.get(a.timestamp) ?? undefined}
            r={a.level === "serious" ? 6 : 4}
            fill={a.level === "serious" ? "#f43f5e" : "#f5a524"}
            stroke="#0b1220"
            strokeWidth={1.5}
            isFront
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function VolumeChart({
  data,
  height = 120,
}: {
  data: { timestamp: string; volume: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="timestamp" tick={AXIS} tickFormatter={(t) => fmtDateTime(t).slice(0, 6)} minTickGap={40} axisLine={false} tickLine={false} />
        <YAxis tick={AXIS} width={54} axisLine={false} tickLine={false} tickFormatter={(v) => (v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : `${Math.round(v / 1e3)}k`)} />
        <Tooltip content={<ChartTooltip />} />
        <Bar dataKey="volume" name="Volume" fill="#334155" radius={[2, 2, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ComparisonChart({
  data,
  height = 240,
  labels = { stock: "Stock", sector: "Sector", market: "Market" },
}: {
  data: { timestamp: string; stock_indexed: number; sector_indexed: number; market_indexed: number }[];
  height?: number;
  labels?: { stock: string; sector: string; market: string };
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="timestamp" tick={AXIS} tickFormatter={(t) => fmtDateTime(t).slice(0, 6)} minTickGap={40} axisLine={false} tickLine={false} />
        <YAxis tick={AXIS} width={44} axisLine={false} tickLine={false} domain={["auto", "auto"]} />
        <Tooltip content={<ChartTooltip />} />
        <ReferenceLine y={100} stroke={GRID} />
        <Line type="monotone" dataKey="stock_indexed" name={labels.stock} stroke="#f5a524" strokeWidth={2.4} dot={false} isAnimationActive={false} />
        <Line type="monotone" dataKey="sector_indexed" name={labels.sector} stroke="#22d3ee" strokeWidth={1.6} dot={false} isAnimationActive={false} />
        <Line type="monotone" dataKey="market_indexed" name={labels.market} stroke="#94a3b8" strokeWidth={1.4} strokeDasharray="4 3" dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function ScoreEvolutionChart({
  data,
  threshold,
  height = 130,
}: {
  data: { timestamp: string; attention_score: number }[];
  threshold?: number;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 6, right: 12, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="sc" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f5a524" stopOpacity={0.4} />
            <stop offset="100%" stopColor="#f5a524" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="timestamp" tick={AXIS} tickFormatter={(t) => fmtDateTime(t).slice(0, 6)} minTickGap={40} axisLine={false} tickLine={false} />
        <YAxis tick={AXIS} width={30} domain={[0, 100]} axisLine={false} tickLine={false} />
        <Tooltip content={<ChartTooltip />} />
        {threshold !== undefined && (
          <ReferenceLine y={threshold} stroke="#f5a524" strokeDasharray="3 3" strokeOpacity={0.5} />
        )}
        <Area type="monotone" dataKey="attention_score" name="Attention" stroke="#f5a524" strokeWidth={2} fill="url(#sc)" isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
