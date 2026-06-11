"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { StockSentimentTrendPoint } from "@/lib/api";

type SentimentTrendChartProps = {
  points: StockSentimentTrendPoint[];
};

function formatDate(value: string) {
  const parsedDate = new Date(value);

  if (Number.isNaN(parsedDate.getTime())) {
    return value;
  }

  return parsedDate.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function SentimentTrendChart({ points }: SentimentTrendChartProps) {
  const chartData = points.map((point) => ({
    ...point,
    label: formatDate(point.date),
  }));

  return (
    <div className="h-[280px] rounded-md border bg-background/30 p-3">
      {chartData.length === 0 ? (
        <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
          Sentiment trend appears after dated articles are analyzed.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ left: 8, right: 8, top: 12, bottom: 0 }}>
            <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              minTickGap={24}
            />
            <YAxis
              yAxisId="count"
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              width={34}
            />
            <YAxis
              yAxisId="score"
              orientation="right"
              domain={[-1, 1]}
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              width={44}
            />
            <Tooltip
              contentStyle={{
                background: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "6px",
                color: "hsl(var(--foreground))",
              }}
            />
            <Bar yAxisId="count" dataKey="positive" stackId="sentiment" fill="#34d399" radius={[3, 3, 0, 0]} />
            <Bar yAxisId="count" dataKey="neutral" stackId="sentiment" fill="#94a3b8" />
            <Bar yAxisId="count" dataKey="negative" stackId="sentiment" fill="#f87171" radius={[3, 3, 0, 0]} />
            <Line
              yAxisId="score"
              type="monotone"
              dataKey="average_score"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={false}
            />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
