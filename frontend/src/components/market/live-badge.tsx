import { Activity } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { MarketSession } from "@/lib/api";
import type { StreamStatus } from "@/lib/market-stream";
import { cn } from "@/lib/utils";

type LiveBadgeProps = {
  status: StreamStatus;
  lastUpdated: string | null;
  marketSession?: MarketSession;
  nextMarketOpen?: string | null;
  hasExtendedHoursActivity?: boolean;
};

function formatTimestamp(value: string | null) {
  if (!value) {
    return "Waiting for update";
  }

  return `Updated ${new Date(value).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "America/Los_Angeles",
  })} PT`;
}

function formatNextOpen(value: string | null | undefined) {
  if (!value) {
    return null;
  }

  return `Next open ${new Date(value).toLocaleString("en-US", {
    weekday: "short",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/Los_Angeles",
  })} PT`;
}

function sessionLabel(session: MarketSession | undefined, status: StreamStatus) {
  if (status === "error") {
    return "ERROR";
  }

  if (status === "connecting" || status === "idle") {
    return "CONNECTING";
  }

  if (session === "PRE_MARKET") {
    return "PRE-MARKET";
  }

  if (session === "AFTER_HOURS") {
    return "AFTER HOURS";
  }

  if (session === "CLOSED") {
    return "MARKET CLOSED";
  }

  return "LIVE";
}

export function LiveBadge({
  status,
  lastUpdated,
  marketSession = "OPEN",
  nextMarketOpen = null,
}: LiveBadgeProps) {
  const displayStatus = status !== "error" && lastUpdated ? "connected" : status;
  const isOpen = displayStatus === "connected" && marketSession === "OPEN";
  const isExtended = displayStatus === "connected" && (marketSession === "PRE_MARKET" || marketSession === "AFTER_HOURS");
  const isClosed = displayStatus === "connected" && marketSession === "CLOSED";
  const nextOpenText = isClosed || isExtended ? formatNextOpen(nextMarketOpen) : null;

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
      <Badge
        variant={isOpen || isExtended ? "secondary" : "outline"}
        className={cn(
          "gap-1.5",
          isOpen && "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
          isExtended && "border-amber-500/30 bg-amber-500/10 text-amber-300",
          isClosed && "border-slate-500/30 bg-slate-500/10 text-slate-300",
          status === "error" && "border-destructive/40 bg-destructive/10 text-destructive",
        )}
      >
        <Activity className="h-3 w-3" aria-hidden="true" />
        {sessionLabel(marketSession, displayStatus)}
      </Badge>
      <span>{formatTimestamp(lastUpdated)}</span>
      {nextOpenText ? <span>{nextOpenText}</span> : null}
    </div>
  );
}
