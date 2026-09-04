import type { ReactNode } from "react";
import { AlertTriangle, Info, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card as ShadCard, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress as ShadProgress } from "@/components/ui/progress";
import {
  Tooltip as ShadTooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/**
 * Compatibility layer over the shadcn/ui (base-lyra) primitives. Pages import
 * these names; the implementations are now plain semantic-token components.
 */

export function Card({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <ShadCard className={className}>
      <CardContent>{children}</CardContent>
    </ShadCard>
  );
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
      <div className="min-w-0">
        <h2 className="text-sm font-semibold tracking-tight text-foreground">{children}</h2>
        {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
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
    <Badge variant="outline" title={title} className={cn("gap-1", className)}>
      {children}
    </Badge>
  );
}

const STAT_TONE: Record<string, string> = {
  default: "text-foreground",
  attention: "text-warning-foreground",
  neutral: "text-primary",
  risk: "text-negative",
  gain: "text-positive",
};

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
  return (
    <div className="rounded-md border bg-card p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className={cn("mt-1 text-lg font-semibold tabular-nums", STAT_TONE[tone])}>{value}</div>
      {sub && <div className="mt-0.5 text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <Loader2 className="size-4 animate-spin" />
      {label ?? "Loading…"}
    </div>
  );
}

export function LoadingBlock({ height = 160 }: { height?: number }) {
  return <Skeleton style={{ height }} className="w-full" aria-busy="true" aria-label="Loading" />;
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
    <div className="flex flex-col items-center justify-center gap-2 rounded-md border border-dashed bg-card px-6 py-10 text-center">
      <div className="text-muted-foreground">{icon ?? <Info className="size-5" />}</div>
      <div className="text-sm font-medium text-foreground">{title}</div>
      {message && <div className="max-w-sm text-xs text-muted-foreground">{message}</div>}
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-md border border-destructive/30 bg-card px-6 py-8 text-center">
      <AlertTriangle className="size-5 text-destructive" />
      <div className="text-sm font-medium text-foreground">Something went wrong</div>
      <div className="max-w-sm text-xs text-muted-foreground">{message ?? "Please try again."}</div>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-1" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

export function Tooltip({ text, children }: { text: string; children: ReactNode }) {
  return (
    <ShadTooltip>
      <TooltipTrigger
        render={<span className="inline-flex cursor-help items-center">{children}</span>}
      />
      <TooltipContent className="max-w-xs">{text}</TooltipContent>
    </ShadTooltip>
  );
}

export function InfoDot({ text }: { text: string }) {
  return (
    <Tooltip text={text}>
      <Info className="size-3.5 text-muted-foreground hover:text-foreground" tabIndex={0} />
    </Tooltip>
  );
}

export function Progress({
  value,
  max = 100,
  className,
}: {
  value: number;
  max?: number;
  className?: string;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return <ShadProgress value={pct} className={cn("w-full", className)} />;
}
