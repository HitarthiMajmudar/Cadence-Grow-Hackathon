import { FastForward, RotateCcw, Clock } from "lucide-react";
import { useClock, useAdvanceClock, useResetClock } from "@/hooks/queries";
import { fmtDateTime } from "@/utils/format";
import { Button } from "@/components/ui/button";
import { Spinner } from "./ui";

export function DatasetClock({ compact = false }: { compact?: boolean }) {
  const { data: clock, isLoading } = useClock();
  const advance = useAdvanceClock();
  const reset = useResetClock();

  if (isLoading || !clock) return <Spinner label="clock" />;

  const atEnd = clock.is_at_end;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="flex items-center gap-2 rounded-md border bg-muted/40 px-3 py-2">
        <Clock className="size-4 text-primary" />
        <div className="leading-tight">
          <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            Simulated market time
          </div>
          <div className="font-mono text-sm font-semibold">
            {fmtDateTime(clock.current_dataset_timestamp)}
          </div>
        </div>
      </div>
      {!compact && (
        <div className="text-xs text-muted-foreground">
          {clock.bars_from_present > 0
            ? `+${clock.bars_from_present} market hours ahead of "present"`
            : `dataset "present"`}
          {" · "}
          {clock.bars_to_end} hours of data remain
        </div>
      )}
      <Button
        size="sm"
        disabled={advance.isPending || atEnd}
        onClick={() => advance.mutate(undefined)}
        title={atEnd ? "You have reached the end of the dataset" : "Jump the market clock forward"}
      >
        <FastForward />
        {advance.isPending ? "Advancing…" : "Advance market time"}
      </Button>
      <Button
        variant="outline"
        size="sm"
        disabled={reset.isPending || clock.bars_from_present === 0}
        onClick={() => reset.mutate()}
        title="Reset the market clock to the dataset present"
      >
        <RotateCcw />
        Reset
      </Button>
    </div>
  );
}
