const MISSING = "N/A";

export function formatCurrency(value: number | null | undefined, maximumFractionDigits = 2) {
  if (value === null || value === undefined) {
    return MISSING;
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits,
  }).format(value);
}

/** Formats a fraction as a percentage: 0.1234 becomes "12.3%". */
export function formatPercent(value: number | null | undefined, fractionDigits = 1) {
  if (value === null || value === undefined) {
    return MISSING;
  }

  return `${(value * 100).toFixed(fractionDigits)}%`;
}

/** Like formatPercent, with a plus sign on gains: 0.1234 becomes "+12.3%". */
export function formatSignedPercent(value: number | null | undefined, fractionDigits = 1) {
  if (value === null || value === undefined) {
    return MISSING;
  }

  return `${value > 0 ? "+" : ""}${formatPercent(value, fractionDigits)}`;
}

export function formatNumber(value: number | null | undefined, fractionDigits = 2) {
  if (value === null || value === undefined) {
    return MISSING;
  }

  return value.toFixed(fractionDigits);
}

export function formatCompact(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return MISSING;
  }

  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 2 }).format(value);
}

/** Formats an ISO date such as "2026-11-12" without shifting it across time zones. */
export function formatDate(value: string | null | undefined, options?: Intl.DateTimeFormatOptions) {
  if (!value) {
    return MISSING;
  }

  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString(
    "en-US",
    options ?? { month: "short", day: "numeric", year: "numeric" },
  );
}

/** Tailwind text colour for a gain, a loss or no change. */
export function changeColor(value: number | null | undefined) {
  if (value === null || value === undefined || value === 0) {
    return "text-muted-foreground";
  }

  return value > 0 ? "text-emerald-400" : "text-red-400";
}
