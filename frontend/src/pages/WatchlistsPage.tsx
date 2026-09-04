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
import { cx, money, pct, priceDirClass } from "@/utils/format";

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
          <h1 className="text-2xl font-extrabold tracking-tight">Watchlists</h1>
          <p className="text-sm text-slate-500">Create lists, tune each list's attention threshold and daily budget.</p>
        </div>
        <button className="btn-primary" onClick={() => setCreating((v) => !v)}>
          <Plus className="h-4 w-4" /> New watchlist
        </button>
      </div>

      {creating && (
        <Card className="!p-4">
          <div className="flex flex-wrap items-center gap-2">
            <input
              className="flex-1 rounded-xl border border-white/10 bg-ink-850 px-3 py-2.5 text-sm outline-none focus:border-attention/60"
              placeholder="Watchlist name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <button
              className="btn-primary"
              disabled={!newName.trim() || m.create.isPending}
              onClick={async () => {
                const w = await m.create.mutateAsync({ name: newName.trim(), symbols: ["RELIANCE", "TCS"] });
                setNewName("");
                setCreating(false);
                setSelectedId(w.id);
              }}
            >
              Create
            </button>
            <button className="btn-ghost" onClick={() => setCreating(false)}>
              Cancel
            </button>
          </div>
        </Card>
      )}

      <div className="grid gap-5 lg:grid-cols-[260px_1fr]">
        {/* list rail */}
        <div className="space-y-2">
          {(watchlists ?? []).map((w) => (
            <button
              key={w.id}
              onClick={() => setSelectedId(w.id)}
              className={cx(
                "w-full rounded-xl border px-3 py-3 text-left transition-colors",
                w.id === wid ? "border-attention/40 bg-attention/10" : "border-white/10 bg-white/5 hover:bg-white/10",
              )}
            >
              <div className="flex items-center justify-between">
                <span className="truncate font-semibold">{w.name}</span>
                <span className="text-xs text-slate-500">{w.symbols.length}</span>
              </div>
              <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-500">
                <Target className="h-3 w-3" /> ≥{w.attention_threshold}
                <Wallet className="h-3 w-3" /> {w.daily_attention_budget}
              </div>
            </button>
          ))}
        </div>

        {/* editor */}
        <div className="space-y-5">
          {isLoading && <LoadingBlock height={200} />}
          {detail && (
            <>
              <Card>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  {renaming ? (
                    <div className="flex items-center gap-2">
                      <input
                        className="rounded-lg border border-white/10 bg-ink-850 px-2 py-1.5 text-sm outline-none"
                        value={nameDraft}
                        onChange={(e) => setNameDraft(e.target.value)}
                      />
                      <button
                        className="rounded-lg bg-attention p-1.5 text-ink-950"
                        onClick={async () => {
                          await m.rename.mutateAsync({ id: detail.id, name: nameDraft.trim() });
                          setRenaming(false);
                        }}
                      >
                        <Check className="h-4 w-4" />
                      </button>
                      <button className="rounded-lg bg-white/10 p-1.5" onClick={() => setRenaming(false)}>
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ) : (
                    <h2 className="flex items-center gap-2 text-lg font-bold">
                      {detail.name}
                      <button className="text-slate-500 hover:text-slate-200" onClick={() => setRenaming(true)}>
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                    </h2>
                  )}
                  <div className="flex items-center gap-2">
                    {wid !== activeId && (
                      <button className="btn-ghost !py-1.5 text-xs" onClick={() => setActive(detail.id)}>
                        Set as active
                      </button>
                    )}
                    {(watchlists?.length ?? 0) > 1 &&
                      (confirmDelete ? (
                        <button
                          className="btn !bg-risk/20 !text-risk !py-1.5 text-xs"
                          onClick={async () => {
                            await m.remove.mutateAsync(detail.id);
                            setSelectedId(undefined);
                            setConfirmDelete(false);
                          }}
                        >
                          Confirm delete
                        </button>
                      ) : (
                        <button className="btn-ghost !py-1.5 text-xs" onClick={() => setConfirmDelete(true)}>
                          <Trash2 className="h-3.5 w-3.5" /> Delete
                        </button>
                      ))}
                  </div>
                </div>

                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="label">Attention threshold: {detail.attention_threshold}</label>
                    <input
                      type="range"
                      min={20}
                      max={90}
                      value={detail.attention_threshold}
                      onChange={(e) =>
                        m.settings.mutate({ id: detail.id, attention_threshold: Number(e.target.value) })
                      }
                      className="mt-2 w-full accent-attention"
                    />
                    <p className="mt-1 text-xs text-slate-500">
                      Cases scoring below this land in "Still investigating" instead of "Needs attention".
                    </p>
                  </div>
                  <div>
                    <label className="label">Daily attention budget</label>
                    <select
                      value={detail.daily_attention_budget}
                      onChange={(e) =>
                        m.settings.mutate({ id: detail.id, daily_attention_budget: e.target.value })
                      }
                      className="mt-2 block w-full rounded-xl border border-white/10 bg-ink-850 px-3 py-2.5 text-sm outline-none focus:border-attention/60"
                    >
                      {budgets.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.label}
                        </option>
                      ))}
                    </select>
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
                      className="flex items-center gap-3 rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2.5"
                    >
                      <Link to={`/stocks/${it.symbol}`} className="w-24 shrink-0">
                        <div className="font-mono text-sm font-bold hover:text-attention">{it.symbol}</div>
                        <div className="truncate text-[11px] text-slate-500">{it.name}</div>
                      </Link>
                      <div className="w-20 text-right text-sm tabular-nums">{money(it.latest_price)}</div>
                      <div className={cx("w-16 text-right text-sm font-medium tabular-nums", priceDirClass(it.change_pct))}>
                        {pct(it.change_pct)}
                      </div>
                      <div className="flex-1">
                        <AttentionMeter score={it.attention_score} />
                      </div>
                      <FreshnessBadge freshness={it.freshness} />
                      <button
                        className="rounded-lg p-1.5 text-slate-500 hover:bg-risk/20 hover:text-risk"
                        onClick={() => m.removeSymbol.mutate({ id: detail.id, symbol: it.symbol })}
                        title={`Remove ${it.symbol}`}
                      >
                        <X className="h-4 w-4" />
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
