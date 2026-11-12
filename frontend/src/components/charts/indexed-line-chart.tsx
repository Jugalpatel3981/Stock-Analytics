"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CHART_AXIS_TICK, CHART_GRID_STROKE } from "@/lib/chart-colors";
import { formatDate, formatSignedPercent } from "@/lib/format";

export type IndexedSeries = {
  key: string;
  label: string;
  color: string;
};

type IndexedLineChartProps = {
  // One row per day. Each series value is an index where 100 is the starting value.
  points: Array<Record<string, number | string | null>>;
  series: IndexedSeries[];
  emptyMessage?: string;
};

function latestValue(points: IndexedLineChartProps["points"], key: string) {
  for (let index = points.length - 1; index >= 0; index -= 1) {
    const value = points[index][key];
    if (typeof value === "number") {
      return value;
    }
  }

  return null;
}

/** Change since the start of the chart, for an index that began at 100. */
function changeFromIndex(value: number | null) {
  // Rounded to a hundredth of a percent so it matches figures shown elsewhere on the page.
  return value === null ? null : Math.round((value / 100 - 1) * 10000) / 10000;
}

const TICK_STEPS = [5, 10, 20, 25, 50, 100, 200, 250, 500, 1000];
const MAX_TICKS = 6;

/** Axis ticks on round percentages (such as -10%, 0%, +10%) that cover every value. */
function roundTicks(points: IndexedLineChartProps["points"], keys: string[]) {
  const values = points.flatMap((point) =>
    keys.map((key) => point[key]).filter((value): value is number => typeof value === "number"),
  );
  const lowest = Math.min(100, ...values);
  const highest = Math.max(100, ...values);
  const step =
    TICK_STEPS.find((candidate) => Math.ceil(highest / candidate) - Math.floor(lowest / candidate) < MAX_TICKS) ??
    TICK_STEPS[TICK_STEPS.length - 1];
  const first = Math.floor(lowest / step) * step;
  const last = Math.ceil(highest / step) * step;

  return Array.from({ length: Math.round((last - first) / step) + 1 }, (_, index) => first + index * step);
}

export function IndexedLineChart({ points, series, emptyMessage = "No price history available." }: IndexedLineChartProps) {
  if (points.length < 2) {
    return (
      <div className="flex h-[320px] items-center justify-center rounded-md border bg-background/30 p-3 text-center text-sm text-muted-foreground">
        {emptyMessage}
      </div>
    );
  }

  const ticks = roundTicks(
    points,
    series.map((item) => item.key),
  );

  return (
    <div className="space-y-3">
      <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm" aria-label="Chart legend">
        {series.map((item) => (
          <li key={item.key} className="flex items-center gap-2">
            <span className="h-0.5 w-4 rounded-full" style={{ backgroundColor: item.color }} aria-hidden="true" />
            <span className="font-medium">{item.label}</span>
            <span className="text-muted-foreground">{formatSignedPercent(changeFromIndex(latestValue(points, item.key)))}</span>
          </li>
        ))}
      </ul>

      <div className="h-[320px] rounded-md border bg-background/30 p-3">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ left: 4, right: 12, top: 12, bottom: 0 }}>
            <CartesianGrid stroke={CHART_GRID_STROKE} strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              tick={CHART_AXIS_TICK}
              axisLine={false}
              tickLine={false}
              minTickGap={48}
              tickFormatter={(value) => formatDate(String(value), { month: "short", year: "2-digit" })}
            />
            <YAxis
              domain={[ticks[0], ticks[ticks.length - 1]]}
              ticks={ticks}
              tick={CHART_AXIS_TICK}
              axisLine={false}
              tickLine={false}
              width={52}
              tickFormatter={(value) => formatSignedPercent(Number(value) / 100 - 1, 0)}
            />
            <ReferenceLine y={100} stroke="hsl(var(--muted-foreground))" strokeOpacity={0.5} />
            <Tooltip
              cursor={{ stroke: "hsl(var(--muted-foreground))", strokeOpacity: 0.6 }}
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) {
                  return null;
                }

                return (
                  <div className="rounded-md border bg-card p-3 text-xs shadow-lg">
                    <p className="mb-2 font-medium">{formatDate(String(label))}</p>
                    <div className="space-y-1">
                      {series.map((item) => {
                        const entry = payload.find((candidate) => candidate.dataKey === item.key);
                        const value = typeof entry?.value === "number" ? entry.value : null;

                        return (
                          <div key={item.key} className="flex items-center justify-between gap-6">
                            <span className="flex items-center gap-2 text-muted-foreground">
                              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} aria-hidden="true" />
                              {item.label}
                            </span>
                            <span className="font-medium text-foreground">{formatSignedPercent(changeFromIndex(value))}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              }}
            />
            {series.map((item) => (
              <Line
                key={item.key}
                type="monotone"
                dataKey={item.key}
                name={item.label}
                stroke={item.color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, stroke: "hsl(var(--card))", strokeWidth: 2 }}
                isAnimationActive={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
