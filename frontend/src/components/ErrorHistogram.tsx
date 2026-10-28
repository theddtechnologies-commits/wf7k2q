import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ApiState } from '../hooks/useApi'
import { useChartTheme } from '../hooks/useChartTheme'
import { num } from '../format'
import type { MetricsResponse } from '../types'
import { ChartCard, Legend } from './ChartCard'
import { axisProps, mwAxisLabel, tickMw, xAxisLabel } from './chartStyle'
import { TooltipBox } from './chartBits'

interface Datum {
  mid: number
  start: number
  end: number
  count: number
  beyond: boolean
}

/** Evenly spaced "nice" ticks (multiples of 1/2/2.5/5 × 10^k) covering [lo, hi], always including 0. */
function niceTicks(lo: number, hi: number, target = 6): number[] {
  const raw = (hi - lo) / target
  const mag = 10 ** Math.floor(Math.log10(raw || 1))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? 10 * mag
  const ticks: number[] = []
  for (let t = Math.ceil(lo / step) * step; t <= hi; t += step) ticks.push(t)
  return ticks
}

/** Distribution of forecast errors; bins beyond the recommended buffer are highlighted. */
export function ErrorHistogram({ state }: { state: ApiState<MetricsResponse> }) {
  const theme = useChartTheme()
  const buffer = state.data?.recommendation.buffer_mw ?? 0
  const conf = Math.round((state.data?.recommendation.confidence ?? 0.9) * 100)
  const data: Datum[] =
    state.data?.histogram.map((b) => ({
      mid: (b.bin_start_mw + b.bin_end_mw) / 2,
      start: b.bin_start_mw,
      end: b.bin_end_mw,
      count: b.count,
      beyond: b.bin_start_mw >= buffer,
    })) ?? []
  const lo = data[0]?.start ?? 0
  const hi = data[data.length - 1]?.end ?? 0
  const ticks = niceTicks(lo, hi)

  return (
    <ChartCard
      title="Error distribution"
      subtitle="Forecast − actual, hours per error band. Right of zero = less wind than forecast (shortfall)."
      height={280}
      loading={state.loading}
      hasData={data.length > 0}
      error={state.error}
      table={{
        columns: ['Error band (MW)', 'Hours'],
        rows: data.map((d) => [`${num(d.start)} to ${num(d.end)}`, d.count]),
      }}
    >
      <Legend
        items={[
          { label: 'Within buffer', color: theme.actual },
          { label: `Shortfall beyond ${conf}% buffer`, color: theme.forecast },
        ]}
      />
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 16, right: 8, bottom: 16, left: 8 }} barCategoryGap={1}>
          <CartesianGrid stroke={theme.grid} vertical={false} />
          <XAxis
            dataKey="mid"
            type="number"
            domain={[lo, hi]}
            ticks={ticks}
            interval={0}
            tickFormatter={tickMw}
            label={xAxisLabel(theme, 'Forecast error (MW)')}
            {...axisProps(theme)}
          />
          <YAxis allowDecimals={false} width={48} label={mwAxisLabel(theme, 'Hours')} {...axisProps(theme)} />
          <Tooltip
            cursor={{ fill: theme.band }}
            content={({ active, payload }) => {
              const d = payload?.[0]?.payload as Datum | undefined
              if (!active || !d) return null
              return <TooltipBox title={`${num(d.start)} to ${num(d.end)} MW`} rows={[{ label: 'Hours', value: String(d.count) }]} />
            }}
          />
          <ReferenceLine x={0} stroke={theme.axis} />
          {buffer > 0 && (
            <ReferenceLine
              x={buffer}
              stroke={theme.text}
              strokeDasharray="4 3"
              label={{ value: `${conf}% buffer`, position: 'top', fill: theme.text, fontSize: 12 }}
            />
          )}
          <Bar dataKey="count" radius={[4, 4, 0, 0]} isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.start} fill={d.beyond ? theme.forecast : theme.actual} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}
