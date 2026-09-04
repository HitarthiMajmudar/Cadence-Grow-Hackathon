import type { ReactNode } from "react";
import { AlertTriangle, Info, Loader2 } from "lucide-react";
import { cx } from "@/utils/format";

export function Card({
  children,
  className,
  as: As = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: any;
}) {
  return <As className={cx("glass p-5", className)}>{children}</As>;
}

export function SectionTitle({
  children,
  hint,
  right,
}: {
  children: ReactNode;
  hint?: string;
  right?: ReactNode;
}) {
  return (
    <div className="mb-3 flex items-end justify-between gap-3">
      <div>
        <h2 className="text-sm font-bold uppercase tracking-wide text-slate-200">{children}</h2>
        {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
      </div>
      {right}
    </div>
  );
}

export function Chip({
  children,
  className,
  title,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
}) {
  return (
    <span title={title} className={cx("chip", className)}>
      {children}
    </span>
  );
}

export function StatTile({
  label,
  value,
  sub,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone?: "default" | "attention" | "neutral" | "risk" | "gain";
}) {
  const toneCls = {
    default: "text-slate-100",
    attention: "text-attention",
    neutral: "text-neutralc-soft",
    risk: "text-risk",
    gain: "text-gain",
  }[tone];
  return (
    <div className="glass-soft px-4 py-3">
      <div className="label">{label}</div>
      <div className={cx("mt-1 text-lg font-bold tabular-nums", toneCls)}>{value}</div>
      {sub && <div className="mt-0.5 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-400">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label ?? "Loading…"}
    </div>
  );
}

export function LoadingBlock({ height = 160 }: { height?: number }) {
  return (
    <div
      className="glass animate-pulse"
      style={{ height }}
      aria-busy="true"
      aria-label="Loading"
    />
  );
}

export function EmptyState({
  title,
  message,
  icon,
  action,
}: {
  title: string;
  message?: string;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="glass flex flex-col items-center justify-center gap-2 px-6 py-10 text-center">
      <div className="text-slate-500">{icon ?? <Info className="h-6 w-6" />}</div>
      <div className="font-semibold text-slate-200">{title}</div>
      {message && <div className="max-w-sm text-sm text-slate-500">{message}</div>}
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div className="glass flex flex-col items-center gap-2 border-risk/30 px-6 py-8 text-center">
      <AlertTriangle className="h-6 w-6 text-risk" />
      <div className="font-semibold text-slate-200">Something went wrong</div>
      <div className="max-w-sm text-sm text-slate-500">{message ?? "Please try again."}</div>
      {onRetry && (
        <button className="btn-ghost mt-1" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function Tooltip({ text, children }: { text: string; children: ReactNode }) {
  return (
    <span className="group relative inline-flex cursor-help items-center">
      {children}
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-2 w-56 -translate-x-1/2 rounded-lg border border-white/10 bg-ink-900 px-3 py-2 text-xs leading-relaxed text-slate-300 opacity-0 shadow-xl transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
      >
        {text}
      </span>
    </span>
  );
}

export function InfoDot({ text }: { text: string }) {
  return (
    <Tooltip text={text}>
      <Info className="h-3.5 w-3.5 text-slate-500 hover:text-slate-300" tabIndex={0} />
    </Tooltip>
  );
}

export function Progress({ value, max = 100, className }: { value: number; max?: number; className?: string }) {
  const p = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className={cx("h-1.5 w-full overflow-hidden rounded-full bg-white/10", className)}>
      <div className="h-full rounded-full bg-attention transition-all" style={{ width: `${p}%` }} />
    </div>
  );
}
