interface Props {
  data: number[];
  width?: number;
  height?: number;
  strokeWidth?: number;
  className?: string;
}

export function Sparkline({ data, width = 90, height = 28, strokeWidth = 1.5, className }: Props) {
  if (!data || data.length < 2) {
    return <svg width={width} height={height} className={className} />;
  }
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const step = width / (data.length - 1);
  const pts = data.map((v, i) => `${(i * step).toFixed(2)},${(height - ((v - min) / range) * (height - 2) - 1).toFixed(2)}`);
  const up = data[data.length - 1] >= data[0];
  const color = up ? "#34d399" : "#f43f5e";

  return (
    <svg width={width} height={height} className={className} aria-hidden="true">
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
