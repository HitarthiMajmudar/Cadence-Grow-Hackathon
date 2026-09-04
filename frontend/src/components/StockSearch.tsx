import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { useStocks } from "@/hooks/queries";
import type { StockMeta } from "@/types";
import { cx } from "@/utils/format";

export function StockSearch({
  onPick,
  exclude = [],
  placeholder = "Search by symbol or company…",
  autoFocus = false,
}: {
  onPick: (s: StockMeta) => void;
  exclude?: string[];
  placeholder?: string;
  autoFocus?: boolean;
}) {
  const { data: stocks = [] } = useStocks();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);

  const results = useMemo(() => {
    const term = q.trim().toLowerCase();
    return stocks
      .filter((s) => !exclude.includes(s.symbol))
      .filter((s) =>
        !term ? true : `${s.symbol} ${s.name} ${s.sector_name}`.toLowerCase().includes(term),
      )
      .slice(0, 8);
  }, [stocks, q, exclude]);

  return (
    <div className="relative">
      <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-ink-850 px-3 py-2.5">
        <Search className="h-4 w-4 text-slate-500" />
        <input
          autoFocus={autoFocus}
          className="w-full bg-transparent text-sm outline-none placeholder:text-slate-600"
          placeholder={placeholder}
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 120)}
        />
      </div>
      {open && results.length > 0 && (
        <div className="glass absolute z-30 mt-2 max-h-72 w-full overflow-y-auto scrollbar-thin p-1.5">
          {results.map((s) => (
            <button
              key={s.symbol}
              className={cx("flex w-full items-center justify-between rounded-lg px-3 py-2 text-left hover:bg-white/10")}
              onMouseDown={() => {
                onPick(s);
                setQ("");
                setOpen(false);
              }}
            >
              <span>
                <span className="font-mono text-sm font-bold">{s.symbol}</span>
                <span className="ml-2 text-xs text-slate-500">{s.name}</span>
              </span>
              <span className="text-[11px] text-slate-600">{s.sector_name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
