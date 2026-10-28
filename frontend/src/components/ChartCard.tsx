import { useState, type ReactNode } from 'react'

export interface TableView {
  columns: string[]
  rows: (string | number)[][]
}

interface Props {
  title: string
  subtitle?: ReactNode
  height: number
  loading: boolean // true while fetching (first load or refresh)
  hasData: boolean
  error: string | null
  table?: TableView
  children: ReactNode
}

/**
 * Card wrapper giving every chart the same loading, error and table-view behaviour.
 * The table view is the accessible equivalent of the chart (and handy for traders).
 */
export function ChartCard({ title, subtitle, height, loading, hasData, error, table, children }: Props) {
  const [showTable, setShowTable] = useState(false)

  let body: ReactNode
  if (error) {
    body = <ErrorBox message={error} />
  } else if (!hasData) {
    body = <div className="skeleton" style={{ height }} aria-label="Loading" />
  } else if (showTable && table) {
    body = <DataTable {...table} />
  } else {
    body = children
  }

  return (
    <section className="card">
      <div className="card-head">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {table && hasData && !error && (
          <button className="ghost-button" onClick={() => setShowTable((v) => !v)}>
            {showTable ? 'Chart' : 'Table'}
          </button>
        )}
      </div>
      <div className={`card-body${loading && hasData ? ' refreshing' : ''}`} aria-busy={loading}>
        {body}
      </div>
    </section>
  )
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="error-box" role="alert">
      <span aria-hidden>⚠</span>
      <span>Could not load data: {message}</span>
    </div>
  )
}

function DataTable({ columns, rows }: TableView) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export interface LegendItem {
  label: string
  color: string
  dashed?: boolean
}

/** HTML legend: always shown for multi-series charts so identity is never colour-only. */
export function Legend({ items }: { items: LegendItem[] }) {
  return (
    <div className="legend">
      {items.map((item) => (
        <span key={item.label}>
          <span
            className="swatch"
            style={
              item.dashed
                ? { background: `repeating-linear-gradient(90deg, ${item.color} 0 4px, transparent 4px 6px)` }
                : { background: item.color }
            }
          />
          {item.label}
        </span>
      ))}
    </div>
  )
}
