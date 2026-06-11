import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type MetricCardProps = {
  title: string;
  value: string;
  change: string;
  trend: "up" | "down" | "neutral";
  icon: LucideIcon;
};

export function MetricCard({ title, value, change, trend, icon: Icon }: MetricCardProps) {
  return (
    <Card className="bg-card/80">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase text-muted-foreground">{title}</p>
            <p className="mt-3 text-2xl font-semibold tracking-normal">{value}</p>
          </div>
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-secondary text-primary">
            <Icon className="h-4 w-4" aria-hidden="true" />
          </div>
        </div>
        <p
          className={cn(
            "mt-4 text-sm font-medium",
            trend === "up" && "text-emerald-400",
            trend === "down" && "text-red-400",
            trend === "neutral" && "text-muted-foreground",
          )}
        >
          {change}
        </p>
      </CardContent>
    </Card>
  );
}
