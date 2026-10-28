import { useMemo, useState } from 'react'
import { api } from './api'
import { BuyingAdvice } from './components/BuyingAdvice'
import { ErrorBox } from './components/ChartCard'
import { Controls } from './components/Controls'
import { DailyErrorChart } from './components/DailyErrorChart'
import { ErrorHistogram } from './components/ErrorHistogram'
import { ForecastChart } from './components/ForecastChart'
import { HorizonChart } from './components/HorizonChart'
import { HourOfDayChart } from './components/HourOfDayChart'
import { KpiCards } from './components/KpiCards'
import { useApi, useDebounced } from './hooks/useApi'
import type { Filters, Meta } from './types'

export default function App() {
  const meta = useApi((signal) => api.meta(signal), [])

  if (meta.error) {
    return (
      <main className="app">
        <Header />
        <ErrorBox message={`${meta.error}. Is the backend running?`} />
      </main>
    )
  }
  if (!meta.data) {
    return (
      <main className="app">
        <Header />
        <div className="card skeleton" style={{ height: 80 }} />
      </main>
    )
  }
  return <Dashboard meta={meta.data} />
}

function Dashboard({ meta }: { meta: Meta }) {
  const [filters, setFilters] = useState<Filters>({
    start: meta.delivery_start,
    end: meta.delivery_end,
    cutoffTime: meta.default_cutoff_time,
    cutoffDaysBefore: meta.default_cutoff_days_before,
    confidence: meta.default_confidence,
  })
  // Debounce so typing a cutoff time doesn't fire a request per keystroke.
  const f = useDebounced(filters)

  const timeseries = useApi((s) => api.timeseries(f, s), [f.start, f.end, f.cutoffTime, f.cutoffDaysBefore])
  const metrics = useApi((s) => api.metrics(f, s), [f.start, f.end, f.cutoffTime, f.cutoffDaysBefore, f.confidence])
  const horizon = useApi((s) => api.horizon(f, s), [f.start, f.end])

  // Lead times of the forecasts actually used, to shade on the horizon chart.
  const decisionWindow = useMemo<[number, number] | null>(() => {
    const h = timeseries.data?.points.map((p) => p.horizon_h).filter((v): v is number => v !== null) ?? []
    return h.length ? [Math.min(...h), Math.max(...h)] : null
  }, [timeseries.data])

  return (
    <main className="app">
      <Header />
      <Controls filters={filters} meta={meta} onChange={setFilters} />
      <KpiCards summary={metrics.data?.summary} loading={metrics.loading} />
      <BuyingAdvice metrics={metrics} horizon={horizon} />
      <ForecastChart state={timeseries} bufferMw={metrics.data?.recommendation.buffer_mw} confidence={f.confidence} />
      <div className="grid-2">
        <ErrorHistogram state={metrics} />
        <HourOfDayChart state={metrics} />
        <HorizonChart state={horizon} decisionWindow={decisionWindow} />
        <DailyErrorChart state={metrics} />
      </div>
      <footer className="footer">
        Data: Elexon BMRS{' '}
        <a href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream">FUELHH</a> (wind outturn)
        and <a href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream">WINDFOR</a> (wind
        forecast). {meta.forecast_publishes} forecast runs, {meta.forecast_rows.toLocaleString('en-GB')} forecast rows.
      </footer>
    </main>
  )
}

function Header() {
  return (
    <header className="header">
      <div>
        <h1>GB wind forecast accuracy</h1>
        <p>How far can traders trust the day-ahead wind forecast? National wind, delivery 2 Jan – 1 Feb 2026.</p>
      </div>
      <span className="source">Source: Elexon BMRS · times in UK local time</span>
    </header>
  )
}
