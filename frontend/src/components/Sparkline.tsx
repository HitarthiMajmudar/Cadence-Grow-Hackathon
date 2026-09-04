interface Props {
  data: number[];
  width?: number;
  height?: number;
  strokeWidth?: number;
  className?: string;
  /** Force a colour; defaults to positive/negative based on first vs last value. */
  tone?: "positive" | "negative" | "muted";
}

export function Sparkline({ data, width = 90, height = 28, strokeWidth = 1.5, className, tone }: Props) {
  if (!data || data.length < 2) {
    return <svg width={width} height={height} className={className} />;
  }
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const step = width / (data.length - 1);
  const pts = data.map(
    (v, i) =>
      `${(i * step).toFixed(2)},${(height - ((v - min) / range) * (height - 2) - 1).toFixed(2)}`,
  );
  const resolved = tone ?? (data[data.length - 1] >= data[0] ? "positive" : "negative");
  const stroke =
    resolved === "positive"
      ? "var(--positive)"
      : resolved === "negative"
        ? "var(--negative)"
        : "var(--muted-foreground)";

  return (
    <svg width={width} height={height} className={className} aria-hidden="true">
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
