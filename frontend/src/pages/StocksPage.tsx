import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useStocks } from "@/hooks/queries";
import { LoadingBlock } from "@/components/ui";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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
        <h1 className="text-xl font-semibold tracking-tight">Stock universe</h1>
        <p className="text-sm text-muted-foreground">
          {stocks?.length ?? 0} stocks across {sectors.length} sectors in the Offline Research Dataset.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <Input
          className="max-w-xs flex-1"
          placeholder="Search symbol or company…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <Select value={sector} onValueChange={(v) => setSector(v ?? "all")}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All sectors" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All sectors</SelectItem>
            {sectors.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((s) => (
          <Link key={s.symbol} to={`/stocks/${s.symbol}`} className="group">
            <Card className="h-full gap-2 p-4 transition-colors group-hover:bg-accent/50">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-base font-semibold">{s.symbol}</span>
                <Badge variant="outline">{s.sector_name}</Badge>
              </div>
              <div className="text-sm text-foreground">{s.name}</div>
              <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">{s.summary}</p>
              <div className="text-[11px] text-muted-foreground">
                index weight {(s.weight * 100).toFixed(1)}%
              </div>
            </Card>
          </Link>
        ))}
      </div>
      {filtered.length === 0 && (
        <p className="text-sm text-muted-foreground">No stocks match your filter.</p>
      )}
    </div>
  );
}
