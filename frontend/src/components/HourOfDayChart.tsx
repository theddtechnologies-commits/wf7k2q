import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ApiState } from '../hooks/useApi'
import { useChartTheme } from '../hooks/useChartTheme'
import { hourLabel, mw, signedMw } from '../format'
import type { HourStats, MetricsResponse } from '../types'
import { ChartCard, Legend } from './ChartCard'
import { axisProps, mwAxisLabel, tickMw, xAxisLabel } from './chartStyle'
import { TooltipBox } from './chartBits'

/** Typical error and the hour-specific buffer for each hour of the delivery day. */
export function HourOfDayChart({ state }: { state: ApiState<MetricsResponse> }) {
  const theme = useChartTheme()
  const data = state.data?.by_hour ?? []
  const conf = Math.round((state.data?.recommendation.confidence ?? 0.9) * 100)

  return (
    <ChartCard
      title="Error by hour of day"
      subtitle="Mean absolute error and the buffer needed at each delivery hour (UK time)."
      height={280}
      loading={state.loading}
      hasData={data.length > 0}
      error={state.error}
      table={{
        columns: ['Hour', 'MAE (MW)', 'Bias (MW)', `${conf}% buffer (MW)`, 'Hours'],
        rows: data.map((d) => [hourLabel(d.hour), Math.round(d.mae_mw), Math.round(d.bias_mw), Math.round(d.buffer_mw), d.n]),
      }}
    >
      <Legend
        items={[
          { label: 'Mean absolute error', color: theme.actual },
          { label: `${conf}% buffer`, color: theme.forecast },
        ]}
      />
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 16, left: 8 }} barCategoryGap={2}>
          <CartesianGrid stroke={theme.grid} vertical={false} />
          <XAxis dataKey="hour" tickFormatter={(h: number) => String(h).padStart(2, '0')} interval={2} label={xAxisLabel(theme, 'Hour of day (UK)')} {...axisProps(theme)} />
          <YAxis tickFormatter={tickMw} width={64} label={mwAxisLabel(theme)} {...axisProps(theme)} />
          <Tooltip
            cursor={{ fill: theme.band }}
            content={({ active, payload }) => {
              const d = payload?.[0]?.payload as HourStats | undefined
              if (!active || !d) return null
              return (
                <TooltipBox
                  title={`${hourLabel(d.hour)}–${hourLabel((d.hour + 1) % 24)}`}
                  rows={[
                    { label: 'MAE', value: mw(d.mae_mw), color: theme.actual },
                    { label: `${conf}% buffer`, value: mw(d.buffer_mw), color: theme.forecast },
                    { label: 'Bias', value: signedMw(d.bias_mw) },
                  ]}
                />
              )
            }}
          />
          <Bar dataKey="mae_mw" fill={theme.actual} radius={[4, 4, 0, 0]} isAnimationActive={false} />
          <Line dataKey="buffer_mw" stroke={theme.forecast} strokeWidth={2} dot={{ r: 3, fill: theme.forecast, strokeWidth: 0 }} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}
