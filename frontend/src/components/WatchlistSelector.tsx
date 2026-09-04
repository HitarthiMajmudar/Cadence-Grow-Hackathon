import { ChevronDown, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import { useWatchlists } from "@/hooks/queries";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function WatchlistSelector({
  activeId,
  onChange,
}: {
  activeId?: string;
  onChange: (id: string) => void;
}) {
  const { data: watchlists } = useWatchlists();
  const active = watchlists?.find((w) => w.id === activeId) ?? watchlists?.[0];

  if (!watchlists) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(buttonVariants({ variant: "outline", size: "sm" }), "gap-1.5")}
      >
        <span className="max-w-[160px] truncate">{active?.name ?? "Watchlist"}</span>
        <span className="text-muted-foreground">{active?.symbols.length ?? 0}</span>
        <ChevronDown />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        {watchlists.map((w) => (
          <DropdownMenuItem
            key={w.id}
            onClick={() => onChange(w.id)}
            className="justify-between"
          >
            <span className="truncate">{w.name}</span>
            <span className="text-muted-foreground">{w.symbols.length}</span>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem render={<Link to="/watchlists" />}>
          <Plus />
          Manage watchlists
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
