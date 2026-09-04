import { useMemo } from "react";

export interface ChartColors {
  stock: string;
  sector: string;
  market: string;
  news: string;
  grid: string;
  axis: string;
  positive: string;
  negative: string;
  warning: string;
  surface: string;
}

function read(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

/**
 * Resolve the design-system CSS variables into concrete colour strings for
 * Recharts (which cannot consume `var(--x)` in every prop).
 */
export function useChartColors(): ChartColors {
  return useMemo(
    () => ({
      stock: read("--chart-1", "#0d9488"),
      sector: read("--chart-2", "#3b82f6"),
      market: read("--muted-foreground", "#71717a"),
      news: read("--chart-4", "#7c3aed"),
      grid: read("--border", "#e4e4e7"),
      axis: read("--muted-foreground", "#71717a"),
      positive: read("--positive", "#16a34a"),
      negative: read("--negative", "#dc2626"),
      warning: read("--warning", "#d97706"),
      surface: read("--popover", "#ffffff"),
    }),
    [],
  );
}
