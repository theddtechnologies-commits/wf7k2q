import type { Summary } from '../types'
import { num, pct, signedNum } from '../format'

interface Props {
  summary: Summary | undefined
  loading: boolean
}

/** Headline accuracy numbers for the selected period. */
export function KpiCards({ summary, loading }: Props) {
  const cards = summary
    ? [
        {
          label: 'Mean absolute error',
          value: num(summary.mae_mw),
          note: `${pct(summary.nmae_pct_of_mean_actual)} of average wind output`,
        },
        {
          label: 'RMSE',
          value: num(summary.rmse_mw),
          note: 'Penalises large misses more heavily',
        },
        {
          label: 'Bias (forecast − actual)',
          value: signedNum(summary.bias_mw),
          note: summary.bias_mw > 0 ? 'Forecast tends to be too high' : 'Forecast tends to be too low',
        },
        {
          label: 'P90 shortfall',
          value: num(Math.max(0, summary.p90_error_mw)),
          note: '90% of hours fell short by less than this',
        },
      ]
    : null

  return (
    <div className="kpis" aria-busy={loading}>
      {cards
        ? cards.map((c) => (
            <section key={c.label} className={`card kpi card-body${loading ? ' refreshing' : ''}`}>
              <p className="label">{c.label}</p>
              <p className="value">
                {c.value}
                <small>MW</small>
              </p>
              <p className="note">{c.note}</p>
            </section>
          ))
        : Array.from({ length: 4 }, (_, i) => <div key={i} className="card skeleton" style={{ height: 112 }} />)}
    </div>
  )
}
