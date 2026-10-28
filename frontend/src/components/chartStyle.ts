import type { ChartTheme } from '../hooks/useChartTheme'

/** Recessive axis styling shared across charts. */
export const axisProps = (theme: ChartTheme) => ({
  stroke: theme.axis,
  tick: { fill: theme.muted, fontSize: 12 },
  tickLine: false,
})

/** Y axis in MW with the unit as a rotated label. */
export const mwAxisLabel = (theme: ChartTheme, text = 'MW') => ({
  value: text,
  angle: -90,
  position: 'insideLeft' as const,
  offset: 10,
  style: { fill: theme.muted, fontSize: 12, textAnchor: 'middle' as const },
})

export const xAxisLabel = (theme: ChartTheme, text: string) => ({
  value: text,
  position: 'insideBottom' as const,
  offset: -4,
  style: { fill: theme.muted, fontSize: 12 },
})

export const tickMw = (v: number) => Math.round(v).toLocaleString('en-GB')
