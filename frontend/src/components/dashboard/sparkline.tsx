type SparklineProps = {
  values: number[];
  color: string;
  label: string;
  width?: number;
  height?: number;
};

/** A small line showing the shape of a price series, without axes. */
export function Sparkline({ values, color, label, width = 96, height = 28 }: SparklineProps) {
  if (values.length < 2) {
    return <span className="inline-block text-xs text-muted-foreground">N/A</span>;
  }

  const lowest = Math.min(...values);
  const highest = Math.max(...values);
  const spread = highest - lowest || 1;
  const padding = 2;
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = padding + (1 - (value - lowest) / spread) * (height - padding * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label} className="overflow-visible">
      <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
