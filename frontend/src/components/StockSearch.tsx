import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { useStocks } from "@/hooks/queries";
import type { StockMeta } from "@/types";
import { cn } from "@/utils/format";

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
      <div className="flex h-8 items-center gap-2 rounded-none border bg-background px-2.5 focus-within:border-ring focus-within:ring-1 focus-within:ring-ring/50">
        <Search className="size-4 text-muted-foreground" />
        <input
          autoFocus={autoFocus}
          className="w-full bg-transparent text-xs outline-none placeholder:text-muted-foreground"
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
        <div className="absolute z-30 mt-1 max-h-72 w-full overflow-y-auto rounded-none border bg-popover p-1 text-popover-foreground shadow-md ring-1 ring-foreground/10">
          {results.map((s) => (
            <button
              key={s.symbol}
              className={cn(
                "flex w-full items-center justify-between rounded-none px-2 py-1.5 text-left text-xs hover:bg-accent hover:text-accent-foreground",
              )}
              onMouseDown={() => {
                onPick(s);
                setQ("");
                setOpen(false);
              }}
            >
              <span>
                <span className="font-mono font-semibold">{s.symbol}</span>
                <span className="ml-2 text-muted-foreground">{s.name}</span>
              </span>
              <span className="text-[11px] text-muted-foreground">{s.sector_name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
