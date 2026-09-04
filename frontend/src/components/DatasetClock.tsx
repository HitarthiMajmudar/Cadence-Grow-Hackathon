import { FastForward, RotateCcw, Clock } from "lucide-react";
import { useClock, useAdvanceClock, useResetClock } from "@/hooks/queries";
import { fmtDateTime } from "@/utils/format";
import { Spinner } from "./ui";

export function DatasetClock({ compact = false }: { compact?: boolean }) {
  const { data: clock, isLoading } = useClock();
  const advance = useAdvanceClock();
  const reset = useResetClock();

  if (isLoading || !clock) return <Spinner label="clock" />;

  const atEnd = clock.is_at_end;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="glass-soft flex items-center gap-2 px-3 py-2">
        <Clock className="h-4 w-4 text-neutralc" />
        <div className="leading-tight">
          <div className="label">Simulated market time</div>
          <div className="font-mono text-sm font-semibold text-slate-100">
            {fmtDateTime(clock.current_dataset_timestamp)}
          </div>
        </div>
      </div>
      {!compact && (
        <div className="text-xs text-slate-500">
          {clock.bars_from_present > 0
            ? `+${clock.bars_from_present} market hours ahead of "present"`
            : `dataset "present"`}
          {" · "}
          {clock.bars_to_end} hours of data remain
        </div>
      )}
      <button
        className="btn-primary"
        disabled={advance.isPending || atEnd}
        onClick={() => advance.mutate(undefined)}
        title={atEnd ? "You have reached the end of the dataset" : "Jump the market clock forward"}
      >
        <FastForward className="h-4 w-4" />
        {advance.isPending ? "Advancing…" : "Advance Market Time"}
      </button>
      <button
        className="btn-ghost"
        disabled={reset.isPending || clock.bars_from_present === 0}
        onClick={() => reset.mutate()}
        title="Reset the market clock to the dataset present"
      >
        <RotateCcw className="h-4 w-4" />
        Reset
      </button>
    </div>
  );
}
