import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ApiState } from '../hooks/useApi'
import { useChartTheme } from '../hooks/useChartTheme'
import { dayLabel, mw, signedMw } from '../format'
import type { DayStats, MetricsResponse } from '../types'
import { ChartCard, Legend } from './ChartCard'
import { axisProps, mwAxisLabel, tickMw } from './chartStyle'
import { TooltipBox } from './chartBits'

/** Daily bias as diverging bars: which days the forecast over- or under-shot. */
export function DailyErrorChart({ state }: { state: ApiState<MetricsResponse> }) {
  const theme = useChartTheme()
  const data = state.data?.by_day ?? []

  return (
    <ChartCard
      title="Error by delivery day"
      subtitle="Average daily bias. Above zero = forecast too high, so the buyer was short of wind."
      height={280}
      loading={state.loading}
      hasData={data.length > 0}
      error={state.error}
      table={{
        columns: ['Day', 'Bias (MW)', 'MAE (MW)', 'Avg actual (MW)', 'Avg forecast (MW)'],
        rows: data.map((d) => [
          dayLabel(d.date),
          Math.round(d.bias_mw),
          Math.round(d.mae_mw),
          Math.round(d.mean_actual_mw),
          Math.round(d.mean_forecast_mw),
        ]),
      }}
    >
      <Legend
        items={[
          { label: 'Forecast too high (shortfall)', color: theme.over },
          { label: 'Forecast too low (surplus)', color: theme.under },
        ]}
      />
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }} barCategoryGap={2}>
          <CartesianGrid stroke={theme.grid} vertical={false} />
          <XAxis dataKey="date" tickFormatter={dayLabel} minTickGap={16} {...axisProps(theme)} />
          <YAxis tickFormatter={tickMw} width={64} label={mwAxisLabel(theme)} {...axisProps(theme)} />
          <Tooltip
            cursor={{ fill: theme.band }}
            content={({ active, payload }) => {
              const d = payload?.[0]?.payload as DayStats | undefined
              if (!active || !d) return null
              return (
                <TooltipBox
                  title={new Date(d.date).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })}
                  rows={[
                    { label: 'Bias', value: signedMw(d.bias_mw), color: d.bias_mw >= 0 ? theme.over : theme.under },
                    { label: 'MAE', value: mw(d.mae_mw) },
                    { label: 'Avg actual', value: mw(d.mean_actual_mw) },
                    { label: 'Avg forecast', value: mw(d.mean_forecast_mw) },
                  ]}
                />
              )
            }}
          />
          <ReferenceLine y={0} stroke={theme.axis} />
          <Bar dataKey="bias_mw" radius={[4, 4, 0, 0]} isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.date} fill={d.bias_mw >= 0 ? theme.over : theme.under} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}
