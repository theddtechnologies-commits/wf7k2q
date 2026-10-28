import { useEffect, useState } from 'react'

// Recharts writes colours into SVG attributes, where CSS var() doesn't resolve, so
// the resolved values of the CSS tokens in index.css are read here instead.
const TOKENS = {
  actual: '--series-1',
  forecast: '--series-2',
  over: '--diverging-warm',
  under: '--diverging-cool',
  plan: '--text-muted',
  grid: '--grid',
  axis: '--axis',
  text: '--text-secondary',
  muted: '--text-muted',
  surface: '--surface',
  band: '--band',
} as const

export type ChartTheme = Record<keyof typeof TOKENS, string>

function read(): ChartTheme {
  const style = getComputedStyle(document.documentElement)
  return Object.fromEntries(
    Object.entries(TOKENS).map(([key, cssVar]) => [key, style.getPropertyValue(cssVar).trim()]),
  ) as ChartTheme
}

export function useChartTheme(): ChartTheme {
  const [theme, setTheme] = useState<ChartTheme>(read)
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const update = () => setTheme(read())
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])
  return theme
}
