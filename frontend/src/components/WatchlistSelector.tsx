import { ChevronDown, Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useWatchlists } from "@/hooks/queries";
import { cx } from "@/utils/format";

export function WatchlistSelector({
  activeId,
  onChange,
}: {
  activeId?: string;
  onChange: (id: string) => void;
}) {
  const { data: watchlists } = useWatchlists();
  const [open, setOpen] = useState(false);
  const active = watchlists?.find((w) => w.id === activeId) ?? watchlists?.[0];

  if (!watchlists) return null;

  return (
    <div className="relative">
      <button
        className="btn-ghost"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="max-w-[160px] truncate">{active?.name ?? "Watchlist"}</span>
        <span className="text-xs text-slate-500">{active?.symbols.length ?? 0}</span>
        <ChevronDown className="h-4 w-4" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-20" onClick={() => setOpen(false)} />
          <div
            role="listbox"
            className="glass absolute right-0 z-30 mt-2 w-64 p-1.5"
          >
            {watchlists.map((w) => (
              <button
                key={w.id}
                role="option"
                aria-selected={w.id === active?.id}
                className={cx(
                  "flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm hover:bg-white/10",
                  w.id === active?.id && "bg-white/10",
                )}
                onClick={() => {
                  onChange(w.id);
                  setOpen(false);
                }}
              >
                <span className="truncate">{w.name}</span>
                <span className="text-xs text-slate-500">{w.symbols.length}</span>
              </button>
            ))}
            <Link
              to="/watchlists"
              className="mt-1 flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-neutralc-soft hover:bg-white/10"
              onClick={() => setOpen(false)}
            >
              <Plus className="h-4 w-4" />
              Manage watchlists
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
