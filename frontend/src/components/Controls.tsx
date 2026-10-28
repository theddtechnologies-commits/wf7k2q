import { useEffect, useRef, useState } from 'react'
import { useMediaQuery } from '../hooks/useMediaQuery'
import { dayLabel } from '../format'
import type { Filters, Meta } from '../types'

interface Props {
  filters: Filters
  meta: Meta
  onChange: (next: Filters) => void
}

const CUTOFF_PRESETS = [
  { label: 'N2EX 09:50', time: '09:50' },
  { label: 'EPEX 09:20', time: '09:20' },
]

const CONFIDENCE_LEVELS = [0.8, 0.9, 0.95]

const addDays = (iso: string, days: number) => {
  const d = new Date(`${iso}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

/** One-line description of the current filters, used when the panel is collapsed. */
function summary(f: Filters): string {
  const range = f.start === f.end ? dayLabel(f.start) : `${dayLabel(f.start)} – ${dayLabel(f.end)}`
  return `${range} · cutoff D-${f.cutoffDaysBefore} ${f.cutoffTime} UK · ${Math.round(f.confidence * 100)}% buffer`
}

/**
 * The single filter panel that scopes every chart on the page.
 * - Phones: not sticky; collapsed behind a "Filters" button showing a summary.
 * - Desktop: the full panel scrolls away normally; once it is off screen a slim
 *   summary bar stays pinned to the top with a button to jump back to the controls.
 */
export function Controls(props: Props) {
  const isPhone = useMediaQuery('(max-width: 900px)')
  const [open, setOpen] = useState(false)
  const [scrolledPast, setScrolledPast] = useState(false)
  const panelRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const panel = panelRef.current
    if (!panel || isPhone) return
    const observer = new IntersectionObserver(([entry]) =>
      setScrolledPast(!entry.isIntersecting && entry.boundingClientRect.top < 0),
    )
    observer.observe(panel)
    return () => observer.disconnect()
  }, [isPhone])

  if (isPhone) {
    return (
      <section className="card filters filters-mobile" aria-label="Filters">
        <button className="filters-toggle" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
          <span className="filters-summary">{summary(props.filters)}</span>
          <span className="chip filters-button">{open ? 'Done' : 'Filters'}</span>
        </button>
        {open && (
          <div className="filters-body">
            <FilterFields {...props} />
          </div>
        )}
      </section>
    )
  }

  return (
    <>
      <section ref={panelRef} className="card filters" aria-label="Filters">
        <FilterFields {...props} />
      </section>
      {scrolledPast && (
        <div className="filters-slim" role="region" aria-label="Current filters">
          <span className="filters-summary">{summary(props.filters)}</span>
          <button className="chip" onClick={() => panelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })}>
            Edit filters
          </button>
        </div>
      )}
    </>
  )
}

function FilterFields({ filters, meta, onChange }: Props) {
  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch })
  const min = meta.delivery_start
  const max = meta.delivery_end

  const ranges = [
    { label: 'All', start: min, end: max },
    { label: 'Week 1', start: min, end: addDays(min, 6) },
    { label: 'Last 7 days', start: addDays(max, -6), end: max },
  ]

  return (
    <>
      <div className="field">
        <span>Delivery days</span>
        <div className="field-row">
          <input
            type="date"
            aria-label="First delivery day"
            value={filters.start}
            min={min}
            max={max}
            required
            onChange={(e) => e.target.value && set({ start: e.target.value, end: e.target.value > filters.end ? e.target.value : filters.end })}
          />
          <span aria-hidden>–</span>
          <input
            type="date"
            aria-label="Last delivery day"
            value={filters.end}
            min={min}
            max={max}
            required
            onChange={(e) => e.target.value && set({ end: e.target.value, start: e.target.value < filters.start ? e.target.value : filters.start })}
          />
        </div>
      </div>

      <div className="field">
        <span>Quick range</span>
        <div className="chips">
          {ranges.map((r) => (
            <button
              key={r.label}
              className="chip"
              aria-pressed={filters.start === r.start && filters.end === r.end}
              onClick={() => set({ start: r.start, end: r.end })}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <div className="field">
        <span>Decision cutoff (UK time)</span>
        <div className="field-row">
          <select
            aria-label="Days before delivery"
            value={filters.cutoffDaysBefore}
            onChange={(e) => set({ cutoffDaysBefore: Number(e.target.value) })}
          >
            <option value={1}>Day before (D-1)</option>
            <option value={2}>Two days before (D-2)</option>
          </select>
          <input
            type="time"
            aria-label="Cutoff time"
            value={filters.cutoffTime}
            step={600}
            required
            onChange={(e) => e.target.value && set({ cutoffTime: e.target.value })}
          />
          <div className="chips">
            {CUTOFF_PRESETS.map((p) => (
              <button
                key={p.time}
                className="chip"
                aria-pressed={filters.cutoffTime === p.time}
                onClick={() => set({ cutoffTime: p.time })}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="field">
        <span>Buffer confidence</span>
        <div className="chips">
          {CONFIDENCE_LEVELS.map((c) => (
            <button
              key={c}
              className="chip"
              aria-pressed={filters.confidence === c}
              onClick={() => set({ confidence: c })}
            >
              {Math.round(c * 100)}%
            </button>
          ))}
        </div>
      </div>

      <p className="hint">
        For each hour we use the latest forecast published at or before the cutoff. Default: {meta.cutoff_rationale}
      </p>
    </>
  )
}
