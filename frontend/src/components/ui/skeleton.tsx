import { cn } from "@/lib/utils";

/** A grey placeholder shown where content is still loading. */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-secondary/80", className)} aria-hidden="true" />;
}

/** Placeholder for a row of stat tiles. */
export function StatTilesSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" role="status" aria-label="Loading">
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className="rounded-lg border bg-card/80 p-4">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="mt-4 h-7 w-32" />
          <Skeleton className="mt-3 h-3 w-40" />
        </div>
      ))}
    </div>
  );
}

/** Placeholder for a panel with a heading and a chart or table. */
export function PanelSkeleton({ height = "h-72" }: { height?: string }) {
  return (
    <div className="rounded-lg border bg-card/80 p-5" role="status" aria-label="Loading">
      <Skeleton className="h-4 w-48" />
      <Skeleton className="mt-2 h-3 w-72 max-w-full" />
      <Skeleton className={cn("mt-5 w-full", height)} />
    </div>
  );
}

/** Placeholder for a list of rows. */
export function RowsSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-3" role="status" aria-label="Loading">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="flex items-center justify-between gap-4">
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3 w-3/4" />
            <Skeleton className="h-3 w-1/3" />
          </div>
          <Skeleton className="h-6 w-16" />
        </div>
      ))}
    </div>
  );
}
