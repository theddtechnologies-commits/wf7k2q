// Display helpers. All times are shown in UK local time, matching the market.

const UK = 'Europe/London'

/** Whole number with thousands separators, e.g. 12000 → "12,000". */
export const num = (v: number) => Math.round(v).toLocaleString('en-GB')

/** Signed whole number using a true minus sign, e.g. "+1,730" / "−250". */
export const signedNum = (v: number) => {
  const r = Math.round(v)
  return `${r > 0 ? '+' : r < 0 ? '−' : ''}${Math.abs(r).toLocaleString('en-GB')}`
}

export const mw = (v: number) => `${num(v)} MW`

export const signedMw = (v: number) => `${signedNum(v)} MW`

export const pct = (v: number, digits = 1) => `${v.toFixed(digits)}%`

export const hourLabel = (h: number) => `${String(h).padStart(2, '0')}:00`

export const dayLabel = (isoOrMs: string | number) =>
  new Date(isoOrMs).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: UK })

export const dateTimeLabel = (isoOrMs: string | number) =>
  new Date(isoOrMs).toLocaleString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: UK,
  })
