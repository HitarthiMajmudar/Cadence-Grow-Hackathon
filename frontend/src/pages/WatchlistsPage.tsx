import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Check, Pencil, Plus, Target, Trash2, Wallet, X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/endpoints";
import { useWatchlist, useWatchlistMutations, useWatchlists } from "@/hooks/queries";
import { useActiveWatchlist } from "@/hooks/useActiveWatchlist";
import { StockSearch } from "@/components/StockSearch";
import { AttentionMeter } from "@/components/AttentionScore";
import { FreshnessBadge } from "@/components/badges";
import { Card, EmptyState, LoadingBlock, SectionTitle } from "@/components/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn, money, pct, priceDirClass } from "@/utils/format";

export function WatchlistsPage() {
  const { data: watchlists } = useWatchlists();
  const { activeId, setActive } = useActiveWatchlist();
  const [selectedId, setSelectedId] = useState<string | undefined>(activeId);
  const wid = selectedId ?? activeId;
  const { data: detail, isLoading } = useWatchlist(wid);
  const m = useWatchlistMutations();
  const { data: budgetData } = useQuery({ queryKey: ["budgets"], queryFn: api.attentionBudgets });

  const [renaming, setRenaming] = useState(false);
  const [nameDraft, setNameDraft] = useState("");
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    if (detail) setNameDraft(detail.name);
  }, [detail]);

  const budgets = budgetData?.budgets ?? [];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Watchlists</h1>
          <p className="text-sm text-muted-foreground">
            Create lists, tune each list's attention threshold and daily budget.
          </p>
        </div>
        <Button size="sm" onClick={() => setCreating((v) => !v)}>
          <Plus /> New watchlist
        </Button>
      </div>

      {creating && (
        <Card className="p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Input
              className="flex-1"
              placeholder="Watchlist name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <Button
              size="sm"
              disabled={!newName.trim() || m.create.isPending}
              onClick={async () => {
                const w = await m.create.mutateAsync({ name: newName.trim(), symbols: ["RELIANCE", "TCS"] });
                setNewName("");
                setCreating(false);
                setSelectedId(w.id);
              }}
            >
              Create
            </Button>
            <Button variant="outline" size="sm" onClick={() => setCreating(false)}>
              Cancel
            </Button>
          </div>
        </Card>
      )}

      <div className="grid gap-5 lg:grid-cols-[260px_1fr]">
        <div className="space-y-2">
          {(watchlists ?? []).map((w) => (
            <button
              key={w.id}
              onClick={() => setSelectedId(w.id)}
              className={cn(
                "w-full rounded-md border px-3 py-3 text-left transition-colors",
                w.id === wid ? "border-primary/50 bg-primary/5" : "bg-card hover:bg-accent/50",
              )}
            >
              <div className="flex items-center justify-between">
                <span className="truncate font-medium">{w.name}</span>
                <span className="text-xs text-muted-foreground">{w.symbols.length}</span>
              </div>
              <div className="mt-1 flex items-center gap-2 text-[11px] text-muted-foreground">
                <Target className="size-3" /> ≥{w.attention_threshold}
                <Wallet className="size-3" /> {w.daily_attention_budget}
              </div>
            </button>
          ))}
        </div>

        <div className="space-y-5">
          {isLoading && <LoadingBlock height={200} />}
          {detail && (
            <>
              <Card>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  {renaming ? (
                    <div className="flex items-center gap-2">
                      <Input
                        className="h-8 w-48"
                        value={nameDraft}
                        onChange={(e) => setNameDraft(e.target.value)}
                      />
                      <Button
                        size="icon-sm"
                        onClick={async () => {
                          await m.rename.mutateAsync({ id: detail.id, name: nameDraft.trim() });
                          setRenaming(false);
                        }}
                      >
                        <Check />
                      </Button>
                      <Button size="icon-sm" variant="outline" onClick={() => setRenaming(false)}>
                        <X />
                      </Button>
                    </div>
                  ) : (
                    <h2 className="flex items-center gap-2 text-base font-semibold">
                      {detail.name}
                      <button
                        className="text-muted-foreground hover:text-foreground"
                        onClick={() => setRenaming(true)}
                      >
                        <Pencil className="size-3.5" />
                      </button>
                    </h2>
                  )}
                  <div className="flex items-center gap-2">
                    {wid !== activeId && (
                      <Button variant="outline" size="sm" onClick={() => setActive(detail.id)}>
                        Set as active
                      </Button>
                    )}
                    {(watchlists?.length ?? 0) > 1 &&
                      (confirmDelete ? (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={async () => {
                            await m.remove.mutateAsync(detail.id);
                            setSelectedId(undefined);
                            setConfirmDelete(false);
                          }}
                        >
                          Confirm delete
                        </Button>
                      ) : (
                        <Button variant="outline" size="sm" onClick={() => setConfirmDelete(true)}>
                          <Trash2 /> Delete
                        </Button>
                      ))}
                  </div>
                </div>

                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div>
                    <Label>Attention threshold: {detail.attention_threshold}</Label>
                    <input
                      type="range"
                      min={20}
                      max={90}
                      value={detail.attention_threshold}
                      onChange={(e) =>
                        m.settings.mutate({ id: detail.id, attention_threshold: Number(e.target.value) })
                      }
                      className="mt-2 w-full accent-primary"
                    />
                    <p className="mt-1 text-xs text-muted-foreground">
                      Cases scoring below this land in "Still investigating" instead of "Needs
                      attention".
                    </p>
                  </div>
                  <div>
                    <Label>Daily attention budget</Label>
                    <Select
                      value={detail.daily_attention_budget}
                      onValueChange={(v) =>
                        v && m.settings.mutate({ id: detail.id, daily_attention_budget: v })
                      }
                    >
                      <SelectTrigger className="mt-2 w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {budgets.map((b) => (
                          <SelectItem key={b.id} value={b.id}>
                            {b.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </Card>

              <Card>
                <SectionTitle hint="Search by company name or symbol">Add a stock</SectionTitle>
                <StockSearch
                  exclude={detail.symbols}
                  onPick={(s) => m.addSymbol.mutate({ id: detail.id, symbol: s.symbol })}
                />
                <div className="mt-4 space-y-1.5">
                  {detail.items.length === 0 && (
                    <EmptyState title="Empty watchlist" message="Add a stock above to start tracking it." />
                  )}
                  {detail.items.map((it) => (
                    <div
                      key={it.symbol}
                      className="flex items-center gap-3 rounded-md border bg-card px-3 py-2.5"
                    >
                      <Link to={`/stocks/${it.symbol}`} className="w-24 shrink-0">
                        <div className="font-mono text-sm font-semibold hover:text-primary">
                          {it.symbol}
                        </div>
                        <div className="truncate text-[11px] text-muted-foreground">{it.name}</div>
                      </Link>
                      <div className="w-20 text-right text-sm tabular-nums">{money(it.latest_price)}</div>
                      <div
                        className={cn(
                          "w-16 text-right text-sm font-medium tabular-nums",
                          priceDirClass(it.change_pct),
                        )}
                      >
                        {pct(it.change_pct)}
                      </div>
                      <div className="flex-1">
                        <AttentionMeter score={it.attention_score} />
                      </div>
                      <FreshnessBadge freshness={it.freshness} />
                      <button
                        className="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                        onClick={() => m.removeSymbol.mutate({ id: detail.id, symbol: it.symbol })}
                        title={`Remove ${it.symbol}`}
                      >
                        <X className="size-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
