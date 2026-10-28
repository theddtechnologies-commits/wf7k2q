import { CartesianGrid, Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ApiState } from '../hooks/useApi'
import { useChartTheme } from '../hooks/useChartTheme'
import { mw, signedMw } from '../format'
import type { HorizonResponse } from '../types'
import { ChartCard, Legend } from './ChartCard'
import { axisProps, mwAxisLabel, tickMw, xAxisLabel } from './chartStyle'
import { TooltipBox } from './chartBits'

interface Props {
  state: ApiState<HorizonResponse>
  /** [min, max] lead time (h) of the forecasts actually used at the decision cutoff. */
  decisionWindow: [number, number] | null
}

interface Datum {
  mid: number
  start: number
  end: number
  mae: number
  bias: number
  n: number
}

/** How forecast accuracy improves as delivery approaches, using every published forecast. */
export function HorizonChart({ state, decisionWindow }: Props) {
  const theme = useChartTheme()
  const data: Datum[] =
    state.data?.buckets.map((b) => ({
      mid: (b.horizon_start_h + b.horizon_end_h) / 2,
      start: b.horizon_start_h,
      end: b.horizon_end_h,
      mae: b.mae_mw,
      bias: b.bias_mw,
      n: b.n,
    })) ?? []

  return (
    <ChartCard
      title="Error vs forecast horizon"
      subtitle="All forecasts, grouped by how far ahead they were issued. Shaded: lead times used at your cutoff."
      height={280}
      loading={state.loading}
      hasData={data.length > 0}
      error={state.error}
      table={{
        columns: ['Hours ahead', 'MAE (MW)', 'Bias (MW)', 'Pairs'],
        rows: data.map((d) => [`${d.start}–${d.end} h`, Math.round(d.mae), Math.round(d.bias), d.n]),
      }}
    >
      <Legend
        items={[
          { label: 'Mean absolute error', color: theme.actual },
          { label: 'Bias (forecast − actual)', color: theme.forecast },
        ]}
      />
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 16, left: 8 }}>
          <CartesianGrid stroke={theme.grid} vertical={false} />
          {decisionWindow && <ReferenceArea x1={decisionWindow[0]} x2={decisionWindow[1]} fill={theme.band} fillOpacity={1} stroke="none" />}
          <XAxis
            dataKey="mid"
            type="number"
            domain={[0, 'dataMax']}
            ticks={data.length ? Array.from({ length: Math.ceil(data[data.length - 1].end / 12) + 1 }, (_, i) => i * 12) : []}
            label={xAxisLabel(theme, 'Hours ahead of delivery')}
            {...axisProps(theme)}
          />
          <YAxis tickFormatter={tickMw} width={64} domain={[0, 'auto']} label={mwAxisLabel(theme)} {...axisProps(theme)} />
          <Tooltip
            cursor={{ stroke: theme.axis }}
            content={({ active, payload }) => {
              const d = payload?.[0]?.payload as Datum | undefined
              if (!active || !d) return null
              return (
                <TooltipBox
                  title={`${d.start}–${d.end} h ahead`}
                  rows={[
                    { label: 'MAE', value: mw(d.mae), color: theme.actual },
                    { label: 'Bias', value: signedMw(d.bias), color: theme.forecast },
                    { label: 'Pairs', value: d.n.toLocaleString('en-GB') },
                  ]}
                />
              )
            }}
          />
          <Line dataKey="mae" stroke={theme.actual} strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 2, stroke: theme.surface }} isAnimationActive={false} />
          <Line dataKey="bias" stroke={theme.forecast} strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 2, stroke: theme.surface }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}
