import type { ApiState } from '../hooks/useApi'
import { hourLabel, mw, pct } from '../format'
import type { HorizonResponse, MetricsResponse } from '../types'
import { ErrorBox } from './ChartCard'

interface Props {
  metrics: ApiState<MetricsResponse>
  horizon: ApiState<HorizonResponse>
}

/** Confidence as plain odds: 0.9 → "9 hours in 10", 0.95 → "19 hours in 20". */
function hoursInN(confidence: number): string {
  const pct = Math.round(confidence * 100)
  for (const n of [10, 20, 100]) {
    if ((pct * n) % 100 === 0) return `${(pct * n) / 100}\u00a0hours\u00a0in\u00a0${n}`
  }
  return `${pct}\u00a0hours\u00a0in\u00a0100`
}

/** Plain-English translation of the metrics into a procurement action. */
export function BuyingAdvice({ metrics, horizon }: Props) {
  const m = metrics.data
  const buckets = horizon.data?.buckets ?? []

  if (metrics.error) {
    return (
      <section className="card advice">
        <ErrorBox message={metrics.error} />
      </section>
    )
  }
  if (!m) return <div className="card skeleton" style={{ height: 170 }} />

  const r = m.recommendation
  const s = m.summary
  const conf = Math.round(r.confidence * 100)
  const near = buckets[0]
  const far = buckets.length > 1 ? buckets[buckets.length - 1] : undefined

  return (
    <section className={`card advice card-body${metrics.loading ? ' refreshing' : ''}`} aria-live="polite">
      <div className="card-head">
        <h2>What this means for buying power</h2>
      </div>
      <p className="headline">
        In {conf}% of hours, actual wind was no more than {mw(r.buffer_mw)} below the forecast, so consider procuring an
        extra <span className="buffer">{mw(r.buffer_mw)}</span> to cover {hoursInN(r.confidence)}.
      </p>
      <ul>
        <li>
          The forecast was <b>too high in {pct(r.shortfall_hours_pct, 0)} of hours</b>, by {mw(Math.abs(s.bias_mw))} on
          average ({s.bias_mw > 0 ? 'systematic over-forecast' : 'systematic under-forecast'}). The buffer is{' '}
          {pct(r.buffer_pct_of_mean_forecast, 0)} of the average forecast.
        </li>
        {/* Static finding from an offline check (scripts/verify_curtailment.py); the app itself uses only FUELHH and WINDFOR. */}
        {s.bias_mw > 0 && (
          <li>
            Most of this over-forecast is curtailment, not missing wind: an offline check found that output cut by the
            grid operator explains about 75% of January’s bias (full-month analysis; see README).
          </li>
        )}
        <li>
          Highest-risk delivery hours: <b>{r.riskiest_hours.map(hourLabel).join(', ')}</b>. Consider a larger buffer
          for these hours (see “Error by hour of day”).
        </li>
        {near && far && (
          <li>
            Forecasts improve closer to delivery: MAE is {mw(near.mae_mw)} at {near.horizon_start_h}–{near.horizon_end_h}{' '}
            h ahead vs {mw(far.mae_mw)} at {far.horizon_start_h}–{far.horizon_end_h} h. Topping up intraday can reduce
            the buffer needed.
          </li>
        )}
        <li>
          Based on {s.n.toLocaleString('en-GB')} hours
          {s.coverage_pct < 99.5 ? ` (${pct(s.coverage_pct, 0)} of hours had a forecast before the cutoff)` : ''}. Past
          errors are a guide, not a guarantee.
        </li>
      </ul>
    </section>
  )
}
