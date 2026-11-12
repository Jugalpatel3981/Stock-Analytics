// Chart colours for the dark theme. The order is fixed: a series keeps its slot, so adding
// or removing a series never repaints the others. The set was checked for colour-blind
// separation and contrast against the card surface.
export const SERIES_COLORS = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"] as const;

export function seriesColor(index: number) {
  return SERIES_COLORS[index % SERIES_COLORS.length];
}

// Two-sided scale for values around zero, such as correlation: blue above, red below.
const POSITIVE_RGB = [57, 135, 229];
const NEGATIVE_RGB = [230, 103, 103];
const NEUTRAL_RGB = [56, 56, 53];

/** Colour for a value between -1 and 1, fading to neutral grey at zero. */
export function divergingColor(value: number) {
  const strength = Math.min(1, Math.abs(value));
  const target = value >= 0 ? POSITIVE_RGB : NEGATIVE_RGB;
  const channels = NEUTRAL_RGB.map((neutral, index) =>
    Math.round(neutral + (target[index] - neutral) * strength),
  );

  return `rgb(${channels.join(", ")})`;
}

export const CHART_AXIS_TICK = { fill: "hsl(var(--muted-foreground))", fontSize: 12 };
export const CHART_GRID_STROKE = "hsl(var(--border))";
