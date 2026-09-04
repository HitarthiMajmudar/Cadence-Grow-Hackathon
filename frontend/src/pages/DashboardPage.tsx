import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertTriangle, Gauge, History, Rewind, Search, Target } from "lucide-react";
import {
  useBriefing,
  useCases,
  useClock,
  useMarkBriefingSeen,
  useRecentCases,
  useWatchlist,
} from "@/hooks/queries";
import { useActiveWatchlist } from "@/hooks/useActiveWatchlist";
import { DatasetClock } from "@/components/DatasetClock";
import { WatchlistSelector } from "@/components/WatchlistSelector";
import { SinceYouLeft } from "@/components/SinceYouLeft";
import { CaseCard } from "@/components/CaseCard";
import { AttentionMeter } from "@/components/AttentionScore";
import { VerdictBadge, FreshnessBadge } from "@/components/badges";
import { Card, EmptyState, ErrorState, LoadingBlock, SectionTitle, StatTile } from "@/components/ui";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn, fmtDateTime, pct, priceDirClass, money } from "@/utils/format";
import type { CaseSummary } from "@/types";

export function DashboardPage() {
  const { activeId, setActive } = useActiveWatchlist();
  const { data: clock } = useClock();
  const { data: watchlist, isLoading: wlLoading } = useWatchlist(activeId);
  const { data: briefing, isLoading: brLoading, error: brError, refetch } = useBriefing(activeId);
  const budget = watchlist?.daily_attention_budget;
  const { data: cases, isLoading: casesLoading } = useCases(activeId, budget);
  const { data: recent } = useRecentCases();
  const markSeen = useMarkBriefingSeen();
  const navigate = useNavigate();
  const [showAllExplained, setShowAllExplained] = useState(false);

  const topCase = cases?.needs_attention[0] ?? cases?.still_investigating[0];
  const budgetLabel = cases?.budget_label ?? "—";

  const handleMarkSeen = () => {
    if (activeId) markSeen.mutate({ watchlistId: activeId });
  };

  const explained = useMemo(() => {
    const list = cases?.explained ?? [];
    return showAllExplained ? list : list.slice(0, 4);
  }, [cases, showAllExplained]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Investigation Room</h1>
          <p className="text-sm text-muted-foreground">
            {watchlist ? `${watchlist.name} · ${watchlist.symbols.length} stocks` : "Loading watchlist…"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <WatchlistSelector activeId={activeId} onChange={setActive} />
          <Link
            to="/time-machine"
            className={cn(buttonVariants({ variant: "secondary", size: "sm" }), "gap-1.5")}
          >
            <Rewind />
            Replay what I missed
          </Link>
        </div>
      </div>

      <Card className="p-4">
        <DatasetClock />
      </Card>

      {brLoading && <LoadingBlock height={220} />}
      {brError && <ErrorState message={(brError as Error).message} onRetry={() => refetch()} />}
      {briefing && (
        <SinceYouLeft briefing={briefing} onMarkSeen={handleMarkSeen} marking={markSeen.isPending} />
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Deserve attention"
          value={briefing?.changes_worth_attention ?? "—"}
          sub={`of ${briefing?.total_changes ?? 0} changes`}
          tone="attention"
        />
        <StatTile
          label="Attention budget"
          value={budgetLabel}
          sub={`threshold ${cases?.threshold ?? watchlist?.attention_threshold ?? "—"}`}
          tone="neutral"
        />
        <StatTile
          label="Open cases (watchlist)"
          value={cases ? cases.total : "—"}
          sub={`${cases?.needs_attention.length ?? 0} need attention`}
        />
        <StatTile
          label="Dataset clock"
          value={clock ? fmtDateTime(clock.current_dataset_timestamp).slice(0, 6) : "—"}
          sub={clock ? `${clock.bars_to_end} market hours remain` : ""}
        />
      </div>

      {topCase && (
        <Card className="border-primary/40">
          <SectionTitle hint="The single case ranked most urgent for this watchlist right now">
            <span className="flex items-center gap-2">
              <Target className="size-4 text-primary" /> Top Investigation Case
            </span>
          </SectionTitle>
          <div className="flex flex-wrap items-start gap-5">
            <div className="min-w-[240px] flex-1">
              <div className="flex items-center gap-2">
                <span className="font-mono text-base font-semibold">{topCase.symbol}</span>
                <span className="text-sm text-muted-foreground">{topCase.company_name}</span>
              </div>
              <div className="mt-1.5">
                <VerdictBadge verdict={topCase.verdict} />
              </div>
              <p className="mt-2 max-w-xl text-sm text-foreground/80">{topCase.headline_explanation}</p>
              <div className="mt-3 flex items-center gap-4">
                <AttentionMeter score={topCase.attention_score} />
                <span className="text-xs text-muted-foreground">
                  {Math.round(topCase.confidence)}% confidence
                </span>
              </div>
            </div>
            <div className="flex gap-2">
              <Link
                to={`/cases/${topCase.case_id}`}
                className={cn(buttonVariants({ size: "sm" }))}
              >
                Open the case
              </Link>
              <Link
                to={`/time-machine/${topCase.symbol}`}
                className={cn(buttonVariants({ variant: "outline", size: "sm" }), "gap-1.5")}
              >
                <Rewind />
                Time Machine
              </Link>
            </div>
          </div>
        </Card>
      )}

      {casesLoading && <LoadingBlock height={200} />}
      {cases && (
        <div className="grid gap-5 lg:grid-cols-3">
          <Column
            title="Needs Attention"
            icon={<AlertTriangle className="size-4 text-warning-foreground" />}
            hint={`Score ≥ ${cases.threshold} · ${budgetLabel}`}
            list={cases.needs_attention}
            empty="Nothing crossed your attention threshold. That's the point — quiet is good."
          />
          <Column
            title="Still Investigating"
            icon={<Search className="size-4 text-primary" />}
            hint="Conflicting or developing evidence"
            list={cases.still_investigating}
            empty="No cases with unresolved evidence right now."
          />
          <div>
            <SectionTitle hint="Market-wide, sector-driven or news-explained moves">
              <span className="flex items-center gap-2">
                <Gauge className="size-4 text-muted-foreground" /> Explained / Low Priority
              </span>
            </SectionTitle>
            <div className="space-y-3">
              {explained.length === 0 && (
                <EmptyState title="Nothing to explain away" message="No low-priority moves on this watchlist." />
              )}
              {explained.map((c) => (
                <CaseCard key={c.case_id} c={c} dense />
              ))}
              {cases.explained.length > 4 && (
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={() => setShowAllExplained((v) => !v)}
                >
                  {showAllExplained ? "Show fewer" : `Show ${cases.explained.length - 4} more`}
                </Button>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionTitle
            hint="Latest state at the simulated market time"
            right={
              <Link to="/watchlists" className="text-xs text-primary hover:underline">
                Manage
              </Link>
            }
          >
            Watchlist
          </SectionTitle>
          {wlLoading && <LoadingBlock height={160} />}
          {watchlist && (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Symbol</TableHead>
                    <TableHead className="text-right">Price</TableHead>
                    <TableHead className="text-right">Change</TableHead>
                    <TableHead>Attention</TableHead>
                    <TableHead>Data</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {watchlist.items.map((it) => (
                    <TableRow
                      key={it.symbol}
                      className="cursor-pointer"
                      onClick={() => navigate(`/stocks/${it.symbol}`)}
                    >
                      <TableCell>
                        <div className="font-mono font-semibold">{it.symbol}</div>
                        <div className="text-[11px] text-muted-foreground">{it.sector_name}</div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{money(it.latest_price)}</TableCell>
                      <TableCell
                        className={cn("text-right font-medium tabular-nums", priceDirClass(it.change_pct))}
                      >
                        {pct(it.change_pct)}
                      </TableCell>
                      <TableCell>
                        <AttentionMeter score={it.attention_score} />
                      </TableCell>
                      <TableCell>
                        <FreshnessBadge freshness={it.freshness} />
                      </TableCell>
                      <TableCell className="text-right">
                        {it.open_case_id ? (
                          <Link
                            to={`/cases/${it.open_case_id}`}
                            className="text-xs text-primary hover:underline"
                            onClick={(e) => e.stopPropagation()}
                          >
                            case →
                          </Link>
                        ) : null}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </Card>

        <Card>
          <SectionTitle hint="Cases you opened recently">
            <span className="flex items-center gap-2">
              <History className="size-4 text-muted-foreground" /> Recently Viewed
            </span>
          </SectionTitle>
          <div className="space-y-2">
            {(recent?.cases ?? []).length === 0 && (
              <p className="text-sm text-muted-foreground">You haven't opened any cases yet.</p>
            )}
            {(recent?.cases ?? []).map((c: CaseSummary) => (
              <Link
                key={c.case_id}
                to={`/cases/${c.case_id}`}
                className="block rounded-md border bg-card px-3 py-2 hover:bg-accent/50"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-semibold">{c.symbol}</span>
                  <span className="text-[11px] text-muted-foreground">
                    {fmtDateTime(c.detection_timestamp).slice(0, 6)}
                  </span>
                </div>
                <div className="mt-0.5 text-xs text-muted-foreground">{c.verdict}</div>
              </Link>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

function Column({
  title,
  icon,
  hint,
  list,
  empty,
}: {
  title: string;
  icon: React.ReactNode;
  hint: string;
  list: CaseSummary[];
  empty: string;
}) {
  return (
    <div>
      <SectionTitle hint={hint}>
        <span className="flex items-center gap-2">
          {icon} {title}
          <Badge variant="secondary" className="h-4 px-1.5">
            {list.length}
          </Badge>
        </span>
      </SectionTitle>
      <div className="space-y-3">
        {list.length === 0 && <EmptyState title="All clear" message={empty} />}
        {list.map((c) => (
          <CaseCard key={c.case_id} c={c} />
        ))}
      </div>
    </div>
  );
}
