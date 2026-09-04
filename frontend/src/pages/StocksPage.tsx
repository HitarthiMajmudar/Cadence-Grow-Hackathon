import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useStocks } from "@/hooks/queries";
import { Card, LoadingBlock, SectionTitle } from "@/components/ui";
import { cx } from "@/utils/format";

export function StocksPage() {
  const { data: stocks, isLoading } = useStocks();
  const [q, setQ] = useState("");
  const [sector, setSector] = useState<string>("all");

  const sectors = useMemo(
    () => Array.from(new Set((stocks ?? []).map((s) => s.sector_name))).sort(),
    [stocks],
  );

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    return (stocks ?? []).filter((s) => {
      if (sector !== "all" && s.sector_name !== sector) return false;
      if (!term) return true;
      return `${s.symbol} ${s.name}`.toLowerCase().includes(term);
    });
  }, [stocks, q, sector]);

  if (isLoading) return <LoadingBlock height={300} />;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight">Stock universe</h1>
        <p className="text-sm text-slate-500">
          {stocks?.length ?? 0} stocks across {sectors.length} sectors in the Offline Research Dataset.
        </p>
      </div>

      <Card className="!p-4">
        <div className="flex flex-wrap gap-3">
          <input
            className="flex-1 rounded-xl border border-white/10 bg-ink-850 px-3 py-2.5 text-sm outline-none focus:border-attention/60"
            placeholder="Search symbol or company…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <select
            value={sector}
            onChange={(e) => setSector(e.target.value)}
            className="rounded-xl border border-white/10 bg-ink-850 px-3 py-2.5 text-sm outline-none focus:border-attention/60"
          >
            <option value="all">All sectors</option>
            {sectors.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((s) => (
          <Link
            key={s.symbol}
            to={`/stocks/${s.symbol}`}
            className="group glass card-hover p-4 transition-colors hover:border-white/20"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-lg font-bold">{s.symbol}</span>
              <span className={cx("chip border-white/10 bg-white/5 text-slate-400")}>{s.sector_name}</span>
            </div>
            <div className="mt-1 text-sm text-slate-300">{s.name}</div>
            <p className="mt-2 text-xs leading-relaxed text-slate-500 line-clamp-2">{s.summary}</p>
            <div className="mt-2 text-[11px] text-slate-600">
              index weight {(s.weight * 100).toFixed(1)}%
            </div>
          </Link>
        ))}
      </div>
      {filtered.length === 0 && (
        <SectionTitle>No stocks match your filter.</SectionTitle>
      )}
    </div>
  );
}
