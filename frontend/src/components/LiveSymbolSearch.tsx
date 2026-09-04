import { useEffect, useRef, useState } from "react";
import { Popover as PopoverPrimitive } from "@base-ui/react/popover";
import { Loader2, Search } from "lucide-react";
import { useLiveSearch } from "@/hooks/queries";
import type { LiveSymbolMatch } from "@/types";
import { cn } from "@/utils/format";

/** Sibling of StockSearch, but backed by the live Twelve Data symbol search
 * instead of the curated Detective Mode dataset — kept separate so this page
 * can never accidentally search the offline 15-stock universe, and vice
 * versa. Uses the same portal-based dropdown so results are never clipped by
 * an ancestor's `overflow-hidden`. */
export function LiveSymbolSearch({
  onPick,
  placeholder = "Search any stock — India or worldwide…",
  autoFocus = false,
}: {
  onPick: (s: LiveSymbolMatch) => void;
  placeholder?: string;
  autoFocus?: boolean;
}) {
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const anchorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  const { data: results = [], isFetching, isError, error } = useLiveSearch(debounced);
  const showPanel = open && debounced.length > 0;

  return (
    <PopoverPrimitive.Root open={showPanel} onOpenChange={setOpen}>
      <div
        ref={anchorRef}
        className="flex h-8 items-center gap-2 rounded-none border bg-background px-2.5 focus-within:border-ring focus-within:ring-1 focus-within:ring-ring/50"
      >
        {isFetching ? (
          <Loader2 className="size-4 animate-spin text-muted-foreground" />
        ) : (
          <Search className="size-4 text-muted-foreground" />
        )}
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
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Positioner
          anchor={anchorRef}
          side="bottom"
          align="start"
          sideOffset={4}
          className="isolate z-50"
        >
          <PopoverPrimitive.Popup className="max-h-72 w-(--anchor-width) overflow-y-auto rounded-none border bg-popover p-1 text-popover-foreground shadow-md ring-1 ring-foreground/10 outline-none">
            {isError && (
              <div className="px-2 py-3 text-center text-xs text-destructive">
                {(error as Error)?.message ?? "Couldn't search live symbols."}
              </div>
            )}
            {!isError && results.length === 0 && !isFetching && (
              <div className="px-2 py-3 text-center text-xs text-muted-foreground">
                No matches for "{debounced}"
              </div>
            )}
            {results.slice(0, 8).map((s) => (
              <button
                key={`${s.symbol}-${s.exchange}`}
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
                <span className="text-[11px] text-muted-foreground">{s.exchange}</span>
              </button>
            ))}
          </PopoverPrimitive.Popup>
        </PopoverPrimitive.Positioner>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
