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
import { useChartColors } from "@/lib/chart-colors";

function ChartTooltip({ active, payload, label, unit, currencySymbol }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md">
      <div className="mb-1 font-mono text-muted-foreground">{fmtDateTime(label)}</div>
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="size-2 rounded-full" style={{ background: p.color }} />
          <span className="text-muted-foreground">{p.name}</span>
          <span className="ml-auto font-semibold">
            {unit === "money"
              ? currencySymbol
                ? `${currencySymbol}${typeof p.value === "number" ? p.value.toFixed(2) : p.value}`
                : money(p.value)
              : typeof p.value === "number"
                ? p.value.toFixed(2)
                : p.value}
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
  currencySymbol,
}: {
  data: { timestamp: string; close: number | null }[];
  anomalies?: AnomalyMark[];
  newsMarks?: { timestamp: string }[];
  height?: number;
  /** Overrides the default (Detective Mode's dataset is always INR). Live
   * Markets passes the quote's actual currency symbol here. */
  currencySymbol?: string;
}) {
  const c = useChartColors();
  const axis = { fontSize: 11, fill: c.axis };
  const closeByTs = new Map(data.map((d) => [d.timestamp, d.close]));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={c.grid} vertical={false} />
        <XAxis
          dataKey="timestamp"
          tick={axis}
          tickFormatter={(t) => fmtDateTime(t).slice(0, 6)}
          minTickGap={40}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={axis}
          domain={["auto", "auto"]}
          width={54}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${currencySymbol ?? "₹"}${Math.round(v)}`}
        />
        <Tooltip content={<ChartTooltip unit="money" currencySymbol={currencySymbol} />} />
        <Area
          type="monotone"
          dataKey="close"
          name="Price"
          stroke={c.stock}
          strokeWidth={2}
          fill={c.stock}
          fillOpacity={0.1}
          connectNulls
          isAnimationActive={false}
        />
        {newsMarks.map((n, i) => (
          <ReferenceLine key={`n${i}`} x={n.timestamp} stroke={c.news} strokeDasharray="2 3" strokeOpacity={0.6} />
        ))}
        {anomalies.map((a, i) => (
          <ReferenceDot
            key={`a${i}`}
            x={a.timestamp}
            y={a.value ?? closeByTs.get(a.timestamp) ?? undefined}
            r={a.level === "serious" ? 6 : 4}
            fill={a.level === "serious" ? c.negative : c.warning}
            stroke={c.surface}
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
  const c = useChartColors();
  const axis = { fontSize: 11, fill: c.axis };
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={c.grid} vertical={false} />
        <XAxis
          dataKey="timestamp"
          tick={axis}
          tickFormatter={(t) => fmtDateTime(t).slice(0, 6)}
          minTickGap={40}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={axis}
          width={54}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => (v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : `${Math.round(v / 1e3)}k`)}
        />
        <Tooltip content={<ChartTooltip />} />
        <Bar dataKey="volume" name="Volume" fill={c.market} fillOpacity={0.5} radius={[2, 2, 0, 0]} isAnimationActive={false} />
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
  const c = useChartColors();
  const axis = { fontSize: 11, fill: c.axis };
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={c.grid} vertical={false} />
        <XAxis
          dataKey="timestamp"
          tick={axis}
          tickFormatter={(t) => fmtDateTime(t).slice(0, 6)}
          minTickGap={40}
          axisLine={false}
          tickLine={false}
        />
        <YAxis tick={axis} width={44} axisLine={false} tickLine={false} domain={["auto", "auto"]} />
        <Tooltip content={<ChartTooltip />} />
        <ReferenceLine y={100} stroke={c.grid} />
        <Line type="monotone" dataKey="stock_indexed" name={labels.stock} stroke={c.stock} strokeWidth={2.4} dot={false} isAnimationActive={false} />
        <Line type="monotone" dataKey="sector_indexed" name={labels.sector} stroke={c.sector} strokeWidth={1.6} dot={false} isAnimationActive={false} />
        <Line type="monotone" dataKey="market_indexed" name={labels.market} stroke={c.market} strokeWidth={1.4} strokeDasharray="4 3" dot={false} isAnimationActive={false} />
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
  const c = useChartColors();
  const axis = { fontSize: 11, fill: c.axis };
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 6, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={c.grid} vertical={false} />
        <XAxis
          dataKey="timestamp"
          tick={axis}
          tickFormatter={(t) => fmtDateTime(t).slice(0, 6)}
          minTickGap={40}
          axisLine={false}
          tickLine={false}
        />
        <YAxis tick={axis} width={30} domain={[0, 100]} axisLine={false} tickLine={false} />
        <Tooltip content={<ChartTooltip />} />
        {threshold !== undefined && (
          <ReferenceLine y={threshold} stroke={c.warning} strokeDasharray="3 3" strokeOpacity={0.6} />
        )}
        <Area
          type="monotone"
          dataKey="attention_score"
          name="Attention"
          stroke={c.warning}
          strokeWidth={2}
          fill={c.warning}
          fillOpacity={0.12}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
