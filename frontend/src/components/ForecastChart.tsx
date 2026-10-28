import { useMemo } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ApiState } from '../hooks/useApi'
import { useChartTheme } from '../hooks/useChartTheme'
import { dateTimeLabel, dayLabel, mw, signedMw } from '../format'
import type { TimeseriesResponse } from '../types'
import { ChartCard, Legend } from './ChartCard'
import { axisProps, mwAxisLabel, tickMw } from './chartStyle'
import { TooltipBox } from './chartBits'

interface Props {
  state: ApiState<TimeseriesResponse>
  bufferMw: number | undefined
  confidence: number
}

interface Datum {
  t: number
  actual: number
  forecast: number | null
  plan: number | null
  publish: string | null
  horizon: number | null
  error: number | null
}

const DAY_MS = 86_400_000

/** One tick per day for short ranges, thinned out for longer ones. */
function dayTicks(first: number, last: number): number[] {
  const start = Math.ceil(first / DAY_MS) * DAY_MS
  const days = Math.max(1, Math.round((last - start) / DAY_MS))
  const step = Math.ceil(days / 10)
  const ticks: number[] = []
  for (let t = start; t <= last; t += step * DAY_MS) ticks.push(t)
  return ticks
}

export function ForecastChart({ state, bufferMw, confidence }: Props) {
  const theme = useChartTheme()
  const data = useMemo<Datum[]>(
    () =>
      state.data?.points.map((p) => ({
        t: Date.parse(p.start_time),
        actual: p.actual_mw,
        forecast: p.forecast_mw,
        // Planning level = forecast - buffer. Where the buffer exceeds the forecast the line
        // breaks (null) rather than drawing a flat 0, which would look like missing data.
        plan: p.forecast_mw !== null && bufferMw !== undefined && p.forecast_mw > bufferMw ? p.forecast_mw - bufferMw : null,
        publish: p.publish_time,
        horizon: p.horizon_h,
        error: p.error_mw,
      })) ?? [],
    [state.data, bufferMw],
  )
  const ticks = data.length ? dayTicks(data[0].t, data[data.length - 1].t) : []
  // Round y ticks: 5,000 MW steps up to the largest value shown.
  const yMax = Math.ceil(Math.max(1, ...data.map((d) => Math.max(d.actual, d.forecast ?? 0))) / 5000) * 5000
  const yTicks = Array.from({ length: yMax / 5000 + 1 }, (_, i) => i * 5000)
  const planLabel = `Forecast − ${Math.round(confidence * 100)}% buffer`

  return (
    <ChartCard
      title="Actual wind vs day-ahead forecast"
      subtitle="Hourly national wind generation (UK time). The forecast shown is the latest one published before the decision cutoff. Gaps mean no value."
      height={340}
      loading={state.loading}
      hasData={data.length > 0}
      error={state.error}
      table={{
        columns: ['Time (UK)', 'Actual (MW)', 'Forecast (MW)', 'Error (MW)', 'Forecast issued'],
        rows: data.map((d) => [
          dateTimeLabel(d.t),
          Math.round(d.actual),
          d.forecast ?? '—',
          d.error !== null ? Math.round(d.error) : '—',
          d.publish ? dateTimeLabel(d.publish) : '—',
        ]),
      }}
    >
      <Legend
        items={[
          { label: 'Actual generation', color: theme.actual },
          { label: 'Day-ahead forecast', color: theme.forecast },
          { label: planLabel, color: theme.plan, dashed: true },
        ]}
      />
      <ResponsiveContainer width="100%" height={340}>
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={theme.grid} vertical={false} />
          <XAxis
            dataKey="t"
            type="number"
            scale="time"
            domain={['dataMin', 'dataMax']}
            ticks={ticks}
            tickFormatter={dayLabel}
            {...axisProps(theme)}
          />
          <YAxis domain={[0, yMax]} ticks={yTicks} tickFormatter={tickMw} width={64} label={mwAxisLabel(theme)} {...axisProps(theme)} />
          <Tooltip
            cursor={{ stroke: theme.axis }}
            content={({ active, payload }) => {
              const d = payload?.[0]?.payload as Datum | undefined
              if (!active || !d) return null
              return (
                <TooltipBox
                  title={dateTimeLabel(d.t)}
                  rows={[
                    { label: 'Actual', value: mw(d.actual), color: theme.actual },
                    { label: 'Forecast', value: d.forecast !== null ? mw(d.forecast) : '—', color: theme.forecast },
                    { label: 'Error', value: d.error !== null ? signedMw(d.error) : '—' },
                    {
                      label: 'Plan level',
                      value: d.plan !== null ? mw(d.plan) : d.forecast !== null ? 'buffer ≥ forecast' : '—',
                      color: theme.plan,
                    },
                    {
                      label: 'Issued',
                      value: d.publish ? `${dateTimeLabel(d.publish)} (${d.horizon?.toFixed(1)} h ahead)` : '—',
                    },
                  ]}
                />
              )
            }}
          />
          <Line dataKey="plan" connectNulls={false} stroke={theme.plan} strokeWidth={1.5} strokeDasharray="4 3" dot={false} activeDot={false} isAnimationActive={false} />
          <Line dataKey="forecast" connectNulls={false} stroke={theme.forecast} strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 2, stroke: theme.surface }} isAnimationActive={false} />
          <Line dataKey="actual" connectNulls={false} stroke={theme.actual} strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 2, stroke: theme.surface }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}
