import { AlertCircle, Radar } from "lucide-react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { LiveSymbolSearch } from "@/components/LiveSymbolSearch";
import { LiveDataBadge } from "@/components/badges";
import { PriceChart, VolumeChart } from "@/components/charts";
import { Card as UICard, ErrorState, LoadingBlock, SectionTitle } from "@/components/ui";
import { useLiveHistory, useLiveQuote } from "@/hooks/queries";
import { currencySymbol, pct, signed } from "@/utils/format";
import type { LiveSymbolMatch } from "@/types";

export function LiveQuotePage() {
  const { symbol } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const exchange = params.get("exchange") ?? undefined;

  const quote = useLiveQuote(symbol, exchange);
  const history = useLiveHistory(symbol, exchange);

  function pick(s: LiveSymbolMatch) {
    const qs = s.exchange ? `?exchange=${encodeURIComponent(s.exchange)}` : "";
    navigate(`/live/${encodeURIComponent(s.symbol)}${qs}`);
  }

  const sym = currencySymbol(quote.data?.currency);
  const candles = (history.data?.candles ?? []).map((c) => ({ timestamp: c.date, close: c.close }));
  const volumes = (history.data?.candles ?? []).map((c) => ({
    timestamp: c.date,
    volume: c.volume ?? 0,
  }));

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold tracking-tight">
            <Radar className="size-5 text-primary" /> Live Markets
          </h1>
          <p className="text-sm text-muted-foreground">
            Real quotes for any stock, India or worldwide — no Attention Score here, just the
            numbers.
          </p>
        </div>
        <LiveDataBadge />
      </div>

      <UICard>
        <SectionTitle hint="Search any listed company — not limited to the Detective Mode dataset.">
          Search
        </SectionTitle>
        <LiveSymbolSearch onPick={pick} autoFocus={!symbol} />
      </UICard>

      {!symbol && (
        <div className="rounded-md border border-dashed px-6 py-10 text-center text-sm text-muted-foreground">
          Search for a symbol above to see a live quote and chart.
        </div>
      )}

      {symbol && quote.isLoading && <LoadingBlock height={140} />}

      {symbol && quote.isError && (
        <ErrorState message={(quote.error as Error)?.message ?? "Couldn't load a live quote for this symbol."} />
      )}

      {symbol && quote.data && (
        <>
          <UICard>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <div>
                <div className="flex items-baseline gap-2">
                  <span className="font-mono text-lg font-semibold">{quote.data.symbol}</span>
                  <span className="text-xs text-muted-foreground">
                    {quote.data.name} · {quote.data.exchange}
                  </span>
                </div>
                <div className="mt-1 flex items-baseline gap-3">
                  <span className="text-2xl font-semibold tabular-nums">
                    {sym}
                    {quote.data.price.toFixed(2)}
                  </span>
                  {quote.data.change !== null && quote.data.change_pct !== null && (
                    <span
                      className={
                        quote.data.change >= 0
                          ? "text-positive font-medium"
                          : "text-negative font-medium"
                      }
                    >
                      {signed(quote.data.change)} ({pct(quote.data.change_pct)})
                    </span>
                  )}
                </div>
              </div>
              {quote.data.as_of && (
                <span className="font-mono text-xs text-muted-foreground">
                  as of {quote.data.as_of}
                </span>
              )}
            </div>
          </UICard>

          <UICard>
            <SectionTitle>Daily chart</SectionTitle>
            {history.isLoading ? (
              <LoadingBlock height={260} />
            ) : history.isError ? (
              <ErrorState message="Couldn't load history for this symbol." />
            ) : (
              <PriceChart data={candles} currencySymbol={sym} height={260} />
            )}
          </UICard>

          <UICard>
            <SectionTitle>Volume</SectionTitle>
            {history.isLoading ? (
              <LoadingBlock height={120} />
            ) : (
              <VolumeChart data={volumes} height={120} />
            )}
          </UICard>

          {quote.error == null && (
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <AlertCircle className="size-3.5" /> Live Markets is separate from Detective Mode —
              this symbol has no Attention Score, verdict, or Evidence Court.
            </p>
          )}
        </>
      )}
    </div>
  );
}
